"""
People Data Labs (PDL) API client — contact and company enrichment.

Replaces Proxycurl (shut down July 2025 after LinkedIn lawsuit).
PDL sources data from public/open data only — legally clean.

Free tier: 1,000 credits/month
  - enrich_person:  1 credit per call
  - enrich_company: 1 credit per call
  - search_people:  1 credit per matched result (cap at 10 results = 10 credits)

Caching strategy:
  - All enriched profiles cached in Redis with 90-day TTL
  - Cache key: pdl:person:{sha256(name+company)} or pdl:company:{sha256(name+domain)}
  - Cache hit: 0 credits used — critical for staying within free tier

Error handling:
  - 402 Payment Required (quota exceeded) → log warning, return cached data or None
  - 404 Not Found → return None (person/company not in PDL database)
  - Any other error → log, return None (never crash the worker)

API reference: https://docs.peopledatalabs.com/docs
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.core.config import get_settings

__all__ = ["PDLClient", "PersonProfile", "CompanyProfile", "ContactSearchResult"]

logger = logging.getLogger(__name__)

PDL_BASE_URL = "https://api.peopledatalabs.com/v5"
CACHE_TTL_SECONDS = 90 * 86_400  # 90 days
CACHE_PERMANENT_TTL = 365 * 86_400  # 1 year (for company data)


# ── Data classes ────────────────────────────────────────────────────────────────

@dataclass
class PersonProfile:
    """Normalised contact profile returned by PDL enrich or search."""

    pdl_id: str
    full_name: str
    first_name: str
    last_name: str
    job_title: str
    company_name: str
    linkedin_url: str | None
    email: str | None          # populated by Hunter.io separately
    location: str | None
    seniority: str | None      # e.g. "vp", "director", "manager"
    raw_data: dict[str, Any] = field(default_factory=dict)


@dataclass
class CompanyProfile:
    """Normalised company profile returned by PDL enrich."""

    pdl_id: str
    name: str
    domain: str | None
    industry: str | None
    headcount: int | None      # employee count
    founded_year: int | None
    location: str | None
    linkedin_url: str | None
    raw_data: dict[str, Any] = field(default_factory=dict)


@dataclass
class ContactSearchResult:
    """A single result from PDL search_people, ranked by seniority."""

    full_name: str
    job_title: str
    seniority: str | None
    linkedin_url: str | None
    pdl_id: str
    raw_data: dict[str, Any] = field(default_factory=dict)


# ── Cache helpers ────────────────────────────────────────────────────────────────

def _sha256(value: str) -> str:
    return hashlib.sha256(value.lower().strip().encode()).hexdigest()


def _redis_client() -> Any | None:
    try:
        import redis
        settings = get_settings()
        client = redis.from_url(settings.REDIS_URL, socket_connect_timeout=1)
        client.ping()
        return client
    except Exception as exc:  # noqa: BLE001
        logger.warning("Redis unavailable — PDL results won't be cached: %s", exc)
        return None


def _cache_get(redis_client: Any | None, key: str) -> dict | None:
    if redis_client is None:
        return None
    try:
        raw = redis_client.get(key)
        if raw:
            return json.loads(raw)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Redis GET failed key=%s: %s", key, exc)
    return None


def _cache_set(
    redis_client: Any | None,
    key: str,
    data: dict,
    ttl: int = CACHE_TTL_SECONDS,
) -> None:
    if redis_client is None:
        return
    try:
        redis_client.setex(key, ttl, json.dumps(data))
    except Exception as exc:  # noqa: BLE001
        logger.warning("Redis SETEX failed key=%s: %s", key, exc)


# ── Normalisation helpers ────────────────────────────────────────────────────────

def _normalise_person(raw: dict) -> PersonProfile:
    """Map a PDL /person/enrich response to a PersonProfile."""
    experience = raw.get("experience") or []
    current_job = next(
        (e for e in experience if e.get("is_primary")),
        experience[0] if experience else {},
    )
    company_name = (
        (current_job.get("company") or {}).get("name", "")
        or raw.get("job_company_name", "")
        or ""
    )
    return PersonProfile(
        pdl_id=raw.get("id", ""),
        full_name=raw.get("full_name", ""),
        first_name=raw.get("first_name", ""),
        last_name=raw.get("last_name", ""),
        job_title=raw.get("job_title", "") or (current_job.get("title", {}) or {}).get("name", ""),
        company_name=company_name,
        linkedin_url=raw.get("linkedin_url"),
        email=None,  # populated by Hunter.io separately
        location=raw.get("location_name"),
        seniority=raw.get("job_title_levels", [None])[0] if raw.get("job_title_levels") else None,
        raw_data=raw,
    )


def _normalise_company(raw: dict) -> CompanyProfile:
    """Map a PDL /company/enrich response to a CompanyProfile."""
    return CompanyProfile(
        pdl_id=raw.get("id", ""),
        name=raw.get("display_name") or raw.get("name", ""),
        domain=raw.get("website"),
        industry=raw.get("industry"),
        headcount=raw.get("employee_count"),
        founded_year=raw.get("founded"),
        location=raw.get("location", {}).get("name") if isinstance(raw.get("location"), dict) else raw.get("location"),
        linkedin_url=raw.get("linkedin_url"),
        raw_data=raw,
    )


_SENIORITY_RANK = {
    "c_suite": 0, "vp": 1, "director": 2, "manager": 3,
    "senior": 4, "entry": 5, "training": 6,
}


def _seniority_sort_key(result: ContactSearchResult) -> int:
    """Lower = more senior. Unknown seniority ranks last."""
    return _SENIORITY_RANK.get((result.seniority or "").lower(), 99)


# ── Client ────────────────────────────────────────────────────────────────────────

class PDLClient:
    """
    Async client for the People Data Labs REST API.

    Usage::

        client = PDLClient()
        person = await client.enrich_person("Jane Smith", "McKinsey")
        company = await client.enrich_company("McKinsey", domain="mckinsey.com")
        contacts = await client.search_people("McKinsey", ["VP Strategy", "Principal"])
    """

    def __init__(self) -> None:
        self._settings = get_settings()

    # ── Public methods ────────────────────────────────────────────────────────

    async def enrich_person(
        self,
        name: str,
        company: str,
        linkedin_url: str | None = None,
    ) -> PersonProfile | None:
        """
        Enrich a person by name + company (optionally LinkedIn URL).

        Returns None if not found in PDL or on any error.
        Cached for 90 days to preserve free-tier credits.

        Args:
            name:         Full name of the person.
            company:      Current company name.
            linkedin_url: Optional LinkedIn profile URL (improves match rate).

        Returns:
            PersonProfile or None.
        """
        if self._settings.USE_MOCK_DATA:
            return _mock_enrich_person(name, company)

        cache_key = f"pdl:person:{_sha256(name + company)}"
        redis = _redis_client()

        cached = _cache_get(redis, cache_key)
        if cached is not None:
            logger.debug("PDL enrich_person CACHE HIT: %s @ %s", name, company)
            return _normalise_person(cached)

        params: dict[str, Any] = {
            "name": name,
            "company": company,
            "pretty": "true",
        }
        if linkedin_url:
            params["profile"] = linkedin_url

        raw = await self._get("/person/enrich", params=params)
        if raw is None:
            return None

        _cache_set(redis, cache_key, raw)
        logger.info("PDL enrich_person: %s @ %s → id=%s", name, company, raw.get("id"))
        return _normalise_person(raw)

    async def enrich_company(
        self,
        name: str,
        domain: str | None = None,
    ) -> CompanyProfile | None:
        """
        Enrich a company by name (optionally domain).

        Returns None if not found or on any error.
        Cached for 90 days.

        Args:
            name:   Company name.
            domain: Optional website domain (improves match rate, e.g. "mckinsey.com").

        Returns:
            CompanyProfile or None.
        """
        if self._settings.USE_MOCK_DATA:
            return _mock_enrich_company(name, domain)

        cache_key = f"pdl:company:{_sha256(name + (domain or ''))}"
        redis = _redis_client()

        cached = _cache_get(redis, cache_key)
        if cached is not None:
            logger.debug("PDL enrich_company CACHE HIT: %s", name)
            return _normalise_company(cached)

        params: dict[str, Any] = {"name": name, "pretty": "true"}
        if domain:
            params["website"] = domain

        raw = await self._get("/company/enrich", params=params)
        if raw is None:
            return None

        _cache_set(redis, cache_key, raw, ttl=CACHE_PERMANENT_TTL)
        logger.info("PDL enrich_company: %s → id=%s headcount=%s", name, raw.get("id"), raw.get("employee_count"))
        return _normalise_company(raw)

    async def search_people(
        self,
        company_name: str,
        title_keywords: list[str],
        limit: int = 10,
    ) -> list[ContactSearchResult]:
        """
        Search for people at a company matching title keywords.

        Results are ranked by seniority (VP > Director > Manager > ...).
        Returns up to `limit` results (max 10 to stay within free tier).
        Cached 90 days per (company_name, title_keywords) combination.

        Args:
            company_name:    Company to search within.
            title_keywords:  List of title fragments (e.g. ["VP Strategy", "Principal"]).
            limit:           Max results to return (capped at 10).

        Returns:
            List of ContactSearchResult sorted by seniority (most senior first).
        """
        if self._settings.USE_MOCK_DATA:
            return _mock_search_people(company_name, title_keywords)

        limit = min(limit, 10)
        cache_key = f"pdl:search:{_sha256(company_name + '|'.join(sorted(title_keywords)))}"
        redis = _redis_client()

        cached = _cache_get(redis, cache_key)
        if cached is not None:
            logger.debug("PDL search_people CACHE HIT: %s %s", company_name, title_keywords)
            return [ContactSearchResult(**r) for r in cached]

        # PDL Elasticsearch-style query
        title_clauses = [{"term": {"job_title": kw.lower()}} for kw in title_keywords]
        query = {
            "query": {
                "bool": {
                    "must": [
                        {"term": {"job_company_name": company_name.lower()}},
                    ],
                    "should": title_clauses,
                    "minimum_should_match": 1,
                }
            }
        }

        payload = {
            "query": json.dumps(query),
            "size": limit,
            "pretty": True,
        }

        raw = await self._post("/person/search", json_body=payload)
        if raw is None:
            return []

        matches: list[dict] = raw.get("data", []) or []
        results: list[ContactSearchResult] = []
        for match in matches:
            results.append(ContactSearchResult(
                full_name=match.get("full_name", ""),
                job_title=match.get("job_title", ""),
                seniority=(match.get("job_title_levels") or [None])[0],
                linkedin_url=match.get("linkedin_url"),
                pdl_id=match.get("id", ""),
                raw_data=match,
            ))

        results.sort(key=_seniority_sort_key)

        # Cache the result list as serialisable dicts
        _cache_set(redis, cache_key, [
            {
                "full_name": r.full_name,
                "job_title": r.job_title,
                "seniority": r.seniority,
                "linkedin_url": r.linkedin_url,
                "pdl_id": r.pdl_id,
                "raw_data": r.raw_data,
            }
            for r in results
        ])

        logger.info(
            "PDL search_people: company=%s keywords=%s → %d results",
            company_name, title_keywords, len(results),
        )
        return results

    # ── Private HTTP helpers ──────────────────────────────────────────────────

    async def _get(self, path: str, params: dict) -> dict | None:
        """
        Make a GET request to PDL API.

        Returns None on 402 (quota), 404 (not found), or any error.
        """
        headers = {"X-Api-Key": self._settings.PDL_API_KEY}
        url = PDL_BASE_URL + path
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(url, params=params, headers=headers)

            if resp.status_code == 402:
                logger.warning("PDL quota exceeded (402) for %s — returning None", path)
                return None
            if resp.status_code == 404:
                logger.debug("PDL not found (404) for %s params=%s", path, params)
                return None

            resp.raise_for_status()
            return resp.json()

        except httpx.HTTPStatusError as exc:
            logger.error("PDL HTTP error %d for %s: %s", exc.response.status_code, path, exc)
            return None
        except Exception as exc:  # noqa: BLE001
            logger.error("PDL unexpected error for %s: %s", path, exc)
            return None

    async def _post(self, path: str, json_body: dict) -> dict | None:
        """Make a POST request to PDL API. Returns None on any error."""
        headers = {
            "X-Api-Key": self._settings.PDL_API_KEY,
            "Content-Type": "application/json",
        }
        url = PDL_BASE_URL + path
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(url, json=json_body, headers=headers)

            if resp.status_code == 402:
                logger.warning("PDL quota exceeded (402) for %s — returning None", path)
                return None

            resp.raise_for_status()
            return resp.json()

        except httpx.HTTPStatusError as exc:
            logger.error("PDL HTTP error %d for %s: %s", exc.response.status_code, path, exc)
            return None
        except Exception as exc:  # noqa: BLE001
            logger.error("PDL unexpected error for %s: %s", path, exc)
            return None


# ── Mock helpers ────────────────────────────────────────────────────────────────

def _mock_enrich_person(name: str, company: str) -> PersonProfile:
    parts = name.strip().split()
    first = parts[0] if parts else "Jane"
    last = parts[-1] if len(parts) > 1 else "Smith"
    return PersonProfile(
        pdl_id=f"mock-pdl-person-{_sha256(name + company)[:8]}",
        full_name=name,
        first_name=first,
        last_name=last,
        job_title="Chief of Staff",
        company_name=company,
        linkedin_url=f"https://linkedin.com/in/{first.lower()}-{last.lower()}",
        email=None,
        location="New York, USA",
        seniority="vp",
        raw_data={"mock": True},
    )


def _mock_enrich_company(name: str, domain: str | None) -> CompanyProfile:
    return CompanyProfile(
        pdl_id=f"mock-pdl-co-{_sha256(name)[:8]}",
        name=name,
        domain=domain or f"{name.lower().replace(' ', '')}.com",
        industry="Consulting",
        headcount=30000,
        founded_year=1926,
        location="New York, USA",
        linkedin_url=f"https://linkedin.com/company/{name.lower().replace(' ', '-')}",
        raw_data={"mock": True},
    )


def _mock_search_people(
    company_name: str, title_keywords: list[str]
) -> list[ContactSearchResult]:
    return [
        ContactSearchResult(
            full_name="Jane Smith",
            job_title=title_keywords[0] if title_keywords else "Chief of Staff",
            seniority="vp",
            linkedin_url="https://linkedin.com/in/janesmith",
            pdl_id=f"mock-pdl-{_sha256(company_name)[:8]}-001",
            raw_data={"mock": True},
        ),
        ContactSearchResult(
            full_name="Alex Johnson",
            job_title=title_keywords[-1] if title_keywords else "Director",
            seniority="director",
            linkedin_url="https://linkedin.com/in/alexjohnson",
            pdl_id=f"mock-pdl-{_sha256(company_name)[:8]}-002",
            raw_data={"mock": True},
        ),
    ]
