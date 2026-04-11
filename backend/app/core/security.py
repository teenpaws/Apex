"""
JWT security utilities for Apex — Supabase-compatible token validation.

Supabase issues standard RS256 JWTs signed with the project's JWT secret.
For simplicity in v1.0 we validate using the HS256 algorithm and the
SUPABASE_ANON_KEY as the secret (matches Supabase's default config).
"""

from jose import JWTError, jwt
from fastapi import HTTPException, status

from app.core.config import get_settings

ALGORITHM = "HS256"


def get_token_from_header(authorization: str) -> str:
    """
    Extract the Bearer token from an Authorization header value.

    Args:
        authorization: Raw header value, e.g. "Bearer eyJhbG..."

    Returns:
        The raw JWT string.

    Raises:
        HTTPException 401 if the header is missing or malformed.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header. Expected: 'Bearer <token>'",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return authorization.split(" ", 1)[1]


def verify_token(token: str) -> dict:
    """
    Decode and validate a Supabase JWT.

    Args:
        token: Raw JWT string.

    Returns:
        Decoded payload dict (contains 'sub', 'email', 'role', etc.).

    Raises:
        HTTPException 401 on any validation failure.
    """
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.SUPABASE_ANON_KEY,
            algorithms=[ALGORITHM],
            options={"verify_aud": False},  # Supabase tokens use a custom audience
        )
        return payload
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
