"""
Adzuna API client — job posting search for opportunity validation.

Free API: https://developer.adzuna.com
Sign up for app_id/app_key (free, no credit card).
Covers UK/US/AU/CA/DE/FR/NL/SG.
"""
from __future__ import annotations
import logging
from dataclasses import dataclass
import httpx

logger = logging.getLogger(__name__)
_ADZUNA_BASE = "https://api.adzuna.com/v1/api/jobs"
_REQUEST_TIMEOUT_SECONDS = 10


@dataclass
class AdzunaPosting:
    title: str
    company: str
    url: str
    posted_date: str  # ISO date "2026-04-20"


class AdzunaClient:
    """Async Adzuna job search client."""

    def __init__(self, app_id: str, app_key: str, country: str = "gb") -> None:
        self._app_id = app_id
        self._app_key = app_key
        self._country = country

    async def search_jobs(self, company_name: str, role_keywords: str, max_results: int = 5) -> list[AdzunaPosting]:
        """Search Adzuna for roles matching the predicted opportunity. Returns [] on any error."""
        params = {
            "app_id": self._app_id,
            "app_key": self._app_key,
            "what": role_keywords,
            "company": company_name,
            "results_per_page": max_results,
            "content-type": "application/json",
        }
        try:
            data = await self._get(url=f"{_ADZUNA_BASE}/{self._country}/search/1", params=params)
        except httpx.HTTPStatusError as exc:
            logger.warning("Adzuna HTTP error for company=%s role=%s: %s", company_name, role_keywords, exc)
            return []
        except Exception as exc:  # noqa: BLE001
            logger.warning("Adzuna API error: %s", exc)
            return []

        return [
            AdzunaPosting(
                title=r.get("title", ""),
                company=r.get("company", {}).get("display_name", company_name),
                url=r.get("redirect_url", ""),
                posted_date=r.get("created", "")[:10],
            )
            for r in data.get("results", [])
        ]

    async def _get(self, url: str, params: dict) -> dict:
        """Extracted for easy mocking in tests."""
        async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT_SECONDS) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()
