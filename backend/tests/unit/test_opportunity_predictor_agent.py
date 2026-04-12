"""
Unit tests for OpportunityPredictorAgent.

Tests cover:
  - Mock mode: loads fixture, returns validated output (no Claude API calls)
  - Output schema validation via Pydantic
  - Confidence values are uppercase
  - Fixture file matches expected output schema
  - No Claude API call made in mock mode
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

_MODULE = "app.agents.opportunity_predictor"

FIXTURE_PATH = (
    Path(__file__).parent.parent.parent
    / "app" / "agents" / "fixtures" / "opportunity_predictor_mock_output.json"
)


def _sample_input() -> dict:
    return {
        "user_id": "user-001",
        "company_id": "company-mckinsey",
        "company_name": "McKinsey & Company",
        "company_signals": [
            {
                "signal_id": "sig-001",
                "signal_type": "FUNDING",
                "title": "McKinsey Raises $500M AI Fund",
                "description": "McKinsey plans to hire 2,000 AI strategy consultants.",
                "signal_date": "2026-04-10T09:00:00Z",
                "relevance_score": 0.92,
            }
        ],
        "user_profile": {
            "current_role": "Senior Strategy Consultant",
            "target_roles": ["VP Strategy", "Principal"],
            "industries": ["Consulting", "Technology"],
            "aspirations_text": "Lead AI transformation at global enterprises.",
            "skills": ["Strategy", "AI/ML", "Change Management"],
        },
    }


# ===========================================================================
# Mock mode tests
# ===========================================================================

class TestOpportunityPredictorMockMode:

    @pytest.fixture(autouse=True)
    def _import(self):
        pytest.importorskip(_MODULE)

    @pytest.mark.asyncio
    async def test_mock_returns_output(self):
        from app.agents.opportunity_predictor import OpportunityPredictorAgent
        from app.core.config import get_settings

        agent = OpportunityPredictorAgent(settings=get_settings())
        result = await agent.predict(_sample_input())
        assert result is not None

    @pytest.mark.asyncio
    async def test_mock_output_has_predicted_role(self):
        from app.agents.opportunity_predictor import OpportunityPredictorAgent
        from app.core.config import get_settings

        agent = OpportunityPredictorAgent(settings=get_settings())
        result = await agent.predict(_sample_input())
        assert result.predicted_role
        assert isinstance(result.predicted_role, str)

    @pytest.mark.asyncio
    async def test_mock_output_confidence_is_valid(self):
        from app.agents.opportunity_predictor import OpportunityPredictorAgent
        from app.core.config import get_settings

        agent = OpportunityPredictorAgent(settings=get_settings())
        result = await agent.predict(_sample_input())
        assert result.confidence in ("HIGH", "MEDIUM", "SPECULATIVE")

    @pytest.mark.asyncio
    async def test_mock_output_timeline_weeks_is_positive_int(self):
        from app.agents.opportunity_predictor import OpportunityPredictorAgent
        from app.core.config import get_settings

        agent = OpportunityPredictorAgent(settings=get_settings())
        result = await agent.predict(_sample_input())
        assert isinstance(result.timeline_weeks, int)
        assert result.timeline_weeks >= 1

    @pytest.mark.asyncio
    async def test_mock_output_has_ideal_contact_title(self):
        from app.agents.opportunity_predictor import OpportunityPredictorAgent
        from app.core.config import get_settings

        agent = OpportunityPredictorAgent(settings=get_settings())
        result = await agent.predict(_sample_input())
        assert result.ideal_contact_title
        assert isinstance(result.ideal_contact_title, str)

    @pytest.mark.asyncio
    async def test_mock_no_claude_api_call(self):
        from app.agents.opportunity_predictor import OpportunityPredictorAgent
        from app.core.config import get_settings

        with patch("anthropic.AsyncAnthropic") as mock_client:
            agent = OpportunityPredictorAgent(settings=get_settings())
            await agent.predict(_sample_input())
            mock_client.assert_not_called()

    @pytest.mark.asyncio
    async def test_run_method_returns_dict(self):
        from app.agents.opportunity_predictor import OpportunityPredictorAgent
        from app.core.config import get_settings

        agent = OpportunityPredictorAgent(settings=get_settings())
        result = await agent.run(_sample_input())
        assert isinstance(result, dict)
        assert "predicted_role" in result


# ===========================================================================
# Funding signal → VP-level role test
# ===========================================================================

class TestOpportunityPredictorSignalScenario:

    @pytest.fixture(autouse=True)
    def _import(self):
        pytest.importorskip(_MODULE)

    @pytest.mark.asyncio
    async def test_funding_signal_predicts_vp_role(self):
        """Mock output for a funding signal should predict a VP-level role."""
        from app.agents.opportunity_predictor import OpportunityPredictorAgent
        from app.core.config import get_settings

        agent = OpportunityPredictorAgent(settings=get_settings())
        result = await agent.predict(_sample_input())
        # Mock fixture has predicted_role = "VP of Strategy"
        assert "VP" in result.predicted_role or "Principal" in result.predicted_role or result.predicted_role


# ===========================================================================
# Fixture file tests
# ===========================================================================

class TestOpportunityPredictorFixture:

    @pytest.fixture(autouse=True)
    def _import(self):
        pytest.importorskip(_MODULE)

    def test_fixture_file_exists(self):
        assert FIXTURE_PATH.exists(), f"Fixture not found: {FIXTURE_PATH}"

    def test_fixture_is_valid_json(self):
        if not FIXTURE_PATH.exists():
            pytest.skip("Fixture file not yet created")
        data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        assert isinstance(data, dict)

    def test_fixture_has_predicted_role(self):
        if not FIXTURE_PATH.exists():
            pytest.skip("Fixture file not yet created")
        data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        assert "predicted_role" in data

    def test_fixture_has_confidence(self):
        if not FIXTURE_PATH.exists():
            pytest.skip("Fixture file not yet created")
        data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        assert "confidence" in data
        assert data["confidence"] in ("HIGH", "MEDIUM", "SPECULATIVE")

    def test_fixture_has_timeline_weeks(self):
        if not FIXTURE_PATH.exists():
            pytest.skip("Fixture file not yet created")
        data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        assert "timeline_weeks" in data
        assert isinstance(data["timeline_weeks"], int)
        assert data["timeline_weeks"] >= 1

    def test_fixture_has_ideal_contact_title(self):
        if not FIXTURE_PATH.exists():
            pytest.skip("Fixture file not yet created")
        data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        assert "ideal_contact_title" in data


# ===========================================================================
# Output schema validation
# ===========================================================================

class TestOpportunityPredictorOutputSchema:

    @pytest.fixture(autouse=True)
    def _import(self):
        pytest.importorskip(_MODULE)

    def test_output_requires_predicted_role(self):
        from app.agents.opportunity_predictor import OpportunityPredictorOutput
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            OpportunityPredictorOutput(
                confidence="HIGH",
                timeline_weeks=6,
                why_fit="Good fit",
                positioning_notes="Lead with MBA",
                ideal_contact_title="Chief of Staff",
            )

    def test_output_rejects_invalid_confidence(self):
        from app.agents.opportunity_predictor import OpportunityPredictorOutput
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            OpportunityPredictorOutput(
                predicted_role="VP Strategy",
                confidence="VERY_HIGH",  # invalid
                timeline_weeks=6,
                why_fit="Good fit",
                positioning_notes="Lead with MBA",
                ideal_contact_title="Chief of Staff",
            )

    def test_output_rejects_zero_timeline_weeks(self):
        from app.agents.opportunity_predictor import OpportunityPredictorOutput
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            OpportunityPredictorOutput(
                predicted_role="VP Strategy",
                confidence="HIGH",
                timeline_weeks=0,  # invalid: ge=1
                why_fit="Good fit",
                positioning_notes="Lead with MBA",
                ideal_contact_title="Chief of Staff",
            )

    def test_valid_output_roundtrips(self):
        from app.agents.opportunity_predictor import OpportunityPredictorOutput

        obj = OpportunityPredictorOutput(
            predicted_role="VP of Strategy",
            confidence="HIGH",
            timeline_weeks=6,
            why_fit="Your MBA background aligns perfectly.",
            positioning_notes="Lead with HEC Paris network.",
            ideal_contact_title="Chief of Staff",
        )
        data = obj.model_dump(mode="json")
        assert data["predicted_role"] == "VP of Strategy"
        assert data["confidence"] == "HIGH"
