"""
Hunter.io API client — email discovery by company domain + person name.

Free tier: 25 searches/month — use sparingly, only for high-priority contacts.
  - find_email:        1 request per call
  - find_domain_emails: 1 request per call

Caching strategy:
  - Cache permanently (1 year TTL) — emails rarely change
  - Cache key: hunter:email:{sha256(first+last+domain)} or hunter:domain:{sha256(domain)}
  - Cache hit: 0 requests used

Error handling:
  - 401 Unauthorized  → log error, return None (bad API key)
  - 429 Too Many Requests → log warning, return None (monthly limit hit)
  - 404 / not found   → return None (no email found for this person)
  - Any other error   → log, return None

API reference: https://hunter.io/api-documentation
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import get_settings

__all__ = ["HunterClient", "EmailResult", "DomainEmailResult"]

logger = logging.getLogger(__name__)

HUNTER_BASE_URL = "https://api.hunter.io/v2"
CACHE_TTL_SECONDS = 365 * 86_400  # 1 year — emails are stable


# ── Data classes ────────────────────────────────────────────────────────────────

@dataclass
class EmailResult:
    """Result of a single email finder lookup."""

    email: str | None
    score: int             # Hunter confidence score 0–100
    first_name: str
    last_name: str
    domain: str
    verified: bool
    sources: list[str]


@dataclass
class DomainEmailResult:
    """One entry from a domain-wide email lookup."""

    email: str
    first_name: str
    last_name: str
    job_title: str
    confidence: int


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
        logger.warning("Redis unavailable — Hunter results won't be cached: %s", exc)
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


# ── Client ────────────────────────────────────────────────────────────────────────

class HunterClient:
    """
    Async client for the Hunter.io REST API.

    Usage::

        client = HunterClient()
        result = await client.find_email("Jane", "Smith", "mckinsey.com")
        emails = await client.find_domain_emails("mckinsey.com", limit=5)
    """

    def __init__(self) -> None:
        self._settings = get_settings()

    # ── Public methods ────────────────────────────────────────────────────────

    async def find_email(
        self,
        first_name: str,
        last_name: str,
        domain: str,
    ) -> EmailResult | None:
        """
        Find a verified email address for a person at a company domain.

        Uses permanent caching — emails don't change often.
        Returns None if not found or on any error.

        Args:
            first_name: Person's first name.
            last_name:  Person's last name.
            domain:     Company website domain (e.g. "mckinsey.com").

        Returns:
            EmailResult or None.
        """
        if self._settings.USE_MOCK_DATA:
            return _mock_find_email(first_name, last_name, domain)

        cache_key = f"hunter:email:{_sha256(first_name + last_name + domain)}"
        redis = _redis_client()

        cached = _cache_get(redis, cache_key)
        if cached is not None:
            logger.debug("Hunter find_email CACHE HIT: %s %s @ %s", first_name, last_name, domain)
            return EmailResult(**cached) if cached.get("email") else None

        params = {
            "first_name": first_name,
            "last_name": last_name,
            "domain": domain,
            "api_key": self._settings.HUNTER_API_KEY,
        }

        raw = await self._get("/email-finder", params=params)
        if raw is None:
            return None

        data = raw.get("data", {}) or {}
        result = EmailResult(
            email=data.get("email"),
            score=data.get("score", 0),
            first_name=data.get("first_name", first_name),
            last_name=data.get("last_name", last_name),
            domain=domain,
            verified=(data.get("verification", {}) or {}).get("status") == "valid",
            sources=[s.get("uri", "") for s in (data.get("sources") or [])],
        )

        # Cache even None results (as {"email": null}) to avoid wasting monthly quota
        _cache_set(redis, cache_key, {
            "email": result.email,
            "score": result.score,
            "first_name": result.first_name,
            "last_name": result.last_name,
            "domain": result.domain,
            "verified": result.verified,
            "sources": result.sources,
        })

        if result.email:
            logger.info(
                "Hunter find_email: %s %s @ %s → %s (score=%d)",
                first_name, last_name, domain, result.email, result.score,
            )
        else:
            logger.debug("Hunter find_email: no email found for %s %s @ %s", first_name, last_name, domain)

        return result if result.email else None

    async def find_domain_emails(
        self,
        domain: str,
        limit: int = 5,
    ) -> list[DomainEmailResult]:
        """
        Retrieve known email addresses at a company domain.

        Returns up to `limit` results sorted by confidence.
        Useful for finding any reachable contact at a company.
        Cached permanently.

        Args:
            domain: Company website domain (e.g. "mckinsey.com").
            limit:  Max results to return (capped at 10 to preserve quota).

        Returns:
            List of DomainEmailResult sorted by confidence descending.
        """
        if self._settings.USE_MOCK_DATA:
            return _mock_find_domain_emails(domain, limit)

        limit = min(limit, 10)
        cache_key = f"hunter:domain:{_sha256(domain)}:{limit}"
        redis = _redis_client()

        cached = _cache_get(redis, cache_key)
        if cached is not None:
            logger.debug("Hunter find_domain_emails CACHE HIT: %s", domain)
            return [DomainEmailResult(**r) for r in cached]

        params = {
            "domain": domain,
            "limit": limit,
            "api_key": self._settings.HUNTER_API_KEY,
        }

        raw = await self._get("/domain-search", params=params)
        if raw is None:
            return []

        emails_raw: list[dict] = (raw.get("data", {}) or {}).get("emails", []) or []
        results: list[DomainEmailResult] = []
        for entry in emails_raw:
            results.append(DomainEmailResult(
                email=entry.get("value", ""),
                first_name=entry.get("first_name", ""),
                last_name=entry.get("last_name", ""),
                job_title=entry.get("position", ""),
                confidence=entry.get("confidence", 0),
            ))

        results.sort(key=lambda r: r.confidence, reverse=True)

        _cache_set(redis, cache_key, [
            {
                "email": r.email,
                "first_name": r.first_name,
                "last_name": r.last_name,
                "job_title": r.job_title,
                "confidence": r.confidence,
            }
            for r in results
        ])

        logger.info("Hunter domain-search: %s → %d emails", domain, len(results))
        return results

    # ── Private HTTP helper ───────────────────────────────────────────────────

    async def _get(self, path: str, params: dict) -> dict | None:
        """GET request to Hunter API. Returns None on quota/error."""
        url = HUNTER_BASE_URL + path
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(url, params=params)

            if resp.status_code == 401:
                logger.error("Hunter.io 401 Unauthorized — check HUNTER_API_KEY")
                return None
            if resp.status_code == 429:
                logger.warning("Hunter.io monthly quota exceeded (429)")
                return None
            if resp.status_code == 404:
                return None

            resp.raise_for_status()
            return resp.json()

        except httpx.HTTPStatusError as exc:
            logger.error("Hunter.io HTTP error %d for %s: %s", exc.response.status_code, path, exc)
            return None
        except Exception as exc:  # noqa: BLE001
            logger.error("Hunter.io unexpected error for %s: %s", path, exc)
            return None


# ── Mock helpers ────────────────────────────────────────────────────────────────

def _mock_find_email(first_name: str, last_name: str, domain: str) -> EmailResult:
    mock_email = f"{first_name.lower()}.{last_name.lower()}@{domain}"
    return EmailResult(
        email=mock_email,
        score=92,
        first_name=first_name,
        last_name=last_name,
        domain=domain,
        verified=True,
        sources=[f"https://{domain}/team"],
    )


def _mock_find_domain_emails(domain: str, limit: int) -> list[DomainEmailResult]:
    return [
        DomainEmailResult(
            email=f"jane.smith@{domain}",
            first_name="Jane",
            last_name="Smith",
            job_title="Chief of Staff",
            confidence=94,
        ),
        DomainEmailResult(
            email=f"alex.johnson@{domain}",
            first_name="Alex",
            last_name="Johnson",
            job_title="VP Strategy",
            confidence=88,
        ),
    ][:limit]
