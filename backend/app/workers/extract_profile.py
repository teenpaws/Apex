"""
Celery worker for profile extraction from user-uploaded documents.

Flow:
  1. Fetch all EXTRACTED user_documents for the user
  2. Build ProfileExtractorInput (resume + cover_letters list)
  3. Call ProfileExtractorAgent
  4. Store output as extraction_staging_json on career_profiles
  5. Mark documents as ANALYZED

In mock mode (USE_MOCK_DATA=True): returns success without any DB/agent calls.
"""
from __future__ import annotations

import asyncio
import logging

from celery.utils.log import get_task_logger

from app.core.celery_app import celery_app
from app.core.config import get_settings

logger = get_task_logger(__name__)


@celery_app.task(
    name="app.workers.extract_profile.extract_profile_from_documents",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    queue="default",
)
def extract_profile_from_documents(self, user_id: str) -> dict:
    """Celery task: extract structured profile from all uploaded documents.

    Args:
        user_id: Supabase user UUID string.

    Returns:
        dict with keys: status, user_id, and optionally mock=True.
    """
    settings = get_settings()

    if settings.USE_MOCK_DATA:
        logger.info("[mock] extract_profile_from_documents user_id=%s", user_id)
        return {"status": "SUCCESS", "user_id": user_id, "mock": True}

    try:
        return asyncio.run(_run_extraction(user_id, settings))
    except Exception as exc:
        logger.error("extract_profile_from_documents failed: %s", exc, exc_info=True)
        raise self.retry(exc=exc, countdown=30)


async def _run_extraction(user_id: str, settings) -> dict:
    import json
    import uuid as _uuid
    import asyncpg
    from app.db.session import get_asyncpg_db_url
    from app.agents.profile_extractor import ProfileExtractorAgent, ProfileExtractorInput, CoverLetterInput

    conn = await asyncpg.connect(get_asyncpg_db_url(), statement_cache_size=0)
    try:
        rows = await conn.fetch(
            """SELECT id, doc_type, target_context, extracted_text
               FROM user_documents
               WHERE user_id = $1 AND extraction_status = 'EXTRACTED'
               ORDER BY doc_type, created_at""",
            _uuid.UUID(user_id),
        )

        if not rows:
            logger.warning("No EXTRACTED documents found for user_id=%s", user_id)
            return {"status": "NO_DOCUMENTS", "user_id": user_id}

        resume_text = ""
        cover_letters: list[CoverLetterInput] = []
        doc_ids: list[_uuid.UUID] = []

        for row in rows:
            doc_ids.append(row["id"])
            text = row["extracted_text"] or ""
            if row["doc_type"] == "RESUME":
                resume_text = text
            elif row["doc_type"] == "COVER_LETTER":
                cover_letters.append(
                    CoverLetterInput(
                        text=text,
                        target_context=row["target_context"] or "general",
                    )
                )

        # Fetch existing profile for context
        profile_row = await conn.fetchrow(
            'SELECT "current_role", target_roles, industries, aspirations_text FROM career_profiles WHERE user_id = $1',
            _uuid.UUID(user_id),
        )
        existing = {}
        if profile_row:
            existing = {
                "current_role": profile_row["current_role"],
                "target_roles": list(profile_row["target_roles"] or []),
                "industries": list(profile_row["industries"] or []),
                "aspirations_text": profile_row["aspirations_text"],
            }

        agent = ProfileExtractorAgent(settings=settings)
        output = await agent.extract(
            ProfileExtractorInput(
                user_id=user_id,
                resume_text=resume_text,
                cover_letters=cover_letters,
                existing_profile=existing,
            )
        )

        staging = output.model_dump(mode="json")

        # Write staging JSON to career_profiles
        await conn.execute(
            """UPDATE career_profiles
               SET extraction_staging_json = $1, raw_resume_text = $2
               WHERE user_id = $3""",
            json.dumps(staging),
            resume_text or None,
            _uuid.UUID(user_id),
        )

        # Mark all processed documents as ANALYZED
        await conn.execute(
            "UPDATE user_documents SET extraction_status = 'ANALYZED' WHERE id = ANY($1)",
            doc_ids,
        )

    finally:
        await conn.close()

    return {"status": "SUCCESS", "user_id": user_id}
