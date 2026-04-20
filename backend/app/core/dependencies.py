"""
FastAPI dependency injection for Apex.

Provides reusable dependencies (current user, DB session, etc.)
that can be injected into route handlers via Depends().
"""

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings
from app.core.security import get_token_from_header, verify_token

# HTTPBearer shows a simple "Value: <token>" input in Swagger UI.
bearer_scheme = HTTPBearer(auto_error=False)

# Fixed mock user returned when USE_MOCK_DATA=True — no token required.
MOCK_USER = {"id": "mock-user-id", "email": "test@apex.ai"}


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
) -> dict:
    """
    Validate the Bearer JWT and return the authenticated user dict.

    In mock mode (USE_MOCK_DATA=True), skips validation entirely and
    returns a fixed test user so the full pipeline can be exercised
    without a live Supabase project.

    Returns:
        dict with at minimum {"id": str, "email": str}

    Raises:
        HTTPException 401 when not in mock mode and no valid token is provided.
    """
    settings = get_settings()

    if settings.USE_MOCK_DATA:
        return MOCK_USER

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    payload = verify_token(token)

    user_id = payload.get("sub")
    email = payload.get("email")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload missing 'sub' claim",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {"id": user_id, "email": email or ""}
