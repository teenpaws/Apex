"""
Apex Live Pipeline Runner — no Celery/Redis required.

Runs the complete pipeline for Swapneet's account:
  1. Load companies + career profile from Supabase
  2. Fetch signals: NewsData.io + GNews (by company name)
  3. Persist new signals to DB (deduplication via dedup_hash)
  4. Classify each signal (Claude Haiku)
  5. For each company with relevant signals:
       → Predict opportunities (Claude Sonnet)
       → Score career fit (Claude Sonnet)
  6. Generate actions (Claude Haiku)
  7. Print summary

Usage:
    cd E:\Claude Projects\Apex\backend
    python run_pipeline.py
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import sys
import os
import uuid
from datetime import datetime, timezone

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("apex.pipeline")
sys.path.insert(0, os.path.dirname(__file__))

# ── Force-load .env before any app imports ─────────────────────────────────────
# Windows system environment variables (even empty ones) override pydantic_settings.
# We read .env directly and fill in any missing/empty env vars.
def _load_env_override():
    from pathlib import Path
    env_path = Path(__file__).parent / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        # Override if system env is missing or empty
        if not os.environ.get(key):
            os.environ[key] = value

_load_env_override()

# Clear cached settings so they re-read with corrected env vars
from app.core.config import get_settings as _gs
_gs.cache_clear()

USER_ID = "bd380ed9-9d4a-4a34-ac42-5355019f4a93"


# ── DB helpers ─────────────────────────────────────────────────────────────────

async def get_db(settings):
    import asyncpg
    url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    return await asyncpg.connect(url, statement_cache_size=0)


async def load_companies(conn) -> list[dict]:
    rows = await conn.fetch("SELECT id, name, domain FROM companies")
    return [dict(r) for r in rows]


async def load_career_profile(conn, user_id: str) -> dict:
    row = await conn.fetchrow(
        'SELECT "current_role", target_roles, industries, aspirations_text FROM career_profiles WHERE user_id = $1',
        uuid.UUID(user_id),
    )
    if not row:
        return {}
    return dict(row)


async def signal_exists(conn, dedup_hash: str) -> bool:
    row = await conn.fetchrow(
        "SELECT id FROM signals WHERE dedup_hash = $1", dedup_hash
    )
    return row is not None


async def persist_signal(conn, user_id: str, company_id: str, event) -> str | None:
    """Insert a new signal; return its UUID or None if duplicate."""
    raw = json.dumps(event.raw_data)
    dedup_hash = hashlib.sha256(
        f"{event.source}:{event.external_id}:{event.signal_date.date().isoformat()}".encode()
    ).hexdigest()

    if await signal_exists(conn, dedup_hash):
        return None

    sid = str(uuid.uuid4())
    try:
        async with conn.transaction():
            await conn.execute(
                """
                INSERT INTO signals
                    (id, user_id, company_id, type, source, title, description,
                     raw_data_json, signal_date, relevance_score, is_duplicate, dedup_hash)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb, $9::timestamptz, $10, $11, $12)
                """,
                sid,
                uuid.UUID(user_id),
                uuid.UUID(company_id) if company_id else None,
                "FUNDING",          # default; overwritten after classification
                event.source,
                (event.title or "")[:500],
                (event.description or "")[:2000],
                raw,
                event.signal_date,
                0.5,                # default; overwritten after classification
                False,
                dedup_hash,
            )
    except Exception as exc:
        logger.warning("persist_signal failed: %s", exc)
        return None
    return sid


async def update_signal_classification(conn, signal_id: str, signal_type: str, relevance_score: float):
    try:
        async with conn.transaction():
            await conn.execute(
                "UPDATE signals SET type = $1, relevance_score = $2 WHERE id = $3",
                signal_type, relevance_score, uuid.UUID(signal_id),
            )
    except Exception as exc:
        logger.warning("update_signal_classification failed: %s", exc)


async def persist_opportunity(conn, user_id: str, company_id: str, output, signal_ids: list[str]) -> str:
    oid = str(uuid.uuid4())
    sig_uuids = [uuid.UUID(s) for s in signal_ids]
    try:
        async with conn.transaction():
            await conn.execute(
                """
                INSERT INTO opportunities
                    (id, user_id, company_id, predicted_role, confidence,
                     timeline_weeks, why_fit, positioning_notes,
                     predicted_salary_range, fit_score, signal_ids, status)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11::uuid[],$12)
                """,
                oid,
                uuid.UUID(user_id),
                uuid.UUID(company_id),
                output.predicted_role,
                output.confidence,
                output.timeline_weeks,
                output.why_fit,
                output.positioning_notes,
                "",    # predicted_salary_range not in agent output
                0.0,   # fit_score filled in later
                sig_uuids,
                "PREDICTED",
            )
    except Exception as exc:
        logger.warning("persist_opportunity failed: %s", exc)
    return oid


def _parse_relative_due(due_str: str) -> datetime:
    """Convert '+3d', '+1w' etc to an absolute datetime."""
    from datetime import timedelta
    now = datetime.now(timezone.utc)
    try:
        if due_str.startswith("+") and due_str.endswith("d"):
            return now + timedelta(days=int(due_str[1:-1]))
        if due_str.startswith("+") and due_str.endswith("w"):
            return now + timedelta(weeks=int(due_str[1:-1]))
    except (ValueError, IndexError):
        pass
    return now + timedelta(days=3)


async def persist_actions(conn, user_id: str, opportunity_id: str, company_id: str, actions: list[dict]):
    for a in actions:
        aid = str(uuid.uuid4())
        due = _parse_relative_due(a.get("due_date", "+3d"))
        try:
            async with conn.transaction():
                await conn.execute(
                    """
                    INSERT INTO actions
                        (id, user_id, opportunity_id, company_id,
                         title, description, type, priority, status, due_date, ai_draft_json)
                    VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10::timestamptz,$11::jsonb)
                    """,
                    aid,
                    uuid.UUID(user_id),
                    uuid.UUID(opportunity_id),
                    uuid.UUID(company_id),
                    a.get("title", "Action"),
                    "",   # description not in ActionItem schema
                    a.get("type", "OUTREACH"),
                    a.get("priority", "MEDIUM"),
                    "TODO",
                    due,
                    "{}",
                )
        except Exception as exc:
            logger.warning("persist_action failed: %s", exc)


# ── Pipeline stages ────────────────────────────────────────────────────────────

async def get_unclassified_signals(conn) -> list[str]:
    """Return IDs of signals with default relevance_score (never classified)."""
    uid = uuid.UUID(USER_ID)
    rows = await conn.fetch(
        "SELECT id FROM signals WHERE user_id = $1 AND relevance_score = 0.5",
        uid
    )
    return [str(r["id"]) for r in rows]


async def ingest_company(company: dict, user_id: str, conn, settings) -> list[str]:
    """Fetch news for one company, persist new signals, return their IDs."""
    from app.integrations.newsdata_client import NewsDataClient
    from app.integrations.gnews_client import GNewsClient

    name = company["name"]
    company_id = str(company["id"])
    new_ids: list[str] = []

    for Client, label in [(NewsDataClient, "NewsData"), (GNewsClient, "GNews")]:
        try:
            client = Client()
            events = await client.fetch_company_news(name, days_back=14)
            for event in events:
                sid = await persist_signal(conn, user_id, company_id, event)
                if sid:
                    new_ids.append(sid)
            logger.info("  %s → %s: %d new signals", name, label, len([e for e in events]))
        except Exception as exc:
            logger.warning("  %s %s error: %s", name, label, exc)

    return new_ids


async def classify_signals(signal_ids: list[str], conn, profile: dict, settings) -> list[str]:
    """Classify signals, return IDs of relevant ones (score >= 0.4)."""
    from app.agents.signal_classifier import SignalClassifierAgent, SignalClassifierInput

    agent = SignalClassifierAgent(settings=settings)
    relevant_ids: list[str] = []

    for sid in signal_ids:
        try:
            row = await conn.fetchrow(
                "SELECT id, title, description, source, signal_date, company_id FROM signals WHERE id = $1",
                uuid.UUID(sid)
            )
            if not row:
                continue

            # Get company name
            comp_row = await conn.fetchrow("SELECT name FROM companies WHERE id = $1", row["company_id"])
            company_name = comp_row["name"] if comp_row else "Unknown"

            inp = SignalClassifierInput(
                signal_id=sid,
                title=row["title"] or "",
                description=row["description"] or "",
                source=row["source"] or "",
                signal_date=row["signal_date"],
                company_name=company_name,
                user_target_industries=profile.get("industries", []),
                user_target_roles=profile.get("target_roles", []),
            )
            output = await agent.classify(inp)
            await update_signal_classification(conn, sid, output.signal_type, output.relevance_score)

            if output.relevance_score >= 0.4:
                relevant_ids.append(sid)
                logger.info("  Signal %s: %s (%.2f)", sid[:8], output.signal_type, output.relevance_score)
            else:
                logger.debug("  Signal %s gated out: %.2f", sid[:8], output.relevance_score)

        except Exception as exc:
            logger.warning("  classify %s failed: %s", sid[:8], exc)

    return relevant_ids


async def predict_opportunities(company: dict, signal_ids: list[str], profile: dict, user_id: str, conn, settings) -> list[str]:
    """Predict opportunities for one company, return opportunity IDs."""
    from app.agents.opportunity_predictor import (
        OpportunityPredictorAgent, OpportunityPredictorInput,
        SignalSummary, UserProfileSummary
    )

    if not signal_ids:
        return []

    # Load signal details
    signal_rows = []
    for sid in signal_ids:
        row = await conn.fetchrow(
            "SELECT id, type, title, description, signal_date, relevance_score FROM signals WHERE id = $1",
            uuid.UUID(sid)
        )
        if row:
            signal_rows.append(row)

    if not signal_rows:
        return []

    agent = OpportunityPredictorAgent(settings=settings)
    inp = OpportunityPredictorInput(
        user_id=user_id,
        company_id=str(company["id"]),
        company_name=company["name"],
        company_signals=[
            SignalSummary(
                signal_id=str(r["id"]),
                signal_type=r["type"],
                title=r["title"] or "",
                description=r["description"] or "",
                signal_date=r["signal_date"].isoformat() if r["signal_date"] else "",
                relevance_score=float(r["relevance_score"] or 0.5),
            )
            for r in signal_rows
        ],
        user_profile=UserProfileSummary(
            current_role=profile.get("current_role") or "",
            target_roles=profile.get("target_roles") or [],
            industries=profile.get("industries") or [],
            aspirations_text=profile.get("aspirations_text") or "",
        ),
    )

    try:
        output = await agent.predict(inp)
        oid = await persist_opportunity(conn, user_id, str(company["id"]), output, signal_ids)
        logger.info(
            "  Opportunity: %s | %s | %d weeks",
            output.predicted_role, output.confidence, output.timeline_weeks
        )
        return [oid]
    except Exception as exc:
        logger.warning("  predict_opportunities failed for %s: %s", company["name"], exc)
        return []


async def generate_actions_for_opportunity(opp_id: str, company: dict, profile: dict, user_id: str, conn, settings):
    """Generate actions for a predicted opportunity."""
    from app.agents.action_generator import (
        ActionGeneratorAgent, ActionGeneratorInput, OpportunityForActions
    )

    try:
        opp_row = await conn.fetchrow(
            "SELECT predicted_role, confidence, why_fit, positioning_notes, timeline_weeks FROM opportunities WHERE id = $1",
            uuid.UUID(opp_id)
        )
        if not opp_row:
            return

        agent = ActionGeneratorAgent(settings=settings)
        inp = ActionGeneratorInput(
            user_id=user_id,
            opportunity_id=opp_id,
            opportunity=OpportunityForActions(
                predicted_role=opp_row["predicted_role"],
                confidence=opp_row["confidence"],
                timeline_weeks=opp_row["timeline_weeks"],
                why_fit=opp_row["why_fit"] or "",
                company_name=company["name"],
            ),
            fit_score=70.0,
            contacts=[],
        )
        output = await agent.generate(inp)
        actions = [a.model_dump() for a in output.actions]
        await persist_actions(conn, user_id, opp_id, str(company["id"]), actions)
        logger.info("  Generated %d actions for %s", len(actions), opp_row["predicted_role"])
    except Exception as exc:
        logger.warning("  generate_actions failed for opp %s: %s", opp_id[:8], exc)


# ── Main ───────────────────────────────────────────────────────────────────────

async def main():
    from app.core.config import get_settings
    settings = get_settings()

    print("\n" + "="*60)
    print("  APEX — First Production Run")
    print("  User: Swapneet Lahoti | HEC Paris MBA 2026")
    print("="*60)

    conn = await get_db(settings)
    try:
        # Load companies and profile
        companies = await load_companies(conn)
        profile = await load_career_profile(conn, USER_ID)
        print(f"\n[Setup] {len(companies)} companies | Profile: {profile.get('current_role', 'loaded')}")
        print(f"        Targets: {', '.join((profile.get('target_roles') or [])[:3])} ...")

        total_signals = 0
        total_relevant = 0
        total_opps = 0
        total_actions = 0

        # Step A: Classify any existing unclassified signals first
        print("\n[Backfill] Classifying existing unclassified signals...")
        unclassified = await get_unclassified_signals(conn)
        print(f"           Found {len(unclassified)} unclassified signals")
        backfill_relevant = await classify_signals(unclassified, conn, profile, settings)
        total_relevant += len(backfill_relevant)
        print(f"           {len(backfill_relevant)} relevant after classification")

        # Group backfill relevant signals by company for opportunity prediction
        if backfill_relevant:
            by_company: dict[str, list[str]] = {}
            for sid in backfill_relevant:
                row = await conn.fetchrow(
                    "SELECT company_id FROM signals WHERE id = $1", uuid.UUID(sid)
                )
                if row and row["company_id"]:
                    cid = str(row["company_id"])
                    by_company.setdefault(cid, []).append(sid)

            company_map = {str(c["id"]): c for c in companies}
            for cid, sids in by_company.items():
                company = company_map.get(cid)
                if not company:
                    continue
                print(f"\n  Predicting for {company['name']} ({len(sids)} signals)...")
                opp_ids = await predict_opportunities(company, sids, profile, USER_ID, conn, settings)
                total_opps += len(opp_ids)
                for opp_id in opp_ids:
                    await generate_actions_for_opportunity(opp_id, company, profile, USER_ID, conn, settings)
                total_actions += len(opp_ids) * 3

        # Step B: Ingest new signals for each company
        print()
        for i, company in enumerate(companies, 1):
            print(f"\n[{i}/{len(companies)}] {company['name']}")

            # Ingest
            new_signal_ids = await ingest_company(company, USER_ID, conn, settings)
            total_signals += len(new_signal_ids)

            if not new_signal_ids:
                print(f"  No new signals")
                continue

            # Classify
            print(f"  Classifying {len(new_signal_ids)} signals ...")
            relevant_ids = await classify_signals(new_signal_ids, conn, profile, settings)
            total_relevant += len(relevant_ids)

            if not relevant_ids:
                print(f"  No relevant signals (all gated out)")
                continue

            # Predict opportunities
            print(f"  Predicting opportunities from {len(relevant_ids)} signals ...")
            opp_ids = await predict_opportunities(company, relevant_ids, profile, USER_ID, conn, settings)
            total_opps += len(opp_ids)

            for opp_id in opp_ids:
                await generate_actions_for_opportunity(opp_id, company, profile, USER_ID, conn, settings)
            total_actions += len(opp_ids) * 3

        print("\n" + "="*60)
        print("  PIPELINE COMPLETE")
        print(f"  Signals ingested : {total_signals}")
        print(f"  Signals relevant : {total_relevant}")
        print(f"  Opportunities    : {total_opps}")
        print(f"  Actions created  : ~{total_actions}")
        print("="*60)
        print("\n  View at: http://127.0.0.1:9000/api/v1/signals")
        print("           http://127.0.0.1:9000/api/v1/opportunities")
        print("           http://127.0.0.1:9000/api/v1/actions")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
