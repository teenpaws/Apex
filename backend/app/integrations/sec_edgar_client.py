"""
SEC EDGAR API client — free public data, no API key required.

Covers two signal types:
    - Form D filings  → FUNDING signals (private placement / funding rounds)
    - 8-K filings     → EXEC_HIRE or MA signals (exec changes, material contracts)

SEC policy: max 10 requests/second.  We enforce this with a 0.12 s sleep
between requests.  The User-Agent header is mandatory per SEC robots policy.

Reference:
    https://efts.sec.gov/LATEST/search-index (EDGAR full-text search API)
    https://www.sec.gov/developer (developer guidelines)
"""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timedelta, timezone

import httpx

from app.core.config import get_settings
from app.integrations.newsdata_client import SignalEvent
from app.models.enums import SignalType

__all__ = ["SECEdgarClient"]

logger = logging.getLogger(__name__)

# SEC requires a descriptive User-Agent; anonymous requests may be blocked.
SEC_USER_AGENT = "Apex-Platform contact@apex.ai"
SEC_SEARCH_BASE = "https://efts.sec.gov/LATEST/search-index"

# Seconds between consecutive SEC API calls to stay within 10 req/s limit.
SEC_RATE_LIMIT_SLEEP = 0.12

# Keywords in 8-K filing titles/descriptions that suggest exec changes vs M&A.
EXEC_HIRE_KEYWORDS = re.compile(
    r"\b(appoint|officer|director|ceo|cfo|coo|cto|president|hire|named|elected)\b",
    re.IGNORECASE,
)
MA_KEYWORDS = re.compile(
    r"\b(acqui|merger|acquis|definitive agreement|transaction|purchase agreement)\b",
    re.IGNORECASE,
)


def _build_params(
    company_name: str,
    form_type: str,
    days_back: int,
) -> dict[str, str]:
    """Build the EDGAR full-text search query params."""
    start_date = (
        datetime.now(tz=timezone.utc) - timedelta(days=days_back)
    ).strftime("%Y-%m-%d")
    return {
        "q": f'"{company_name}"',
        "forms": form_type,
        "dateRange": "custom",
        "startdt": start_date,
    }


def _classify_8k(title: str, description: str) -> SignalType:
    """
    Heuristically classify an 8-K filing as EXEC_HIRE or MA.

    Falls back to MA if neither pattern matches strongly (8-K = material event).
    """
    text = f"{title} {description}"
    if EXEC_HIRE_KEYWORDS.search(text):
        return SignalType.EXEC_HIRE
    return SignalType.MA


def _parse_edgar_date(date_str: str | None) -> datetime:
    """Parse EDGAR date string (YYYY-MM-DD or ISO-8601) → UTC datetime."""
    if not date_str:
        return datetime.now(tz=timezone.utc)
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            dt = datetime.strptime(date_str, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    return datetime.now(tz=timezone.utc)


class SECEdgarClient:
    """
    Async client for SEC EDGAR full-text search API.

    Usage::

        client = SECEdgarClient()
        funding_signals = await client.fetch_form_d("Stripe", days_back=30)
        exec_signals    = await client.fetch_8k_filings("Stripe", days_back=30)

    No API key is required.  User-Agent header is mandatory per SEC policy.
    """

    def __init__(self) -> None:
        self._settings = get_settings()
        self._http_headers = {"User-Agent": SEC_USER_AGENT}

    # ── Internal helpers ───────────────────────────────────────────────────────

    async def _search(
        self,
        params: dict[str, str],
        context: str,
    ) -> list[dict]:
        """
        Execute a single EDGAR search query.

        Returns the raw ``hits`` list or [] on any error.
        Enforces the SEC rate-limit sleep after every call.
        """
        try:
            async with httpx.AsyncClient(
                headers=self._http_headers, timeout=20.0
            ) as client:
                response = await client.get(SEC_SEARCH_BASE, params=params)

            if response.status_code == 429:
                logger.warning("SEC EDGAR rate limit (429) for %s — returning []", context)
                await asyncio.sleep(SEC_RATE_LIMIT_SLEEP * 5)
                return []

            response.raise_for_status()
            payload = response.json()

        except httpx.HTTPStatusError as exc:
            logger.error(
                "SEC EDGAR HTTP error %d for %s: %s",
                exc.response.status_code,
                context,
                exc,
            )
            return []
        except Exception as exc:  # noqa: BLE001
            logger.error("SEC EDGAR unexpected error for %s: %s", context, exc)
            return []
        finally:
            # Enforce rate limit regardless of success/failure.
            await asyncio.sleep(SEC_RATE_LIMIT_SLEEP)

        hits: list[dict] = (
            (payload.get("hits") or {}).get("hits", []) or []
        )
        return hits

    # ── Public methods ─────────────────────────────────────────────────────────

    async def fetch_form_d(
        self,
        company_name: str,
        days_back: int = 30,
    ) -> list[SignalEvent]:
        """
        Fetch Form D filings (private funding rounds) for *company_name*.

        Returns SignalEvent list with ``source="sec_edgar"`` and inferred
        signal_type FUNDING.
        """
        if self._settings.USE_MOCK_DATA:
            return _mock_form_d_events(company_name)

        params = _build_params(company_name, "D", days_back)
        hits = await self._search(params, f"Form D / {company_name}")

        events: list[SignalEvent] = []
        for hit in hits:
            src: dict = hit.get("_source", {}) or {}
            filing_date: str = src.get("file_date", "") or ""
            entity_name: str = src.get("entity_name", company_name) or company_name
            accession: str = src.get("accession_no", hit.get("_id", "")) or ""
            period: str = src.get("period_of_report", "") or filing_date

            description = (
                f"Form D filing by {entity_name}. "
                f"Period: {period}. "
                f"Accession: {accession}."
            )

            events.append(
                SignalEvent(
                    source="sec_edgar",
                    external_id=f"sec_d:{accession}",
                    title=f"{entity_name} — Form D (Private Offering)",
                    description=description,
                    raw_data=src,
                    signal_date=_parse_edgar_date(filing_date),
                    company_name=company_name,
                )
            )

        logger.info(
            "SEC EDGAR Form D: %d filings for company=%r",
            len(events),
            company_name,
        )
        return events

    async def fetch_8k_filings(
        self,
        company_name: str,
        days_back: int = 30,
    ) -> list[SignalEvent]:
        """
        Fetch 8-K filings (material events) for *company_name*.

        Each filing is classified as EXEC_HIRE or MA based on keyword matching
        against the filing title/description.
        """
        if self._settings.USE_MOCK_DATA:
            return _mock_8k_events(company_name)

        params = _build_params(company_name, "8-K", days_back)
        hits = await self._search(params, f"8-K / {company_name}")

        events: list[SignalEvent] = []
        for hit in hits:
            src: dict = hit.get("_source", {}) or {}
            filing_date: str = src.get("file_date", "") or ""
            entity_name: str = src.get("entity_name", company_name) or company_name
            accession: str = src.get("accession_no", hit.get("_id", "")) or ""
            display_names: list[str] = src.get("display_names", []) or []
            form_type_desc = ", ".join(display_names) if display_names else "8-K"

            title = f"{entity_name} — {form_type_desc}"
            description = (
                f"SEC 8-K filing by {entity_name}. "
                f"Filing date: {filing_date}. "
                f"Accession: {accession}."
            )
            signal_type = _classify_8k(title, description)

            events.append(
                SignalEvent(
                    source="sec_edgar",
                    external_id=f"sec_8k:{accession}",
                    title=title,
                    description=description,
                    raw_data={**src, "_signal_type": signal_type.value},
                    signal_date=_parse_edgar_date(filing_date),
                    company_name=company_name,
                )
            )

        logger.info(
            "SEC EDGAR 8-K: %d filings for company=%r",
            len(events),
            company_name,
        )
        return events


# ── Mock helpers ──────────────────────────────────────────────────────────────

def _mock_form_d_events(company_name: str) -> list[SignalEvent]:
    """Return deterministic Form D fixture when USE_MOCK_DATA=true."""
    slug = company_name.lower().replace(" ", "-")
    return [
        SignalEvent(
            source="sec_edgar",
            external_id=f"sec_d:0001234567-26-000001-{slug}",
            title=f"{company_name} — Form D (Private Offering)",
            description=(
                f"Form D filing by {company_name}. Period: 2026-03-15. "
                "Accession: 0001234567-26-000001. "
                "Total offering amount: $150,000,000."
            ),
            raw_data={
                "entity_name": company_name,
                "file_date": "2026-03-20",
                "period_of_report": "2026-03-15",
                "accession_no": f"0001234567-26-000001",
                "_signal_type": "FUNDING",
            },
            signal_date=datetime(2026, 3, 20, tzinfo=timezone.utc),
            company_name=company_name,
        )
    ]


def _mock_8k_events(company_name: str) -> list[SignalEvent]:
    """Return deterministic 8-K fixture when USE_MOCK_DATA=true."""
    slug = company_name.lower().replace(" ", "-")
    return [
        SignalEvent(
            source="sec_edgar",
            external_id=f"sec_8k:0001234567-26-000002-{slug}",
            title=f"{company_name} — Appointment of New Chief Executive Officer",
            description=(
                f"SEC 8-K filing by {company_name}. "
                "Filing date: 2026-04-05. "
                "Accession: 0001234567-26-000002."
            ),
            raw_data={
                "entity_name": company_name,
                "file_date": "2026-04-05",
                "accession_no": "0001234567-26-000002",
                "_signal_type": "EXEC_HIRE",
            },
            signal_date=datetime(2026, 4, 5, tzinfo=timezone.utc),
            company_name=company_name,
        )
    ]
