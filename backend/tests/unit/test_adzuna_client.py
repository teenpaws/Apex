"""Unit tests for AdzunaClient."""
import pytest
from unittest.mock import patch, MagicMock
import httpx
from app.integrations.adzuna_client import AdzunaClient, AdzunaPosting


@pytest.fixture
def client():
    return AdzunaClient(app_id="test-id", app_key="test-key", country="gb")


@pytest.mark.asyncio
async def test_search_jobs_returns_postings(client):
    mock_data = {
        "results": [{
            "id": "123",
            "title": "Head of Strategy",
            "company": {"display_name": "Acme Corp"},
            "redirect_url": "https://adzuna.com/job/123",
            "created": "2026-04-20T10:00:00Z",
        }],
        "count": 1,
    }
    with patch.object(client, "_get", return_value=mock_data):
        postings = await client.search_jobs(company_name="Acme Corp", role_keywords="Head of Strategy")
    assert len(postings) == 1
    assert isinstance(postings[0], AdzunaPosting)
    assert postings[0].title == "Head of Strategy"
    assert postings[0].company == "Acme Corp"


@pytest.mark.asyncio
async def test_search_jobs_returns_empty_on_no_results(client):
    with patch.object(client, "_get", return_value={"results": [], "count": 0}):
        postings = await client.search_jobs(company_name="Unknown Corp XYZ", role_keywords="Nonexistent Role")
    assert postings == []


@pytest.mark.asyncio
async def test_search_jobs_handles_http_error(client):
    with patch.object(client, "_get", side_effect=httpx.HTTPStatusError("404", request=MagicMock(), response=MagicMock(status_code=404))):
        postings = await client.search_jobs(company_name="Test Co", role_keywords="Some Role")
    assert postings == []


def test_adzuna_posting_schema():
    p = AdzunaPosting(title="Strategy Manager", company="Bain", url="https://adzuna.com/1", posted_date="2026-04-20")
    assert p.title == "Strategy Manager"
