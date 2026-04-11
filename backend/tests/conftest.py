"""
Test configuration and fixtures for the Apex backend.
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
import os

# Set test environment vars before importing app
os.environ["USE_MOCK_DATA"] = "true"
os.environ["MOCK_AGENTS"] = "true"
os.environ["DATABASE_URL"] = "postgresql://test:test@localhost:5432/apex_test"
os.environ["SUPABASE_URL"] = "https://placeholder.supabase.co"
os.environ["SUPABASE_ANON_KEY"] = "placeholder"
os.environ["SUPABASE_SERVICE_ROLE_KEY"] = "placeholder"
os.environ["ANTHROPIC_API_KEY"] = "placeholder"
os.environ["OPENAI_API_KEY"] = "placeholder"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"
os.environ["CELERY_BROKER_URL"] = "redis://localhost:6379/1"

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture
async def async_client():
    """Async test client for FastAPI app."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        yield client


@pytest.fixture
def mock_user():
    """Mock authenticated user for testing."""
    return {"id": "mock-user-id", "email": "test@apex.ai"}
