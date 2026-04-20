"""
Health check endpoint — GET /api/v1/health

Returns service status, version, environment, and whether mock mode is active.
Used by load balancers, CI pipelines, and the frontend status indicator.
"""

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import get_settings

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    mock_mode: bool


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Service health check",
    description="Returns 200 with service status. Safe to call without authentication.",
)
async def health_check() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
        mock_mode=settings.USE_MOCK_DATA,
    )
