"""
Unit tests for PositioningAdvisorAgent.

Tests cover:
  - Mock mode: loads fixture, returns validated output (no Claude API calls)
  - Output schema validation via Pydantic
  - Fixture file matches expected output schema
  - No Claude API call made in mock mode
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

_MODULE = "app.agents.positioning_advisor"

FIXTURE_PATH = (
    Path(__file__).parent.parent.parent
    / "app" / "agents" / "fixtures" / "positioning_advisor_mock_output.json"
)


def _sample_input() -> dict:
    return {
        "user_id": "user-001",
        "opportunity_id": "opp-001",
        "user_profile": {
            "current_role": "Senior Strategy Consultant",
            "aspirations_text": "Lead AI transformation for global enterprises.",
            "skills": ["Strategy", "AI/ML", "Change Management"],
            "career_history_summary": (
                "5 years at Bain, 2 years at an AI startup, HEC Paris MBA 2024."
            ),
        },
        "opportunity": {
            "predicted_role": "VP of Strategy",
            "confidence": "HIGH",
            "why_fit": "MBA background aligns with digital transformation leadership.",
            "ideal_contact_title": "Chief of Staff",
        },
        "company_signals": [
            {
                "signal_type": "FUNDING",
                "title": "McKinsey Raises $500M AI Fund",
                "description": "McKinsey plans to hire 2,000 AI strategy consultants.",
                "signal_date": "2026-04-10T09:00:00Z",
            }
        ],
    }


# ===========================================================================
# Mock mode tests
# ===========================================================================

class TestPositioningAdvisorMockMode:

    @pytest.fixture(autouse=True)
    def _import(self):
        pytest.importorskip(_MODULE)

    @pytest.mark.asyncio
    async def test_mock_returns_output(self):
        from app.agents.positioning_advisor import PositioningAdvisorAgent
        from app.core.config import get_settings

        agent = PositioningAdvisorAgent(settings=get_settings())
        result = await agent.advise(_sample_input())
        assert result is not None

    @pytest.mark.asyncio
    async def test_mock_output_has_positioning_narrative(self):
        from app.agents.positioning_advisor import PositioningAdvisorAgent
        from app.core.config import get_settings

        agent = PositioningAdvisorAgent(settings=get_settings())
        result = await agent.advise(_sample_input())
        assert result.positioning_narrative
        assert isinstance(result.positioning_narrative, str)
        assert len(result.positioning_narrative) > 20

    @pytest.mark.asyncio
    async def test_mock_output_has_key_talking_points(self):
        from app.agents.positioning_advisor import PositioningAdvisorAgent
        from app.core.config import get_settings

        agent = PositioningAdvisorAgent(settings=get_settings())
        result = await agent.advise(_sample_input())
        assert isinstance(result.key_talking_points, list)
        assert len(result.key_talking_points) >= 1

    @pytest.mark.asyncio
    async def test_mock_output_has_approach_angle(self):
        from app.agents.positioning_advisor import PositioningAdvisorAgent
        from app.core.config import get_settings

        agent = PositioningAdvisorAgent(settings=get_settings())
        result = await agent.advise(_sample_input())
        assert result.approach_angle
        assert isinstance(result.approach_angle, str)

    @pytest.mark.asyncio
    async def test_mock_no_claude_api_call(self):
        from app.agents.positioning_advisor import PositioningAdvisorAgent
        from app.core.config import get_settings

        with patch("anthropic.AsyncAnthropic") as mock_client:
            agent = PositioningAdvisorAgent(settings=get_settings())
            await agent.advise(_sample_input())
            mock_client.assert_not_called()

    @pytest.mark.asyncio
    async def test_run_method_returns_dict(self):
        from app.agents.positioning_advisor import PositioningAdvisorAgent
        from app.core.config import get_settings

        agent = PositioningAdvisorAgent(settings=get_settings())
        result = await agent.run(_sample_input())
        assert isinstance(result, dict)
        assert "positioning_narrative" in result
        assert "key_talking_points" in result
        assert "approach_angle" in result


# ===========================================================================
# Fixture file tests
# ===========================================================================

class TestPositioningAdvisorFixture:

    @pytest.fixture(autouse=True)
    def _import(self):
        pytest.importorskip(_MODULE)

    def test_fixture_file_exists(self):
        assert FIXTURE_PATH.exists(), f"Fixture not found: {FIXTURE_PATH}"

    def test_fixture_is_valid_json(self):
        if not FIXTURE_PATH.exists():
            pytest.skip("Fixture not created yet")
        data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        assert isinstance(data, dict)

    def test_fixture_has_positioning_narrative(self):
        if not FIXTURE_PATH.exists():
            pytest.skip("Fixture not created yet")
        data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        assert "positioning_narrative" in data
        assert isinstance(data["positioning_narrative"], str)
        assert len(data["positioning_narrative"]) > 10

    def test_fixture_has_key_talking_points(self):
        if not FIXTURE_PATH.exists():
            pytest.skip("Fixture not created yet")
        data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        assert "key_talking_points" in data
        assert isinstance(data["key_talking_points"], list)

    def test_fixture_has_approach_angle(self):
        if not FIXTURE_PATH.exists():
            pytest.skip("Fixture not created yet")
        data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        assert "approach_angle" in data
        assert isinstance(data["approach_angle"], str)


# ===========================================================================
# Output schema validation
# ===========================================================================

class TestPositioningAdvisorOutputSchema:

    @pytest.fixture(autouse=True)
    def _import(self):
        pytest.importorskip(_MODULE)

    def test_output_requires_positioning_narrative(self):
        from app.agents.positioning_advisor import PositioningAdvisorOutput
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            PositioningAdvisorOutput(
                key_talking_points=["Point 1"],
                approach_angle="Lead with funding milestone",
            )

    def test_output_requires_approach_angle(self):
        from app.agents.positioning_advisor import PositioningAdvisorOutput
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            PositioningAdvisorOutput(
                positioning_narrative="I have relevant experience...",
                key_talking_points=["Point 1"],
            )

    def test_valid_output_roundtrips(self):
        from app.agents.positioning_advisor import PositioningAdvisorOutput

        obj = PositioningAdvisorOutput(
            positioning_narrative="As an HEC Paris MBA with AI consulting experience...",
            key_talking_points=["AI strategy expertise", "HEC Paris network"],
            approach_angle="Lead with shared alumni network.",
        )
        data = obj.model_dump(mode="json")
        assert len(data["key_talking_points"]) == 2
        assert data["approach_angle"] == "Lead with shared alumni network."
