"""
Unit tests for the structured error handling layer (app/core/errors.py).

Tests confirm:
1. ApexHTTPException routes are serialised with the ErrorDetail shape.
2. 404 on a non-existent route returns a FastAPI 404 (standard shape acceptable).
"""
import pytest
from fastapi import APIRouter
from fastapi.testclient import TestClient

from app.main import app
from app.core.errors import ApexHTTPException


# ── Helper: mount a test-only route that raises ApexHTTPException ──────────────

_test_router = APIRouter(prefix="/test-errors", tags=["test-errors"])


@_test_router.get("/raise-apex")
async def _raise_apex():
    """Route used purely for testing the error handler."""
    raise ApexHTTPException(
        status_code=400,
        error="Test error",
        detail="Some extra detail",
        code="TEST_CODE",
    )


@_test_router.get("/raise-apex-no-detail")
async def _raise_apex_no_detail():
    raise ApexHTTPException(
        status_code=403,
        error="Forbidden action",
        code="FORBIDDEN",
    )


# Register the test router on the real app once (idempotent — pytest reuses the app).
# We guard against double-registration by checking existing routes.
_existing_paths = {r.path for r in app.routes}  # type: ignore[attr-defined]
if "/test-errors/raise-apex" not in _existing_paths:
    app.include_router(_test_router, prefix="/api/v1")


# ── Tests ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_apex_exception_returns_error_detail_shape(async_client):
    """
    A route that raises ApexHTTPException must return a response with exactly
    the ErrorDetail shape: {error, detail, code}.
    """
    response = await async_client.get("/api/v1/test-errors/raise-apex")
    assert response.status_code == 400
    data = response.json()

    # All three keys must be present
    assert "error" in data
    assert "detail" in data
    assert "code" in data

    assert data["error"] == "Test error"
    assert data["detail"] == "Some extra detail"
    assert data["code"] == "TEST_CODE"


@pytest.mark.asyncio
async def test_apex_exception_null_detail_allowed(async_client):
    """ErrorDetail with no detail serialises detail as null."""
    response = await async_client.get("/api/v1/test-errors/raise-apex-no-detail")
    assert response.status_code == 403
    data = response.json()
    assert data["error"] == "Forbidden action"
    assert data["detail"] is None
    assert data["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_structured_error_on_404(async_client):
    """
    GET on a non-existent route returns 404.
    FastAPI's default 404 is acceptable — no requirement to override it.
    """
    response = await async_client.get("/api/v1/nonexistent-route-xyz")
    assert response.status_code == 404
