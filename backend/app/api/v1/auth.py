"""
Auth endpoints — POST /auth/login, POST /auth/refresh

Mock mode (USE_MOCK_DATA=true): returns fixture tokens without touching Supabase.
Live mode: proxies to Supabase Auth REST API via httpx.
"""

import httpx
from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, EmailStr

from app.core.config import get_settings
from app.core.errors import ApexHTTPException

router = APIRouter(prefix="/auth", tags=["auth"])

# ── Mock constants ─────────────────────────────────────────────────────────────
_MOCK_EMAIL = "test@apex.dev"
_MOCK_USER_ID = "00000000-0000-0000-0000-000000000001"
_MOCK_TOKEN = "mock-token"
_MOCK_REFRESH_TOKEN = "mock-token-refreshed"


# ── Request / Response models ──────────────────────────────────────────────────

class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    access_token: str
    token_type: str = "bearer"
    user: dict  # {id, email}


class RefreshRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    refresh_token: str


class RefreshResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    access_token: str
    token_type: str = "bearer"


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Login with email + password",
    description=(
        "Authenticate a user. In mock mode returns a fixture token for test@apex.dev. "
        "In live mode proxies to Supabase Auth."
    ),
)
async def login(body: LoginRequest) -> LoginResponse:
    settings = get_settings()

    if settings.USE_MOCK_DATA:
        if body.email != _MOCK_EMAIL:
            raise ApexHTTPException(
                status_code=401,
                error="Invalid credentials",
                code="AUTH_INVALID_CREDENTIALS",
            )
        return LoginResponse(
            access_token=_MOCK_TOKEN,
            token_type="bearer",
            user={"id": _MOCK_USER_ID, "email": _MOCK_EMAIL},
        )

    # Live mode — call Supabase Auth REST API
    url = f"{settings.SUPABASE_URL}/auth/v1/token?grant_type=password"
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                url,
                json={"email": body.email, "password": body.password},
                headers={"apikey": settings.SUPABASE_ANON_KEY},
                timeout=10.0,
            )
        except httpx.RequestError as exc:
            raise ApexHTTPException(
                status_code=503,
                error="Authentication service unavailable",
                detail=str(exc),
                code="AUTH_SERVICE_UNAVAILABLE",
            ) from exc

    if resp.status_code != 200:
        raise ApexHTTPException(
            status_code=401,
            error="Authentication failed",
            code="AUTH_FAILED",
        )

    data = resp.json()
    access_token = data.get("access_token", "")
    user_data = data.get("user", {})
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user={"id": user_data.get("id", ""), "email": user_data.get("email", "")},
    )


@router.post(
    "/refresh",
    response_model=RefreshResponse,
    summary="Refresh an access token",
    description=(
        "Exchange a refresh token for a new access token. "
        "In mock mode returns a fixture refreshed token. "
        "In live mode proxies to Supabase Auth."
    ),
)
async def refresh(body: RefreshRequest) -> RefreshResponse:
    settings = get_settings()

    if settings.USE_MOCK_DATA:
        return RefreshResponse(
            access_token=_MOCK_REFRESH_TOKEN,
            token_type="bearer",
        )

    # Live mode — call Supabase Auth REST API
    url = f"{settings.SUPABASE_URL}/auth/v1/token?grant_type=refresh_token"
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                url,
                json={"refresh_token": body.refresh_token},
                headers={"apikey": settings.SUPABASE_ANON_KEY},
                timeout=10.0,
            )
        except httpx.RequestError as exc:
            raise ApexHTTPException(
                status_code=503,
                error="Authentication service unavailable",
                detail=str(exc),
                code="AUTH_SERVICE_UNAVAILABLE",
            ) from exc

    if resp.status_code != 200:
        raise ApexHTTPException(
            status_code=401,
            error="Authentication failed",
            code="AUTH_FAILED",
        )

    data = resp.json()
    return RefreshResponse(
        access_token=data.get("access_token", ""),
        token_type="bearer",
    )
