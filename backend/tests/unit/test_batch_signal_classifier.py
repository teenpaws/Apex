"""Unit tests for BatchSignalClassifierAgent."""
import pytest
from unittest.mock import MagicMock
from datetime import datetime, timezone

from app.agents.batch_signal_classifier import (
    BatchSignalClassifierAgent,
    BatchSignalClassifierInput,
    BatchSignalClassifierOutput,
    SignalBatchItem,
    SignalClassificationResult,
)


@pytest.fixture
def mock_settings():
    s = MagicMock()
    s.MOCK_AGENTS = True
    s.ANTHROPIC_API_KEY = "test-key"
    return s


@pytest.fixture
def agent(mock_settings):
    return BatchSignalClassifierAgent(settings=mock_settings)


@pytest.fixture
def sample_batch_input():
    now = datetime.now(timezone.utc).isoformat()
    return BatchSignalClassifierInput(
        user_id="user-123",
        user_target_industries=["Fintech", "SaaS"],
        user_target_roles=["Strategy", "Operations"],
        signals=[
            SignalBatchItem(
                signal_id=f"sig-{i}",
                title=f"Signal {i} title",
                description=f"Signal {i} description about fintech.",
                source="newsdata.io",
                signal_date=now,
                company_name=f"Company {i}",
            )
            for i in range(3)
        ],
    )


@pytest.mark.asyncio
async def test_classify_batch_mock_mode(agent, sample_batch_input):
    result = await agent.classify_batch(sample_batch_input)
    assert isinstance(result, BatchSignalClassifierOutput)
    assert len(result.results) > 0


@pytest.mark.asyncio
async def test_classify_batch_returns_result_per_signal(agent, sample_batch_input):
    result = await agent.classify_batch(sample_batch_input)
    assert all(isinstance(r, SignalClassificationResult) for r in result.results)


@pytest.mark.asyncio
async def test_classify_batch_result_has_required_fields(agent, sample_batch_input):
    result = await agent.classify_batch(sample_batch_input)
    r = result.results[0]
    assert hasattr(r, "signal_id")
    assert hasattr(r, "signal_type")
    assert hasattr(r, "relevance_score")
    assert 0.0 <= r.relevance_score <= 1.0


@pytest.mark.asyncio
async def test_classify_batch_validates_signal_type(agent, sample_batch_input):
    result = await agent.classify_batch(sample_batch_input)
    valid_types = {"FUNDING", "EXEC_HIRE", "EXPANSION", "LAYOFF", "JOB_POSTING_PATTERN", "MA", "CONTRACT", "EARNINGS", "UNKNOWN"}
    for r in result.results:
        assert r.signal_type in valid_types
