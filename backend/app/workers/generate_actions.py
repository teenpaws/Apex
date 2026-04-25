"""
Celery workers for action generation and positioning advice.

Tasks:
  generate_actions_for_opportunity — Run ActionGeneratorAgent after opportunity is scored
  advise_positioning               — Run PositioningAdvisorAgent for outreach prep
  run_reasoning_pipeline           — Full pipeline: scoring + positioning (parallel) → actions

Pipeline position:
  predict_and_score (predict_opportunities worker)
    → [parallel]
        score_opportunity_fit (already done)
        advise_positioning
      [join]
    → generate_actions_for_opportunity

All tasks are sync Celery tasks that run async agent logic via asyncio.run().
Under USE_MOCK_DATA=true no real DB reads/writes occur — mock data is used.
Under MOCK_AGENTS=true no Claude API calls are made — fixture data is returned.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from celery.utils.log import get_task_logger

from app.core.celery_app import celery_app
from app.core.config import get_settings

logger = get_task_logger(__name__)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _get_settings():
    return get_settings()


def _load_mock_opportunity_full(opportunity_id: str, user_id: str) -> dict[str, Any]:
    """Return full mock opportunity context for USE_MOCK_DATA=true."""
    return {
        "opportunity": {
            "predicted_role": "VP of Strategy",
            "confidence": "HIGH",
            "timeline_weeks": 6,
            "why_fit": (
                "Your MBA background and AI strategy experience align directly with "
                "McKinsey's new digital transformation push."
            ),
            "ideal_contact_title": "Chief of Staff or Partner",
            "company_name": "McKinsey & Company",
        },
        "fit_score": 82.5,
        "contacts": [
            {
                "name": "Jane Smith",
                "title": "Chief of Staff",
                "linkedin_url": "https://linkedin.com/in/janesmith",
            }
        ],
        "user_profile": {
            "current_role": "Senior Strategy Consultant",
            "aspirations_text": (
                "I want to move into a principal-level strategy role where I can "
                "lead AI transformation projects for global enterprises."
            ),
            "skills": ["Strategy", "AI/ML", "Change Management"],
            "career_history_summary": (
                "5 years strategy consulting at Bain, then 2 years at a Series B AI startup. "
                "HEC Paris MBA, graduated 2024."
            ),
        },
        "company_signals": [
            {
                "signal_type": "FUNDING",
                "title": "McKinsey Raises $500M for Digital Transformation Fund",
                "description": (
                    "McKinsey & Company announced a new $500M digital transformation "
                    "fund to expand its AI and data analytics practice globally."
                ),
                "signal_date": "2026-04-10T09:00:00Z",
            }
        ],
    }


def _mock_store_actions(user_id: str, opportunity_id: str, actions: list) -> None:
    """Log what a real DB insert of actions would do."""
    logger.info(
        "[mock] DB insert — actions: user=%s opp=%s count=%d",
        user_id,
        opportunity_id,
        len(actions),
    )
    for action in actions:
        logger.info(
            "[mock]   action: title=%s type=%s priority=%s due=%s",
            action.get("title"),
            action.get("type"),
            action.get("priority"),
            action.get("due_date"),
        )


def _mock_store_positioning(opportunity_id: str, positioning: dict) -> None:
    """Log what a real DB update with positioning notes would do."""
    logger.info(
        "[mock] DB update — opportunities: id=%s positioning_stored=True",
        opportunity_id,
    )


# ── Live DB helpers ────────────────────────────────────────────────────────────

def _parse_due_date(due_str: str):
    """Convert '+3d' / '+1w' style strings to an absolute UTC datetime."""
    from datetime import datetime, timezone, timedelta  # noqa: PLC0415
    now = datetime.now(tz=timezone.utc)
    s = due_str.strip().lstrip("+")
    if s.endswith("d"):
        return now + timedelta(days=int(s[:-1]))
    if s.endswith("w"):
        return now + timedelta(weeks=int(s[:-1]))
    return now + timedelta(days=7)


async def _live_load_opportunity_full(opportunity_id: str, user_id: str) -> dict[str, Any]:
    """Load full opportunity context for ActionGeneratorAgent."""
    import asyncpg  # noqa: PLC0415
    import uuid as _uuid  # noqa: PLC0415
    from app.db.session import get_asyncpg_db_url  # noqa: PLC0415

    conn = await asyncpg.connect(get_asyncpg_db_url(), statement_cache_size=0)
    try:
        opp_row = await conn.fetchrow(
            """
            SELECT o.predicted_role, o.confidence, o.timeline_weeks, o.why_fit,
                   o.approach_angle, o.fit_score, o.company_id,
                   c.name AS company_name
            FROM opportunities o
            LEFT JOIN companies c ON c.id = o.company_id
            WHERE o.id = $1 AND o.user_id = $2
            """,
            _uuid.UUID(opportunity_id),
            _uuid.UUID(user_id),
        )
        profile_row = await conn.fetchrow(
            "SELECT current_role, aspirations_text FROM career_profiles WHERE user_id = $1",
            _uuid.UUID(user_id),
        )
    finally:
        await conn.close()

    if not opp_row:
        raise ValueError(f"Opportunity {opportunity_id} not found for user {user_id}")

    return {
        "opportunity": {
            "predicted_role": opp_row["predicted_role"] or "",
            "confidence": opp_row["confidence"],
            "timeline_weeks": opp_row["timeline_weeks"] or 8,
            "why_fit": opp_row["why_fit"] or "",
            "ideal_contact_title": "",
            "company_name": opp_row["company_name"] or "",
        },
        "fit_score": float(opp_row["fit_score"] or 50.0),
        "company_id": str(opp_row["company_id"]) if opp_row["company_id"] else None,
        "contacts": [],
        "user_profile": {
            "current_role": profile_row["current_role"] if profile_row else "",
            "aspirations_text": profile_row["aspirations_text"] if profile_row else "",
            "skills": [],
            "career_history_summary": "",
        },
        "company_signals": [],
    }


async def _live_store_actions(
    user_id: str,
    company_id: str | None,
    opportunity_id: str,
    actions: list[dict],
) -> None:
    """INSERT generated action items into the actions table."""
    import asyncpg  # noqa: PLC0415
    import uuid as _uuid  # noqa: PLC0415
    from app.db.session import get_asyncpg_db_url  # noqa: PLC0415

    if not actions:
        return

    conn = await asyncpg.connect(get_asyncpg_db_url(), statement_cache_size=0)
    try:
        for action in actions:
            due_date = _parse_due_date(action.get("due_date", "+7d"))
            await conn.execute(
                """
                INSERT INTO actions (
                    id, user_id, opportunity_id, company_id,
                    title, type, priority, status, due_date, ai_draft_json, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, 'TODO', $8, '{}', NOW())
                """,
                _uuid.uuid4(),
                _uuid.UUID(user_id),
                _uuid.UUID(opportunity_id),
                _uuid.UUID(company_id) if company_id else None,
                action.get("title", "")[:200],
                action.get("type", "OUTREACH"),
                action.get("priority", "MEDIUM"),
                due_date,
            )
    finally:
        await conn.close()


# ── Tasks ──────────────────────────────────────────────────────────────────────

@celery_app.task(
    name="app.workers.generate_actions.generate_actions_for_opportunity",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    queue="default",
)
def generate_actions_for_opportunity(
    self, user_id: str, opportunity_id: str
) -> dict[str, Any]:
    """
    Run ActionGeneratorAgent for a user + opportunity after fit scoring completes.

    Steps:
      1. Load opportunity + fit_score + contacts (or mock under USE_MOCK_DATA)
      2. Run ActionGeneratorAgent
      3. Store generated actions in DB (or mock)

    Args:
        user_id:        Supabase user UUID.
        opportunity_id: Opportunity UUID.

    Returns:
        dict with keys: opportunity_id, actions_count, actions (list of dicts)
    """
    settings = _get_settings()

    async def _run() -> dict[str, Any]:
        from app.agents.action_generator import (
            ActionGeneratorAgent,
            ActionGeneratorInput,
            OpportunityForActions,
            ContactSummary,
        )

        # 1. Load context
        if settings.USE_MOCK_DATA:
            ctx = _load_mock_opportunity_full(opportunity_id, user_id)
        else:
            ctx = await _live_load_opportunity_full(opportunity_id, user_id)

        # 2. Run agent
        agent = ActionGeneratorAgent(settings=settings)
        generator_input = ActionGeneratorInput(
            user_id=user_id,
            opportunity_id=opportunity_id,
            opportunity=OpportunityForActions(**ctx["opportunity"]),
            fit_score=ctx["fit_score"],
            contacts=[ContactSummary(**c) for c in ctx.get("contacts", [])],
        )
        output = await agent.generate(generator_input)

        # 3. Store actions
        actions_as_dicts = [a.model_dump(mode="json") for a in output.actions]
        company_id = ctx.get("company_id")
        if settings.USE_MOCK_DATA:
            _mock_store_actions(user_id, opportunity_id, actions_as_dicts)
        else:
            await _live_store_actions(user_id, company_id, opportunity_id, actions_as_dicts)

        logger.info(
            "generate_actions_for_opportunity: opp=%s → %d actions stored",
            opportunity_id,
            len(output.actions),
        )
        return {
            "opportunity_id": opportunity_id,
            "actions_count": len(output.actions),
            "actions": actions_as_dicts,
        }

    try:
        return asyncio.run(_run())
    except Exception as exc:
        logger.error(
            "generate_actions_for_opportunity failed user=%s opp=%s: %s",
            user_id, opportunity_id, exc, exc_info=True,
        )
        raise self.retry(exc=exc)


@celery_app.task(
    name="app.workers.generate_actions.advise_positioning",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    queue="default",
)
def advise_positioning(self, user_id: str, opportunity_id: str) -> dict[str, Any]:
    """
    Run PositioningAdvisorAgent for a user + opportunity.

    Runs in parallel with CareerFitScorer after OpportunityPredictor completes.

    Steps:
      1. Load user profile + opportunity + company signals (or mock)
      2. Run PositioningAdvisorAgent
      3. Store positioning notes on the opportunity record (or mock)

    Args:
        user_id:        Supabase user UUID.
        opportunity_id: Opportunity UUID.

    Returns:
        dict with keys: opportunity_id, approach_angle, talking_points_count
    """
    settings = _get_settings()

    async def _run() -> dict[str, Any]:
        from app.agents.positioning_advisor import (
            PositioningAdvisorAgent,
            PositioningAdvisorInput,
            UserProfileForPositioning,
            OpportunityForPositioning,
            CompanySignalForPositioning,
        )

        # 1. Load context
        if settings.USE_MOCK_DATA:
            ctx = _load_mock_opportunity_full(opportunity_id, user_id)
        else:
            raise NotImplementedError(
                "Live DB reads not yet wired — set USE_MOCK_DATA=true"
            )

        # 2. Run agent
        agent = PositioningAdvisorAgent(settings=settings)
        advisor_input = PositioningAdvisorInput(
            user_id=user_id,
            opportunity_id=opportunity_id,
            user_profile=UserProfileForPositioning(**ctx["user_profile"]),
            opportunity=OpportunityForPositioning(
                predicted_role=ctx["opportunity"]["predicted_role"],
                confidence=ctx["opportunity"]["confidence"],
                why_fit=ctx["opportunity"]["why_fit"],
                ideal_contact_title=ctx["opportunity"].get("ideal_contact_title", ""),
            ),
            company_signals=[
                CompanySignalForPositioning(**s) for s in ctx.get("company_signals", [])
            ],
        )
        output = await agent.advise(advisor_input)

        # 3. Store positioning on opportunity
        positioning_dict = output.model_dump(mode="json")
        if settings.USE_MOCK_DATA:
            _mock_store_positioning(opportunity_id, positioning_dict)
        else:
            raise NotImplementedError(
                "Live DB writes not yet wired — set USE_MOCK_DATA=true"
            )

        logger.info(
            "advise_positioning: opp=%s approach=%s",
            opportunity_id,
            output.approach_angle[:60],
        )
        return {
            "opportunity_id": opportunity_id,
            "approach_angle": output.approach_angle,
            "talking_points_count": len(output.key_talking_points),
        }

    try:
        return asyncio.run(_run())
    except Exception as exc:
        logger.error(
            "advise_positioning failed user=%s opp=%s: %s",
            user_id, opportunity_id, exc, exc_info=True,
        )
        raise self.retry(exc=exc)


@celery_app.task(
    name="app.workers.generate_actions.run_reasoning_pipeline",
    queue="default",
)
def run_reasoning_pipeline(user_id: str, company_id: str) -> dict[str, Any]:
    """
    Run the full AI reasoning pipeline for a user + company.

    Pipeline (synchronous chain via .apply()):
      1. predict_for_company → opportunity_id
      2. [parallel] score_opportunity_fit + advise_positioning
      3. generate_actions_for_opportunity

    This is the single entry point to kick off the entire Phase 4 pipeline.

    Args:
        user_id:    Supabase user UUID.
        company_id: Company UUID.

    Returns:
        Combined result dict with keys from all pipeline steps.
    """
    from app.workers.predict_opportunities import predict_for_company, score_opportunity_fit

    # Step 1: predict
    predict_result = predict_for_company.apply(args=[user_id, company_id]).get()
    opportunity_id = predict_result["opportunity_id"]

    # Step 2: parallel (score + position) — run both synchronously via apply()
    score_result = score_opportunity_fit.apply(args=[user_id, opportunity_id]).get()
    position_result = advise_positioning.apply(args=[user_id, opportunity_id]).get()

    # Step 3: generate actions (uses fit_score from score_result via mock context)
    actions_result = generate_actions_for_opportunity.apply(
        args=[user_id, opportunity_id]
    ).get()

    return {
        **predict_result,
        **score_result,
        **position_result,
        **actions_result,
        "pipeline": "run_reasoning_pipeline",
    }
