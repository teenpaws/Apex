"""Unit tests for OpportunityValidatorService."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.opportunity_validator import OpportunityValidatorService, ValidationResult
from app.integrations.adzuna_client import AdzunaPosting


@pytest.fixture
def mock_adzuna():
    client = MagicMock()
    client.search_jobs = AsyncMock()
    return client


@pytest.fixture
def validator(mock_adzuna):
    return OpportunityValidatorService(adzuna_client=mock_adzuna)


@pytest.mark.asyncio
async def test_validates_opportunity_with_matching_posting(validator, mock_adzuna):
    mock_adzuna.search_jobs.return_value = [
        AdzunaPosting(title="Head of Strategy EMEA", company="Acme Corp", url="https://adzuna.com/123", posted_date="2026-04-20")
    ]
    result = await validator.validate(company_name="Acme Corp", predicted_role="Head of Strategy")
    assert result.is_validated is True
    assert len(result.real_postings) == 1
    assert result.real_postings[0]["title"] == "Head of Strategy EMEA"


@pytest.mark.asyncio
async def test_not_validated_when_no_postings(validator, mock_adzuna):
    mock_adzuna.search_jobs.return_value = []
    result = await validator.validate(company_name="Unknown Corp", predicted_role="VP of Strategy")
    assert result.is_validated is False
    assert result.real_postings == []


@pytest.mark.asyncio
async def test_validation_result_has_postings_as_dicts(validator, mock_adzuna):
    mock_adzuna.search_jobs.return_value = [
        AdzunaPosting(title="Strategy Lead", company="Bain", url="https://adzuna.com/456", posted_date="2026-04-18")
    ]
    result = await validator.validate(company_name="Bain", predicted_role="Strategy")
    assert isinstance(result.real_postings[0], dict)
    assert all(k in result.real_postings[0] for k in ["title", "url", "company", "posted_date"])
