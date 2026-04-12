"""
Celery workers for signal classification and embedding.

Tasks:
  classify_signal      — Classify a single signal via SignalClassifierAgent
  batch_classify_signals — Fan-out classify_signal across many signal IDs
  embed_signal         — Generate and store a 1536-dim embedding for a signal
  classify_and_embed   — Chain classify_signal → embed_signal for one signal

Pipeline gate (in classify_signal):
  relevance_score < 0.4  → mark signal low-relevance, stop pipeline
  relevance_score >= 0.4 → queue embed_signal; ready for opportunity prediction

All tasks are sync Celery tasks that run async agent logic via asyncio.run().
Under USE_MOCK_DATA=true no real DB reads/writes occur — mock data is used.
Under MOCK_AGENTS=true no Claude API calls are made — fixture data is returned.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from celery.utils.log import get_task_logger

from app.core.celery_app import celery_app
from app.core.config import get_settings

logger = get_task_logger(__name__)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _get_settings():
    """Return settings (deferred so tasks import cleanly before app boots)."""
    return get_settings()


def _load_mock_signal(signal_id: str) -> dict[str, Any]:
    """
    Return a mock signal record for development (USE_MOCK_DATA=true).

    In production this would be a Supabase/SQLAlchemy query.
    """
    return {
        "id": signal_id,
        "title": "Acme Corp Raises $45M Series B to Expand EMEA Operations",
        "description": (
            "Acme Corp, a B2B fintech SaaS platform, announced a $45M Series B "
            "led by Sequoia Capital. The company plans to double headcount and "
            "open offices in London and Paris to serve European enterprise clients."
        ),
        "source": "newsdata.io",
        "signal_date": datetime.now(timezone.utc).isoformat(),
        "company_name": "Acme Corp",
        "user_target_industries": ["Fintech", "SaaS", "Consulting"],
        "user_target_roles": ["Strategy", "Operations", "Business Development"],
    }


def _mock_update_signal(
    signal_id: str,
    signal_type: str,
    relevance_score: float,
) -> None:
    """Log what a real DB update would do (USE_MOCK_DATA=true)."""
    logger.info(
        "[mock] DB update — signal %s: type=%s relevance=%.2f processed_at=now",
        signal_id,
        signal_type,
        relevance_score,
    )


def _mock_store_embedding(signal_id: str) -> None:
    """Log what a real embedding DB write would do (USE_MOCK_DATA=true)."""
    logger.info(
        "[mock] DB update — signal %s: embedding stored (1536 zeros)", signal_id
    )


# ── Tasks ──────────────────────────────────────────────────────────────────────

@celery_app.task(
    name="app.workers.classify_signals.classify_signal",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    queue="default",
)
def classify_signal(self, signal_id: str) -> dict[str, Any]:
    """
    Classify a single market signal using the SignalClassifierAgent.

    Steps:
      1. Load signal from DB (or mock under USE_MOCK_DATA)
      2. Run SignalClassifierAgent
      3. Apply gate: relevance_score < 0.4 → low-relevance, stop
      4. Update signal record with type + relevance_score + processed_at
      5. Queue embed_signal for relevant signals

    Args:
        signal_id: UUID string of the signal to classify.

    Returns:
        dict with keys: signal_id, signal_type, relevance_score, gated_out
    """
    settings = _get_settings()

    async def _run() -> dict[str, Any]:
        # 1. Load signal
        if settings.USE_MOCK_DATA:
            signal_data = _load_mock_signal(signal_id)
        else:
            # Production: query Supabase/SQLAlchemy
            # from app.db.session import get_async_session
            # async with get_async_session() as session:
            #     signal = await session.get(SignalORM, signal_id)
            raise NotImplementedError(
                "Live DB reads not yet wired — set USE_MOCK_DATA=true"
            )

        # 2. Run the classifier agent
        from app.agents.signal_classifier import SignalClassifierAgent, SignalClassifierInput

        agent = SignalClassifierAgent(settings=settings)
        classifier_input = SignalClassifierInput(
            signal_id=signal_data["id"],
            title=signal_data["title"],
            description=signal_data["description"],
            source=signal_data["source"],
            signal_date=datetime.fromisoformat(signal_data["signal_date"])
            if isinstance(signal_data["signal_date"], str)
            else signal_data["signal_date"],
            company_name=signal_data["company_name"],
            user_target_industries=signal_data.get("user_target_industries", []),
            user_target_roles=signal_data.get("user_target_roles", []),
        )

        output = await agent.classify(classifier_input)

        # 3. Pipeline gate
        gated_out = output.relevance_score < 0.4
        if gated_out:
            logger.info(
                "Signal %s gated out: relevance_score=%.2f < 0.4 threshold",
                signal_id,
                output.relevance_score,
            )
            if settings.USE_MOCK_DATA:
                _mock_update_signal(signal_id, output.signal_type, output.relevance_score)
            return {
                "signal_id": signal_id,
                "signal_type": output.signal_type,
                "relevance_score": output.relevance_score,
                "gated_out": True,
                "reason": "relevance_score below 0.4 threshold",
            }

        # 4. Update signal record
        if settings.USE_MOCK_DATA:
            _mock_update_signal(signal_id, output.signal_type, output.relevance_score)
        else:
            # Production DB update (to be wired when USE_MOCK_DATA=false)
            pass

        # 5. Queue embedding for relevant signals
        logger.info(
            "Signal %s classified: type=%s relevance=%.2f — queueing embed_signal",
            signal_id,
            output.signal_type,
            output.relevance_score,
        )
        embed_signal.apply_async(args=[signal_id], queue="low")

        return {
            "signal_id": signal_id,
            "signal_type": output.signal_type,
            "relevance_score": output.relevance_score,
            "gated_out": False,
        }

    try:
        return asyncio.run(_run())
    except Exception as exc:
        logger.error("classify_signal failed for %s: %s", signal_id, exc, exc_info=True)
        raise self.retry(exc=exc)


@celery_app.task(
    name="app.workers.classify_signals.batch_classify_signals",
    queue="default",
)
def batch_classify_signals(signal_ids: list[str]) -> dict[str, Any]:
    """
    Fan-out classify_signal across a list of signal IDs.

    Each signal is dispatched as an independent Celery task so they can
    be processed in parallel across available workers.

    Args:
        signal_ids: List of signal UUID strings.

    Returns:
        dict with key: queued (int count of tasks dispatched)
    """
    if not signal_ids:
        return {"queued": 0}

    for signal_id in signal_ids:
        classify_signal.delay(signal_id)

    logger.info("batch_classify_signals: dispatched %d tasks", len(signal_ids))
    return {"queued": len(signal_ids)}


@celery_app.task(
    name="app.workers.classify_signals.embed_signal",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    queue="low",
)
def embed_signal(self, signal_id: str) -> dict[str, Any]:
    """
    Generate and store a 1536-dim embedding for a signal.

    Uses OpenAI text-embedding-3-small on "title + description".
    Under MOCK_AGENTS=true: stores a list of 1536 zeros without calling OpenAI.

    Args:
        signal_id: UUID string of the signal to embed.

    Returns:
        dict with keys: signal_id, embedded (bool)
    """
    settings = _get_settings()

    async def _run() -> dict[str, Any]:
        if settings.MOCK_AGENTS:
            # Mock: fake 1536-dim zero vector (matches pgvector(1536) dimension)
            _mock_embedding = [0.0] * 1536
            _mock_store_embedding(signal_id)
            logger.info("[mock] embed_signal: signal %s embedded (1536 zeros)", signal_id)
            return {"signal_id": signal_id, "embedded": True}

        # Production path: call OpenAI embeddings API
        try:
            import openai  # noqa: PLC0415
        except ImportError as exc:
            raise RuntimeError(
                "openai package not installed. Run: pip install -r requirements.txt"
            ) from exc

        # Load signal text
        if settings.USE_MOCK_DATA:
            signal_data = _load_mock_signal(signal_id)
        else:
            raise NotImplementedError(
                "Live DB reads not yet wired — set USE_MOCK_DATA=true"
            )

        text_to_embed = f"{signal_data['title']}\n\n{signal_data['description']}"

        client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        response = await client.embeddings.create(
            model="text-embedding-3-small",
            input=text_to_embed,
        )
        embedding = response.data[0].embedding  # list[float], 1536 dims

        # Store embedding (production DB write)
        # await session.execute(
        #     update(SignalORM).where(SignalORM.id == signal_id).values(embedding=embedding)
        # )
        logger.info("embed_signal: signal %s embedded (%d dims)", signal_id, len(embedding))
        return {"signal_id": signal_id, "embedded": True}

    try:
        return asyncio.run(_run())
    except Exception as exc:
        logger.error("embed_signal failed for %s: %s", signal_id, exc, exc_info=True)
        raise self.retry(exc=exc)


@celery_app.task(
    name="app.workers.classify_signals.classify_and_embed",
    queue="default",
)
def classify_and_embed(signal_id: str) -> dict[str, Any]:
    """
    Convenience task that chains classify_signal → embed_signal for one signal.

    If classify_signal gates out the signal (relevance < 0.4), embed_signal is
    NOT called — the pipeline stops at the gate.

    Calls tasks synchronously via .apply() (not .delay()) so the chain runs
    inline within the current worker process and returns the combined result.

    Args:
        signal_id: UUID string of the signal to process.

    Returns:
        Combined result dict from both steps (or gate result if gated out).
    """
    classify_result = classify_signal.apply(args=[signal_id]).get()

    if classify_result.get("gated_out"):
        logger.info(
            "classify_and_embed: signal %s gated out, skipping embed", signal_id
        )
        return classify_result

    embed_result = embed_signal.apply(args=[signal_id]).get()

    return {
        **classify_result,
        **embed_result,
        "pipeline": "classify_and_embed",
    }
