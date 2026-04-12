"""
CompanyService — business logic for company data and enrichment.

In mock mode (use_mock=True): serves data from mock_responses/companies.json,
with signals attached from mock_responses/signals.json.
In live mode (use_mock=False): queries Supabase via SQLAlchemy (stubbed for Phase 2).
"""

from __future__ import annotations

from app.core.errors import ApexHTTPException
from app.services._mock_loader import load_mock


class CompanyService:
    """Service layer for company read operations."""

    def __init__(self, user_id: str, use_mock: bool = False) -> None:
        self.user_id = user_id
        self.use_mock = use_mock

    async def get_company(self, company_id: str) -> dict:
        """Return a company by ID with its associated signals attached."""
        if self.use_mock:
            return self._get_company_mock(company_id)
        raise NotImplementedError("Live DB not yet wired")

    def _get_company_mock(self, company_id: str) -> dict:
        companies_data = load_mock("companies.json")
        company: dict | None = None
        for c in companies_data["companies"]:
            if c["id"] == company_id:
                company = dict(c)
                break

        if company is None:
            raise ApexHTTPException(404, "Company not found", code="NOT_FOUND")

        # Attach signals filtered by company_id
        signals_data = load_mock("signals.json")
        company_signals = [
            s for s in signals_data["signals"]
            if s.get("company_id") == company_id
        ]
        company["signals"] = company_signals

        return company
