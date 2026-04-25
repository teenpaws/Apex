"""
Celery workers for opportunity prediction and career fit scoring.

Tasks:
  predict_for_company        — Run OpportunityPredictorAgent for a user + company
  score_opportunity_fit      — Run CareerFitScorerAgent for a user + opportunity
  predict_and_score          — Chain predict_for_company → score_opportunity_fit
  run_parallel_scoring       — Run CareerFitScorer + PositioningAdvisor in parallel

Pipeline position (triggered after signal classification):
  SignalClassifier (Phase 3)
    → predict_for_company
      → [parallel] score_opportunity_fit + positioning_advisor (Phase 5 wires advisor)
        → [join] → generate_actions_for_opportunity (generate_actions worker)

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
from app.integrations.adzuna_client import AdzunaClient
from app.services.opportunity_validator import OpportunityValidatorService

logger = get_task_logger(__name__)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _get_settings():
    return get_settings()


def _load_mock_company_context(user_id: str, company_id: str) -> dict[str, Any]:
    """
    Return mock company + signals context for development (USE_MOCK_DATA=true).

    In production this would query Supabase for company record + recent signals.
    """
    return {
        "company_name": "McKinsey & Company",
        "signals": [
            {
                "signal_id": "sig-001",
                "signal_type": "FUNDING",
                "title": "McKinsey Raises $500M for Digital Transformation Fund",
                "description": (
                    "McKinsey & Company announced a new $500M digital transformation "
                    "fund to expand its AI and data analytics practice globally. "
                    "The firm plans to hire 2,000 new consultants specialising in AI strategy."
                ),
                "signal_date": "2026-04-10T09:00:00Z",
                "relevance_score": 0.92,
            },
            {
                "signal_id": "sig-002",
                "signal_type": "EXEC_HIRE",
                "title": "McKinsey Appoints New Global Head of AI Practice",
                "description": (
                    "McKinsey has appointed a new Global Head of AI Practice, "
                    "signalling an intensified push into enterprise AI strategy consulting."
                ),
                "signal_date": "2026-04-08T14:00:00Z",
                "relevance_score": 0.85,
            },
        ],
        "user_profile": {
            "current_role": "Senior Strategy Consultant",
            "target_roles": ["Principal", "VP Strategy", "Strategy Director"],
            "industries": ["Consulting", "Technology", "Financial Services"],
            "aspirations_text": (
                "I want to move into a principal-level strategy role where I can "
                "lead AI transformation projects for global enterprises."
            ),
            "skills": ["Strategy", "AI/ML", "Change Management", "Executive Stakeholder Management"],
        },
    }


def _load_mock_opportunity(opportunity_id: str, user_id: str) -> dict[str, Any]:
    """Return mock opportunity data for USE_MOCK_DATA=true."""
    return {
        "opportunity_id": opportunity_id,
        "predicted_role": "VP of Strategy",
        "confidence": "HIGH",
        "timeline_weeks": 6,
        "why_fit": (
            "Your MBA background and AI strategy experience align directly with "
            "McKinsey's new digital transformation push."
        ),
        "approach_angle": "Lead with your HEC Paris network and AI consulting background.",
        "ideal_contact_title": "Chief of Staff or Partner",
        "company_name": "McKinsey & Company",
    }


def _mock_store_opportunity(user_id: str, company_id: str, opportunity: dict) -> str:
    """Log what a real DB insert would do. Returns a fake opportunity_id."""
    opportunity_id = f"opp-mock-{company_id[:8]}"
    logger.info(
        "[mock] DB insert — opportunities: user=%s company=%s role=%s confidence=%s → id=%s",
        user_id,
        company_id,
        opportunity.get("predicted_role"),
        opportunity.get("confidence"),
        opportunity_id,
    )
    return opportunity_id


def _mock_update_opportunity_fit(opportunity_id: str, fit_score: float) -> None:
    """Log what a real DB update would do."""
    logger.info(
        "[mock] DB update — opportunities: id=%s fit_score=%.1f",
        opportunity_id,
        fit_score,
    )


# ── Live DB helpers ────────────────────────────────────────────────────────────

async def _live_load_company_context(user_id: str, company_id: str) -> dict[str, Any]:
    """Load company signals + user career profile from Supabase."""
    import asyncpg  # noqa: PLC0415
    import uuid as _uuid  # noqa: PLC0415
    from app.db.session import get_asyncpg_db_url  # noqa: PLC0415

    conn = await asyncpg.connect(get_asyncpg_db_url(), statement_cache_size=0)
    try:
        company_row = await conn.fetchrow(
            "SELECT name FROM companies WHERE id = $1",
            _uuid.UUID(company_id),
        )
        signal_rows = await conn.fetch(
            """
            SELECT id, type, title, description, signal_date, relevance_score
            FROM signals
            WHERE company_id = $1 AND user_id = $2
              AND processed_at IS NOT NULL AND relevance_score >= 0.4
              AND is_duplicate = false
            ORDER BY relevance_score DESC
            LIMIT 10
            """,
            _uuid.UUID(company_id),
            _uuid.UUID(user_id),
        )
        profile_row = await conn.fetchrow(
            """
            SELECT current_role, target_roles, industries, aspirations_text
            FROM career_profiles WHERE user_id = $1
            """,
            _uuid.UUID(user_id),
        )
    finally:
        await conn.close()

    return {
        "company_name": company_row["name"] if company_row else "Unknown",
        "signals": [
            {
                "signal_id": str(r["id"]),
                "signal_type": r["type"],
                "title": r["title"] or "",
                "description": r["description"] or "",
                "signal_date": r["signal_date"].isoformat() if r["signal_date"] else "",
                "relevance_score": float(r["relevance_score"] or 0.0),
            }
            for r in signal_rows
        ],
        "user_profile": {
            "current_role": profile_row["current_role"] or "" if profile_row else "",
            "target_roles": list(profile_row["target_roles"] or []) if profile_row else [],
            "industries": list(profile_row["industries"] or []) if profile_row else [],
            "aspirations_text": profile_row["aspirations_text"] or "" if profile_row else "",
            "skills": [],
        },
    }


async def _live_store_opportunity(
    user_id: str,
    company_id: str,
    output: Any,
) -> str:
    """INSERT a new opportunity row and return its UUID string."""
    import asyncpg  # noqa: PLC0415
    import uuid as _uuid  # noqa: PLC0415
    from app.db.session import get_asyncpg_db_url  # noqa: PLC0415

    opportunity_id = str(_uuid.uuid4())
    conn = await asyncpg.connect(get_asyncpg_db_url(), statement_cache_size=0)
    try:
        await conn.execute(
            """
            INSERT INTO opportunities (
                id, user_id, company_id, predicted_role, confidence,
                timeline_weeks, why_fit, approach_angle,
                status, created_at, updated_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 'PREDICTED', NOW(), NOW())
            """,
            _uuid.UUID(opportunity_id),
            _uuid.UUID(user_id),
            _uuid.UUID(company_id),
            output.predicted_role,
            output.confidence,
            output.timeline_weeks,
            output.why_fit,
            output.approach_angle,
        )
    finally:
        await conn.close()
    return opportunity_id


async def _live_load_opportunity_for_scoring(
    opportunity_id: str,
    user_id: str,
) -> dict[str, Any]:
    """Load opportunity + user profile for CareerFitScorerAgent."""
    import asyncpg  # noqa: PLC0415
    import uuid as _uuid  # noqa: PLC0415
    from app.db.session import get_asyncpg_db_url  # noqa: PLC0415

    conn = await asyncpg.connect(get_asyncpg_db_url(), statement_cache_size=0)
    try:
        opp_row = await conn.fetchrow(
            """
            SELECT predicted_role, confidence, why_fit, approach_angle
            FROM opportunities WHERE id = $1 AND user_id = $2
            """,
            _uuid.UUID(opportunity_id),
            _uuid.UUID(user_id),
        )
        profile_row = await conn.fetchrow(
            """
            SELECT current_role, target_roles, industries, aspirations_text
            FROM career_profiles WHERE user_id = $1
            """,
            _uuid.UUID(user_id),
        )
    finally:
        await conn.close()

    return {
        "opp_data": {
            "predicted_role": opp_row["predicted_role"] or "" if opp_row else "",
            "confidence": opp_row["confidence"] if opp_row else "SPECULATIVE",
            "why_fit": opp_row["why_fit"] or "" if opp_row else "",
            "approach_angle": opp_row["approach_angle"] or "" if opp_row else "",
        },
        "profile_data": {
            "current_role": profile_row["current_role"] or "" if profile_row else "",
            "target_roles": list(profile_row["target_roles"] or []) if profile_row else [],
            "industries": list(profile_row["industries"] or []) if profile_row else [],
            "aspirations_text": profile_row["aspirations_text"] or "" if profile_row else "",
            "skills": [],
            "embedding_summary": "",
        },
    }


async def _live_update_fit_score(
    opportunity_id: str,
    user_id: str,
    fit_score: float,
) -> None:
    """UPDATE opportunities.fit_score after CareerFitScorer runs."""
    import asyncpg  # noqa: PLC0415
    import uuid as _uuid  # noqa: PLC0415
    from app.db.session import get_asyncpg_db_url  # noqa: PLC0415

    conn = await asyncpg.connect(get_asyncpg_db_url(), statement_cache_size=0)
    try:
        await conn.execute(
            "UPDATE opportunities SET fit_score = $1, updated_at = NOW() WHERE id = $2 AND user_id = $3",
            fit_score,
            _uuid.UUID(opportunity_id),
            _uuid.UUID(user_id),
        )
    finally:
        await conn.close()


# ── Tasks ──────────────────────────────────────────────────────────────────────

@celery_app.task(
    name="app.workers.predict_opportunities.predict_for_company",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    queue="default",
)
def predict_for_company(self, user_id: str, company_id: str) -> dict[str, Any]:
    """
    Run OpportunityPredictorAgent for a user + company pair.

    Triggered automatically after signal classification completes for a company.

    Steps:
      1. Load company signals + user profile (or mock under USE_MOCK_DATA)
      2. Run OpportunityPredictorAgent
      3. Store predicted opportunity in DB (or mock)
      4. Queue score_opportunity_fit for the new opportunity

    Args:
        user_id:    Supabase user UUID.
        company_id: Company UUID.

    Returns:
        dict with keys: opportunity_id, predicted_role, confidence, company_id
    """
    settings = _get_settings()

    async def _run() -> dict[str, Any]:
        from app.agents.opportunity_predictor import (
            OpportunityPredictorAgent,
            OpportunityPredictorInput,
            SignalSummary,
            UserProfileSummary,
        )

        # 1. Load context
        if settings.USE_MOCK_DATA:
            ctx = _load_mock_company_context(user_id, company_id)
        else:
            ctx = await _live_load_company_context(user_id, company_id)

        # 2. Build input and run agent
        agent = OpportunityPredictorAgent(settings=settings)
        predictor_input = OpportunityPredictorInput(
            user_id=user_id,
            company_id=company_id,
            company_name=ctx["company_name"],
            company_signals=[SignalSummary(**s) for s in ctx["signals"]],
            user_profile=UserProfileSummary(**ctx["user_profile"]),
        )
        output = await agent.predict(predictor_input)

        # 3. Store opportunity
        if settings.USE_MOCK_DATA:
            opportunity_id = _mock_store_opportunity(
                user_id, company_id, output.model_dump(mode="json")
            )
        else:
            opportunity_id = await _live_store_opportunity(user_id, company_id, output)

            # Adzuna validation — only when real API credentials are configured
            if (
                not settings.ADZUNA_APP_ID.startswith("placeholder")
                and output.predicted_role
            ):
                try:
                    adzuna = AdzunaClient(
                        app_id=settings.ADZUNA_APP_ID,
                        app_key=settings.ADZUNA_APP_KEY,
                        country=settings.ADZUNA_COUNTRY,
                    )
                    validator = OpportunityValidatorService(adzuna_client=adzuna)
                    val_result = await validator.validate(
                        company_name=ctx["company_name"],
                        predicted_role=output.predicted_role,
                    )
                    if val_result.is_validated:
                        import asyncpg as _asyncpg  # noqa: PLC0415
                        import uuid as _uuid  # noqa: PLC0415
                        from app.db.session import get_asyncpg_db_url as _get_db_url  # noqa: PLC0415
                        _conn = await _asyncpg.connect(_get_db_url(), statement_cache_size=0)
                        try:
                            await _conn.execute(
                                """
                                UPDATE opportunities
                                SET real_postings = $1, status = 'VALIDATED', updated_at = now()
                                WHERE id = $2
                                """,
                                val_result.real_postings,  # pass list directly — asyncpg encodes to JSONB
                                _uuid.UUID(opportunity_id),
                            )
                        finally:
                            await _conn.close()
                        logger.info(
                            "Opportunity %s VALIDATED — %d Adzuna postings found",
                            opportunity_id, len(val_result.real_postings),
                        )
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Adzuna validation skipped: %s", exc)

        # 4. Queue fit scoring
        logger.info(
            "predict_for_company: company=%s → role=%s confidence=%s, "
            "queueing score_opportunity_fit for opp=%s",
            company_id,
            output.predicted_role,
            output.confidence,
            opportunity_id,
        )
        score_opportunity_fit.apply_async(
            args=[user_id, opportunity_id],
            queue="default",
        )

        return {
            "opportunity_id": opportunity_id,
            "predicted_role": output.predicted_role,
            "confidence": output.confidence,
            "company_id": company_id,
        }

    try:
        return asyncio.run(_run())
    except Exception as exc:
        logger.error(
            "predict_for_company failed user=%s company=%s: %s",
            user_id, company_id, exc, exc_info=True,
        )
        raise self.retry(exc=exc)


@celery_app.task(
    name="app.workers.predict_opportunities.score_opportunity_fit",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    queue="default",
)
def score_opportunity_fit(self, user_id: str, opportunity_id: str) -> dict[str, Any]:
    """
    Run CareerFitScorerAgent for a user + opportunity pair.

    Steps:
      1. Load opportunity + user profile (or mock under USE_MOCK_DATA)
      2. Run CareerFitScorerAgent
      3. Update opportunity.fit_score in DB (or mock)

    Args:
        user_id:        Supabase user UUID.
        opportunity_id: Opportunity UUID.

    Returns:
        dict with keys: opportunity_id, fit_score, skill_gaps
    """
    settings = _get_settings()

    async def _run() -> dict[str, Any]:
        from app.agents.career_fit_scorer import (
            CareerFitScorerAgent,
            CareerFitScorerInput,
            OpportunitySummary,
            UserProfileForScoring,
        )

        # 1. Load context
        if settings.USE_MOCK_DATA:
            opp_data = _load_mock_opportunity(opportunity_id, user_id)
            profile_data = _load_mock_company_context(user_id, "mock")["user_profile"]
        else:
            ctx = await _live_load_opportunity_for_scoring(opportunity_id, user_id)
            opp_data = ctx["opp_data"]
            profile_data = ctx["profile_data"]

        # 2. Run agent
        agent = CareerFitScorerAgent(settings=settings)
        scorer_input = CareerFitScorerInput(
            user_id=user_id,
            opportunity_id=opportunity_id,
            opportunity=OpportunitySummary(
                predicted_role=opp_data["predicted_role"],
                confidence=opp_data["confidence"],
                why_fit=opp_data["why_fit"],
                approach_angle=opp_data.get("approach_angle", ""),
            ),
            user_profile=UserProfileForScoring(**profile_data),
        )
        output = await agent.score(scorer_input)

        # 3. Update opportunity with fit score
        if settings.USE_MOCK_DATA:
            _mock_update_opportunity_fit(opportunity_id, output.fit_score)
        else:
            await _live_update_fit_score(opportunity_id, user_id, output.fit_score)

        # 4. Chain to action generation
        from app.workers.generate_actions import generate_actions_for_opportunity  # noqa: PLC0415
        generate_actions_for_opportunity.apply_async(
            args=[user_id, opportunity_id],
            queue="default",
        )

        logger.info(
            "score_opportunity_fit: opp=%s fit_score=%.1f gaps=%s → queued action generation",
            opportunity_id,
            output.fit_score,
            output.skill_gaps,
        )
        return {
            "opportunity_id": opportunity_id,
            "fit_score": output.fit_score,
            "skill_gaps": output.skill_gaps,
        }

    try:
        return asyncio.run(_run())
    except Exception as exc:
        logger.error(
            "score_opportunity_fit failed user=%s opp=%s: %s",
            user_id, opportunity_id, exc, exc_info=True,
        )
        raise self.retry(exc=exc)


@celery_app.task(
    name="app.workers.predict_opportunities.predict_and_score",
    queue="default",
)
def predict_and_score(user_id: str, company_id: str) -> dict[str, Any]:
    """
    Convenience task that chains predict_for_company → score_opportunity_fit.

    Calls tasks synchronously via .apply() so the full chain runs inline
    and returns a combined result dict.

    Args:
        user_id:    Supabase user UUID.
        company_id: Company UUID.

    Returns:
        Combined result dict from both steps.
    """
    predict_result = predict_for_company.apply(args=[user_id, company_id]).get()
    opportunity_id = predict_result.get("opportunity_id")

    score_result = score_opportunity_fit.apply(args=[user_id, opportunity_id]).get()

    return {
        **predict_result,
        **score_result,
        "pipeline": "predict_and_score",
    }
