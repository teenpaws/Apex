"""
OpportunityValidatorService — validates predicted opportunities against Adzuna postings.

If Adzuna returns matching open roles → opportunity becomes VALIDATED.
If no match → stays PREDICTED.
"""
from __future__ import annotations
import logging
from dataclasses import dataclass, field
from app.integrations.adzuna_client import AdzunaClient

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    is_validated: bool
    real_postings: list[dict] = field(default_factory=list)


class OpportunityValidatorService:
    def __init__(self, adzuna_client: AdzunaClient) -> None:
        self._adzuna = adzuna_client

    async def validate(self, company_name: str, predicted_role: str, max_results: int = 5) -> ValidationResult:
        """Search Adzuna for roles matching the predicted opportunity."""
        role_keywords = " ".join(predicted_role.split()[:4])
        try:
            postings = await self._adzuna.search_jobs(
                company_name=company_name,
                role_keywords=role_keywords,
                max_results=max_results,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Adzuna validation failed for company=%s role=%s: %s", company_name, predicted_role, exc)
            return ValidationResult(is_validated=False)

        if not postings:
            return ValidationResult(is_validated=False, real_postings=[])

        return ValidationResult(
            is_validated=True,
            real_postings=[{"title": p.title, "url": p.url, "company": p.company, "posted_date": p.posted_date} for p in postings],
        )
