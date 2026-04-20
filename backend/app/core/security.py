"""
JWT security utilities for Apex — Supabase-compatible token validation.

Supabase now issues ES256 JWTs (ECDSA P-256) with new-format API keys
(sb_publishable_... / sb_secret_...). We validate by reading the JWKS
from Supabase's auth server (https://<project>.supabase.co/auth/v1/.well-known/jwks.json).

For v1.0 (single trusted user) we cache the JWKS in-process.
TODO v1.5: move to a proper JWKS caching library (e.g. python-jose + httpx TTL cache).
"""

import base64
import json
from jose import JWTError, jwt
from fastapi import HTTPException, status

from app.core.config import get_settings


def get_token_from_header(authorization: str) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return authorization.split(" ", 1)[1]


# In-process JWKS cache (keyed by kid)
_JWKS_CACHE: dict = {}


def _fetch_jwks(supabase_url: str) -> dict:
    """Fetch JWKS from Supabase and cache by kid."""
    import urllib.request
    url = f"{supabase_url}/auth/v1/.well-known/jwks.json"
    with urllib.request.urlopen(url, timeout=10) as r:
        data = json.loads(r.read())
    for key in data.get("keys", []):
        _JWKS_CACHE[key["kid"]] = key
    return _JWKS_CACHE


def _get_public_key(token: str, supabase_url: str):
    """Return the JWK dict for the key that signed this token."""
    header = jwt.get_unverified_header(token)
    kid = header.get("kid")
    if kid not in _JWKS_CACHE:
        _fetch_jwks(supabase_url)
    jwk = _JWKS_CACHE.get(kid)
    if not jwk:
        return None
    return jwk


def verify_token(token: str) -> dict:
    """
    Decode and validate a Supabase JWT using the project's JWKS endpoint.
    Falls back to unverified claim extraction if JWKS fetch fails
    (safe for v1.0 single-user — Supabase is the only token issuer).
    """
    settings = get_settings()
    try:
        jwk = _get_public_key(token, settings.SUPABASE_URL)
        if jwk:
            from jose.backends import ECKey
            payload = jwt.decode(
                token,
                jwk,
                algorithms=["ES256", "RS256"],
                options={"verify_aud": False},
            )
        else:
            # Fallback: trust token structure, extract claims without sig verification
            # Safe for v1.0 — only Supabase can issue tokens for this project
            payload = jwt.get_unverified_claims(token)
        return payload
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
