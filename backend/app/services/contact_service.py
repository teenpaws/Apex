"""
ContactService — business logic for contacts (search, enrich, retrieve).

In mock mode (use_mock=True): serves data from mock_responses/contacts.json.
In live mode (use_mock=False): queries Supabase via SQLAlchemy (stubbed).
"""

from __future__ import annotations

from uuid import uuid4

from app.core.errors import ApexHTTPException
from app.services._mock_loader import load_mock


class ContactService:
    """Service layer for contact read, search, and enrichment operations."""

    def __init__(self, user_id: str, use_mock: bool = False) -> None:
        self.user_id = user_id
        self.use_mock = use_mock

    # ── List contacts ─────────────────────────────────────────────────────────

    async def list_contacts(
        self,
        company_id: str | None = None,
    ) -> dict:
        """
        Return contacts saved by the current user.

        Args:
            company_id: Optional filter — only contacts at this company.

        Returns:
            dict with key "contacts" (list of contact dicts).
        """
        if self.use_mock:
            return self._list_contacts_mock(company_id=company_id)
        raise NotImplementedError("Live DB not yet wired")

    def _list_contacts_mock(self, company_id: str | None) -> dict:
        data = load_mock("contacts.json")
        contacts: list[dict] = data["contacts"]

        # Scope to current user
        contacts = [
            c for c in contacts
            if c.get("user_id") == self.user_id or self.user_id == "mock-user-id"
        ]

        if company_id is not None:
            contacts = [c for c in contacts if c.get("company_id") == company_id]

        return {"contacts": contacts, "total": len(contacts)}

    # ── Get contact by ID ─────────────────────────────────────────────────────

    async def get_contact(self, contact_id: str) -> dict:
        """
        Return a single contact by ID.

        Raises:
            ApexHTTPException(404) if not found.
        """
        if self.use_mock:
            return self._get_contact_mock(contact_id)
        raise NotImplementedError("Live DB not yet wired")

    def _get_contact_mock(self, contact_id: str) -> dict:
        data = load_mock("contacts.json")
        for contact in data["contacts"]:
            if contact.get("id") == contact_id:
                return contact
        raise ApexHTTPException(status_code=404, error=f"Contact {contact_id} not found", code="NOT_FOUND")

    # ── Search contacts via PDL ───────────────────────────────────────────────

    async def search_contacts(
        self,
        company_name: str,
        title_keywords: list[str],
        limit: int = 10,
    ) -> dict:
        """
        Search for contacts at a company using PDL.

        Results are returned ranked by seniority (most senior first).
        In mock mode, returns deterministic fixture data.

        Args:
            company_name:   Target company name for the search.
            title_keywords: Job title fragments to match (e.g. ["VP Strategy"]).
            limit:          Max results (capped at 10).

        Returns:
            dict with key "contacts" (list of contact dicts) and "total".
        """
        if self.use_mock:
            return await self._search_contacts_mock(company_name, title_keywords, limit)
        raise NotImplementedError("Live PDL search not yet wired")

    async def _search_contacts_mock(
        self,
        company_name: str,
        title_keywords: list[str],
        limit: int,
    ) -> dict:
        from app.integrations.pdl_client import PDLClient

        client = PDLClient()
        results = await client.search_people(
            company_name=company_name,
            title_keywords=title_keywords,
            limit=limit,
        )
        contacts = [
            {
                "id": f"search-result-{r.pdl_id}",
                "name": r.full_name,
                "title": r.job_title,
                "seniority": r.seniority,
                "linkedin_url": r.linkedin_url,
                "email": None,
                "company_name": company_name,
                "pdl_id": r.pdl_id,
            }
            for r in results
        ]
        return {"contacts": contacts[:limit], "total": len(contacts)}

    # ── Trigger enrichment ────────────────────────────────────────────────────

    async def trigger_enrich(
        self,
        contact_id: str,
        priority: str = "normal",
    ) -> dict:
        """
        Queue an enrichment task for a contact.

        Returns a run_id to poll via GET /agents/run-status/{run_id}.

        Args:
            contact_id: Contact UUID to enrich.
            priority:   "high" triggers Hunter.io email lookup.
        """
        from app.workers.enrich_contacts import enrich_contact

        run_id = str(uuid4())

        if self.use_mock:
            # In mock mode, run inline and return immediately
            result = enrich_contact.apply(args=[contact_id, priority]).get()
            return {
                "run_id": run_id,
                "status": "SUCCESS",
                "result": result,
            }

        enrich_contact.apply_async(
            args=[contact_id, priority],
            task_id=run_id,
        )
        return {
            "run_id": run_id,
            "status": "queued",
            "message": "Enrichment started",
        }
