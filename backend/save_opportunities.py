"""
One-shot: predict + save opportunities from already-classified relevant signals.
Run this once after the pipeline has classified all signals.

Usage:
    cd E:\Claude Projects\Apex\backend
    python save_opportunities.py
"""
from __future__ import annotations
import asyncio, json, os, sys, uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# Force-load .env
for line in Path('.env').read_text(encoding='utf-8').splitlines():
    line = line.strip()
    if not line or line.startswith('#') or '=' not in line: continue
    k, _, v = line.partition('=')
    if not os.environ.get(k.strip()): os.environ[k.strip()] = v.strip()

from app.core.config import get_settings
get_settings.cache_clear()

USER_ID = 'bd380ed9-9d4a-4a34-ac42-5355019f4a93'
RELEVANCE_THRESHOLD = 0.4


async def main():
    import asyncpg
    from app.core.config import get_settings
    from app.agents.opportunity_predictor import (
        OpportunityPredictorAgent, OpportunityPredictorInput,
        SignalSummary, UserProfileSummary
    )
    from app.agents.action_generator import (
        ActionGeneratorAgent, ActionGeneratorInput, OpportunityForActions
    )
    from datetime import datetime, timezone, timedelta

    settings = get_settings()
    db_url = settings.DATABASE_URL.replace('postgresql+asyncpg://', 'postgresql://')
    conn = await asyncpg.connect(db_url, statement_cache_size=0)
    uid = uuid.UUID(USER_ID)

    # Load career profile
    profile_row = await conn.fetchrow(
        'SELECT "current_role", target_roles, industries, aspirations_text '
        'FROM career_profiles WHERE user_id = $1', uid
    )
    profile = dict(profile_row) if profile_row else {}
    print(f"Profile: {profile.get('current_role')} | targets: {(profile.get('target_roles') or [])[:2]}")

    # Load relevant signals grouped by company
    sig_rows = await conn.fetch(
        'SELECT s.id, s.type, s.title, s.description, s.signal_date, s.relevance_score, '
        '       s.company_id, c.name as company_name '
        'FROM signals s JOIN companies c ON c.id = s.company_id '
        'WHERE s.user_id = $1 AND s.relevance_score >= $2',
        uid, RELEVANCE_THRESHOLD
    )
    print(f"Relevant signals: {len(sig_rows)}")

    # Group by company
    by_company: dict[str, list] = {}
    for r in sig_rows:
        cid = str(r['company_id'])
        by_company.setdefault(cid, []).append(r)

    print(f"Companies with relevant signals: {len(by_company)}\n")

    opp_agent = OpportunityPredictorAgent(settings=settings)
    act_agent = ActionGeneratorAgent(settings=settings)
    total_opps = 0
    total_actions = 0

    for cid, sigs in by_company.items():
        company_name = sigs[0]['company_name']
        print(f"[{company_name}] {len(sigs)} signals -> predicting...")

        inp = OpportunityPredictorInput(
            user_id=USER_ID,
            company_id=cid,
            company_name=company_name,
            company_signals=[
                SignalSummary(
                    signal_id=str(s['id']),
                    signal_type=s['type'],
                    title=s['title'] or '',
                    description=s['description'] or '',
                    signal_date=s['signal_date'].isoformat() if s['signal_date'] else '',
                    relevance_score=float(s['relevance_score']),
                )
                for s in sigs
            ],
            user_profile=UserProfileSummary(
                current_role=profile.get('current_role') or '',
                target_roles=profile.get('target_roles') or [],
                industries=profile.get('industries') or [],
                aspirations_text=profile.get('aspirations_text') or '',
            ),
        )

        try:
            output = await opp_agent.predict(inp)
        except Exception as exc:
            print(f"  PREDICT FAILED: {exc}")
            continue

        # Save opportunity
        oid = str(uuid.uuid4())
        sig_uuids = [s['id'] for s in sigs]  # already UUID objects from asyncpg
        try:
            async with conn.transaction():
                await conn.execute(
                    'INSERT INTO opportunities '
                    '(id, user_id, company_id, predicted_role, confidence, '
                    ' timeline_weeks, why_fit, approach_angle, '
                    ' predicted_salary_range, fit_score, signal_ids, status) '
                    'VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11::uuid[],$12)',
                    uuid.UUID(oid),
                    uid,
                    uuid.UUID(cid),
                    output.predicted_role,
                    output.confidence,
                    output.timeline_weeks,
                    output.why_fit,
                    output.approach_angle,
                    '',
                    0.0,
                    sig_uuids,
                    'PREDICTED',
                )
            print(f"  [{output.confidence}] {output.predicted_role} ({output.timeline_weeks}w) - SAVED")
            total_opps += 1
        except Exception as exc:
            print(f"  SAVE FAILED: {exc}")
            continue

        # Generate actions
        try:
            act_inp = ActionGeneratorInput(
                user_id=USER_ID,
                opportunity_id=oid,
                opportunity=OpportunityForActions(
                    predicted_role=output.predicted_role,
                    confidence=output.confidence,
                    timeline_weeks=output.timeline_weeks,
                    why_fit=output.why_fit,
                    company_name=company_name,
                ),
                fit_score=70.0,
                contacts=[],
            )
            act_out = await act_agent.generate(act_inp)
            now = datetime.now(timezone.utc)
            for a in act_out.actions:
                days = int(a.due_date.replace('+','').replace('d','')) if 'd' in a.due_date else 3
                due = now + timedelta(days=days)
                async with conn.transaction():
                    await conn.execute(
                        'INSERT INTO actions '
                        '(id, user_id, opportunity_id, company_id, title, description, '
                        ' type, priority, status, due_date, ai_draft_json) '
                        'VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10::timestamptz,$11::jsonb)',
                        uuid.uuid4(), uid, uuid.UUID(oid), uuid.UUID(cid),
                        a.title, '', a.type, a.priority, 'TODO', due, '{}'
                    )
                    total_actions += 1
            print(f"  {len(act_out.actions)} actions generated")
        except Exception as exc:
            print(f"  ACTIONS FAILED: {exc}")

    await conn.close()
    print(f"\nDONE: {total_opps} opportunities, {total_actions} actions saved to DB")


if __name__ == '__main__':
    asyncio.run(main())
