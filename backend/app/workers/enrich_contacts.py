"""
Celery workers for contact and company enrichment.

Tasks:
  enrich_company      — PDL company enrichment; updates companies table
  enrich_contact      — PDL person enrichment + Hunter.io email finding
  find_key_contact    — PDL search → auto-create contact record
  batch_enrich        — Fan-out enrich_contact across a list of contact IDs

Quota-awareness:
  - PDL usage is tracked in agent_runs (agent_name="pdl_enrichment")
  - Enrichment queue is prioritised by opportunity fit_score
    (enrich_contact tasks for high-fit opportunities use the "high" queue)
  - On PDL 402 (quota exceeded) the task returns cached data rather than retrying

All tasks under USE_MOCK_DATA=true return deterministic mock data.
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


def _load_mock_company(company_id: str) -> dict[str, Any]:
    return {
        "id": company_id,
        "name": "McKinsey & Company",
        "domain": "mckinsey.com",
        "industry": "Consulting",
        "size_range": "30000-50000",
    }


def _load_mock_contact(contact_id: str) -> dict[str, Any]:
    return {
        "id": contact_id,
        "name": "Jane Smith",
        "title": "Chief of Staff",
        "company_name": "McKinsey & Company",
        "company_domain": "mckinsey.com",
        "linkedin_url": "https://linkedin.com/in/janesmith",
    }


def _mock_update_company_enrichment(company_id: str, profile: Any) -> None:
    logger.info(
        "[mock] DB update — companies: id=%s headcount=%s industry=%s",
        company_id,
        getattr(profile, "headcount", None),
        getattr(profile, "industry", None),
    )


def _mock_update_contact_enrichment(
    contact_id: str, profile: Any, email: str | None
) -> None:
    logger.info(
        "[mock] DB update — contacts: id=%s pdl_id=%s email=%s",
        contact_id,
        getattr(profile, "pdl_id", None),
        email,
    )


def _mock_create_contact(company_id: str, result: Any, email: str | None) -> str:
    contact_id = f"contact-mock-{company_id[:8]}-{getattr(result, 'pdl_id', 'x')[:8]}"
    logger.info(
        "[mock] DB insert — contacts: company=%s name=%s title=%s email=%s → id=%s",
        company_id,
        getattr(result, "full_name", ""),
        getattr(result, "job_title", ""),
        email,
        contact_id,
    )
    return contact_id


# ── Tasks ──────────────────────────────────────────────────────────────────────

@celery_app.task(
    name="app.workers.enrich_contacts.enrich_company",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    queue="low",
)
def enrich_company(self, company_id: str) -> dict[str, Any]:
    """
    Enrich a company record with PDL data (headcount, industry, founding year).

    Steps:
      1. Load company record from DB (or mock)
      2. Call PDLClient.enrich_company()
      3. Update company.enrichment_json + last_enriched_at in DB (or mock)

    On PDL quota exhaustion (404/402): logs warning and returns partial data.

    Args:
        company_id: Company UUID.

    Returns:
        dict with keys: company_id, enriched (bool), headcount, industry
    """
    settings = _get_settings()

    async def _run() -> dict[str, Any]:
        from app.integrations.pdl_client import PDLClient

        if settings.USE_MOCK_DATA:
            company = _load_mock_company(company_id)
        else:
            raise NotImplementedError("Live DB reads not yet wired")

        client = PDLClient()
        profile = await client.enrich_company(
            name=company["name"],
            domain=company.get("domain"),
        )

        if profile is None:
            logger.warning("enrich_company: PDL returned None for company=%s", company_id)
            return {"company_id": company_id, "enriched": False}

        if settings.USE_MOCK_DATA:
            _mock_update_company_enrichment(company_id, profile)
        else:
            raise NotImplementedError("Live DB writes not yet wired")

        return {
            "company_id": company_id,
            "enriched": True,
            "headcount": profile.headcount,
            "industry": profile.industry,
        }

    try:
        return asyncio.run(_run())
    except Exception as exc:
        logger.error("enrich_company failed id=%s: %s", company_id, exc, exc_info=True)
        raise self.retry(exc=exc)


@celery_app.task(
    name="app.workers.enrich_contacts.enrich_contact",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    queue="default",
)
def enrich_contact(
    self,
    contact_id: str,
    priority: str = "normal",
) -> dict[str, Any]:
    """
    Enrich a contact with PDL person data + Hunter.io email.

    Steps:
      1. Load contact record from DB (or mock)
      2. Call PDLClient.enrich_person() — 1 PDL credit
      3. Call HunterClient.find_email() — 1 Hunter request (only for high-priority)
      4. Update contact.enrichment_json + email in DB (or mock)

    Hunter.io is called only when priority="high" to preserve the 25/month quota.

    Args:
        contact_id: Contact UUID.
        priority:   "high" → call Hunter.io; "normal" → PDL only.

    Returns:
        dict with keys: contact_id, enriched (bool), email, pdl_id
    """
    settings = _get_settings()

    async def _run() -> dict[str, Any]:
        from app.integrations.pdl_client import PDLClient
        from app.integrations.hunter_client import HunterClient

        if settings.USE_MOCK_DATA:
            contact = _load_mock_contact(contact_id)
        else:
            raise NotImplementedError("Live DB reads not yet wired")

        # PDL enrichment
        pdl_client = PDLClient()
        name = contact.get("name", "")
        company = contact.get("company_name", "")
        linkedin_url = contact.get("linkedin_url")

        person = await pdl_client.enrich_person(
            name=name,
            company=company,
            linkedin_url=linkedin_url,
        )

        if person is None:
            logger.warning("enrich_contact: PDL returned None for contact=%s", contact_id)
            return {"contact_id": contact_id, "enriched": False, "email": None, "pdl_id": None}

        # Hunter.io email — only for high-priority contacts
        email: str | None = None
        if priority == "high":
            domain = contact.get("company_domain", "")
            if domain and person.first_name and person.last_name:
                hunter_client = HunterClient()
                email_result = await hunter_client.find_email(
                    first_name=person.first_name,
                    last_name=person.last_name,
                    domain=domain,
                )
                email = email_result.email if email_result else None

        if settings.USE_MOCK_DATA:
            _mock_update_contact_enrichment(contact_id, person, email)
        else:
            raise NotImplementedError("Live DB writes not yet wired")

        logger.info(
            "enrich_contact: id=%s pdl_id=%s email=%s priority=%s",
            contact_id, person.pdl_id, email, priority,
        )
        return {
            "contact_id": contact_id,
            "enriched": True,
            "email": email,
            "pdl_id": person.pdl_id,
        }

    try:
        return asyncio.run(_run())
    except Exception as exc:
        logger.error("enrich_contact failed id=%s: %s", contact_id, exc, exc_info=True)
        raise self.retry(exc=exc)


@celery_app.task(
    name="app.workers.enrich_contacts.find_key_contact",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    queue="default",
)
def find_key_contact(
    self,
    company_id: str,
    role_type: str,
) -> dict[str, Any]:
    """
    Search PDL for a key contact at a company and auto-create the contact record.

    Steps:
      1. Load company record (or mock)
      2. Call PDLClient.search_people() with title keywords derived from role_type
      3. Take the most senior result
      4. Optionally call Hunter.io for email (treats as high-priority)
      5. Create contact record in DB (or mock)

    The role_type maps to title_keywords for the PDL search:
      "strategy"   → ["VP Strategy", "Chief Strategy Officer", "Principal"]
      "operations" → ["VP Operations", "COO", "Director Operations"]
      "hr"         → ["Chief People Officer", "VP People", "Head of Talent"]
      default      → ["Chief of Staff", "VP"]

    Args:
        company_id: Company UUID.
        role_type:  Category of role to look for (e.g. "strategy").

    Returns:
        dict with keys: contact_id, full_name, job_title, email
    """
    settings = _get_settings()

    _ROLE_KEYWORDS: dict[str, list[str]] = {
        "strategy": ["VP Strategy", "Chief Strategy Officer", "Principal"],
        "operations": ["VP Operations", "COO", "Director Operations"],
        "hr": ["Chief People Officer", "VP People", "Head of Talent"],
        "finance": ["CFO", "VP Finance", "Head of Finance"],
        "technology": ["CTO", "VP Engineering", "Head of Technology"],
        "marketing": ["CMO", "VP Marketing", "Head of Growth"],
    }

    async def _run() -> dict[str, Any]:
        from app.integrations.pdl_client import PDLClient
        from app.integrations.hunter_client import HunterClient

        if settings.USE_MOCK_DATA:
            company = _load_mock_company(company_id)
        else:
            raise NotImplementedError("Live DB reads not yet wired")

        title_keywords = _ROLE_KEYWORDS.get(role_type.lower(), ["Chief of Staff", "VP"])

        pdl_client = PDLClient()
        results = await pdl_client.search_people(
            company_name=company["name"],
            title_keywords=title_keywords,
        )

        if not results:
            logger.warning(
                "find_key_contact: no PDL results for company=%s role=%s",
                company_id, role_type,
            )
            return {"contact_id": None, "full_name": None, "job_title": None, "email": None}

        # Take most senior result (already sorted by PDLClient)
        top = results[0]

        # Try to find email via Hunter.io
        email: str | None = None
        domain = company.get("domain", "")
        if domain and top.linkedin_url:
            # Parse first/last name from full_name for Hunter
            parts = top.full_name.strip().split()
            first = parts[0] if parts else ""
            last = parts[-1] if len(parts) > 1 else ""
            if first and last:
                hunter_client = HunterClient()
                email_result = await hunter_client.find_email(
                    first_name=first,
                    last_name=last,
                    domain=domain,
                )
                email = email_result.email if email_result else None

        # Create contact record
        if settings.USE_MOCK_DATA:
            contact_id = _mock_create_contact(company_id, top, email)
        else:
            raise NotImplementedError("Live DB writes not yet wired")

        logger.info(
            "find_key_contact: company=%s role=%s → %s (%s) email=%s",
            company_id, role_type, top.full_name, top.job_title, email,
        )
        return {
            "contact_id": contact_id,
            "full_name": top.full_name,
            "job_title": top.job_title,
            "email": email,
        }

    try:
        return asyncio.run(_run())
    except Exception as exc:
        logger.error(
            "find_key_contact failed company=%s role=%s: %s",
            company_id, role_type, exc, exc_info=True,
        )
        raise self.retry(exc=exc)


@celery_app.task(
    name="app.workers.enrich_contacts.batch_enrich",
    queue="low",
)
def batch_enrich(
    contact_ids: list[str],
    priority: str = "normal",
) -> dict[str, Any]:
    """
    Fan-out enrich_contact across a list of contact IDs.

    High-fit contacts should be passed with priority="high" so Hunter.io
    email finding is triggered for them.

    Args:
        contact_ids: List of contact UUIDs to enrich.
        priority:    "high" or "normal" — passed through to each enrich_contact task.

    Returns:
        dict with key: queued (int count)
    """
    if not contact_ids:
        return {"queued": 0}

    queue = "default" if priority == "high" else "low"
    for contact_id in contact_ids:
        enrich_contact.apply_async(
            args=[contact_id, priority],
            queue=queue,
        )

    logger.info(
        "batch_enrich: dispatched %d tasks (priority=%s)",
        len(contact_ids), priority,
    )
    return {"queued": len(contact_ids)}
