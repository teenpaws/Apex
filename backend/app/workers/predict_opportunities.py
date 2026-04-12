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
        "positioning_notes": "Lead with your HEC Paris network and AI consulting background.",
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
            raise NotImplementedError(
                "Live DB reads not yet wired — set USE_MOCK_DATA=true"
            )

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
            raise NotImplementedError(
                "Live DB writes not yet wired — set USE_MOCK_DATA=true"
            )

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
            raise NotImplementedError(
                "Live DB reads not yet wired — set USE_MOCK_DATA=true"
            )

        # 2. Run agent
        agent = CareerFitScorerAgent(settings=settings)
        scorer_input = CareerFitScorerInput(
            user_id=user_id,
            opportunity_id=opportunity_id,
            opportunity=OpportunitySummary(
                predicted_role=opp_data["predicted_role"],
                confidence=opp_data["confidence"],
                why_fit=opp_data["why_fit"],
                positioning_notes=opp_data.get("positioning_notes", ""),
            ),
            user_profile=UserProfileForScoring(**profile_data),
        )
        output = await agent.score(scorer_input)

        # 3. Update opportunity with fit score
        if settings.USE_MOCK_DATA:
            _mock_update_opportunity_fit(opportunity_id, output.fit_score)
        else:
            raise NotImplementedError(
                "Live DB writes not yet wired — set USE_MOCK_DATA=true"
            )

        logger.info(
            "score_opportunity_fit: opp=%s fit_score=%.1f gaps=%s",
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
