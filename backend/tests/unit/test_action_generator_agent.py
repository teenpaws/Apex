"""
Unit tests for ActionGeneratorAgent.

Tests cover:
  - Mock mode: loads fixture, returns validated output (no Claude API calls)
  - 1 opportunity → 2–4 actions with correct priority
  - HIGH fit_score + HIGH confidence → HIGH priority OUTREACH action
  - Output schema validation via Pydantic
  - Fixture file matches expected output schema
  - No Claude API call made in mock mode
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

_MODULE = "app.agents.action_generator"

FIXTURE_PATH = (
    Path(__file__).parent.parent.parent
    / "app" / "agents" / "fixtures" / "action_generator_mock_output.json"
)


def _high_confidence_input() -> dict:
    return {
        "user_id": "user-001",
        "opportunity_id": "opp-001",
        "opportunity": {
            "predicted_role": "VP of Strategy",
            "confidence": "HIGH",
            "timeline_weeks": 6,
            "why_fit": "MBA background aligns with digital transformation needs.",
            "ideal_contact_title": "Chief of Staff",
            "company_name": "McKinsey & Company",
        },
        "fit_score": 82.5,
        "contacts": [
            {
                "name": "Jane Smith",
                "title": "Chief of Staff",
                "linkedin_url": "https://linkedin.com/in/janesmith",
            }
        ],
    }


def _low_confidence_input() -> dict:
    return {
        "user_id": "user-001",
        "opportunity_id": "opp-002",
        "opportunity": {
            "predicted_role": "Strategy Analyst",
            "confidence": "SPECULATIVE",
            "timeline_weeks": 10,
            "why_fit": "Weak signal from a minor press mention.",
            "ideal_contact_title": "Unknown",
            "company_name": "Acme Corp",
        },
        "fit_score": 45.0,
        "contacts": [],
    }


# ===========================================================================
# Mock mode tests
# ===========================================================================

class TestActionGeneratorMockMode:

    @pytest.fixture(autouse=True)
    def _import(self):
        pytest.importorskip(_MODULE)

    @pytest.mark.asyncio
    async def test_mock_returns_output(self):
        from app.agents.action_generator import ActionGeneratorAgent
        from app.core.config import get_settings

        agent = ActionGeneratorAgent(settings=get_settings())
        result = await agent.generate(_high_confidence_input())
        assert result is not None

    @pytest.mark.asyncio
    async def test_mock_output_has_actions_list(self):
        from app.agents.action_generator import ActionGeneratorAgent
        from app.core.config import get_settings

        agent = ActionGeneratorAgent(settings=get_settings())
        result = await agent.generate(_high_confidence_input())
        assert isinstance(result.actions, list)
        assert len(result.actions) >= 1

    @pytest.mark.asyncio
    async def test_mock_1_opportunity_produces_2_to_4_actions(self):
        """1 opportunity should produce 2–4 action items."""
        from app.agents.action_generator import ActionGeneratorAgent
        from app.core.config import get_settings

        agent = ActionGeneratorAgent(settings=get_settings())
        result = await agent.generate(_high_confidence_input())
        assert 2 <= len(result.actions) <= 4, (
            f"Expected 2–4 actions, got {len(result.actions)}"
        )

    @pytest.mark.asyncio
    async def test_mock_actions_have_required_fields(self):
        from app.agents.action_generator import ActionGeneratorAgent
        from app.core.config import get_settings

        agent = ActionGeneratorAgent(settings=get_settings())
        result = await agent.generate(_high_confidence_input())
        for action in result.actions:
            assert action.title
            assert action.type in ("OUTREACH", "RESEARCH", "FOLLOW_UP", "CALL")
            assert action.priority in ("HIGH", "MEDIUM", "LOW")
            assert action.due_date.startswith("+")

    @pytest.mark.asyncio
    async def test_mock_high_fit_produces_high_priority_action(self):
        """fit_score >= 70 + confidence HIGH should yield at least one HIGH priority action."""
        from app.agents.action_generator import ActionGeneratorAgent
        from app.core.config import get_settings

        agent = ActionGeneratorAgent(settings=get_settings())
        result = await agent.generate(_high_confidence_input())
        priorities = [a.priority for a in result.actions]
        assert "HIGH" in priorities, (
            f"Expected at least one HIGH priority action for high-confidence + high fit, "
            f"got priorities: {priorities}"
        )

    @pytest.mark.asyncio
    async def test_mock_no_claude_api_call(self):
        from app.agents.action_generator import ActionGeneratorAgent
        from app.core.config import get_settings

        with patch("anthropic.AsyncAnthropic") as mock_client:
            agent = ActionGeneratorAgent(settings=get_settings())
            await agent.generate(_high_confidence_input())
            mock_client.assert_not_called()

    @pytest.mark.asyncio
    async def test_run_method_returns_dict(self):
        from app.agents.action_generator import ActionGeneratorAgent
        from app.core.config import get_settings

        agent = ActionGeneratorAgent(settings=get_settings())
        result = await agent.run(_high_confidence_input())
        assert isinstance(result, dict)
        assert "actions" in result
        assert isinstance(result["actions"], list)


# ===========================================================================
# Low confidence / low fit scenario
# ===========================================================================

class TestActionGeneratorLowFitScenario:

    @pytest.fixture(autouse=True)
    def _import(self):
        pytest.importorskip(_MODULE)

    @pytest.mark.asyncio
    async def test_low_fit_fixture_produces_valid_actions(self):
        """Injecting a low-fit fixture still returns valid action objects."""
        from app.agents.action_generator import ActionGeneratorAgent
        from app.core.config import get_settings

        low_fit_fixture = {
            "actions": [
                {
                    "title": "Research Acme Corp strategy team",
                    "type": "RESEARCH",
                    "priority": "LOW",
                    "due_date": "+7d",
                },
                {
                    "title": "Monitor for stronger hiring signals",
                    "type": "RESEARCH",
                    "priority": "LOW",
                    "due_date": "+14d",
                },
            ]
        }

        agent = ActionGeneratorAgent(settings=get_settings())
        with patch.object(agent, "_load_mock_fixture", return_value=low_fit_fixture):
            result = await agent.generate(_low_confidence_input())

        assert len(result.actions) == 2
        for action in result.actions:
            assert action.priority == "LOW"
            assert action.type == "RESEARCH"


# ===========================================================================
# Fixture file tests
# ===========================================================================

class TestActionGeneratorFixture:

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

    def test_fixture_has_actions_list(self):
        if not FIXTURE_PATH.exists():
            pytest.skip("Fixture not created yet")
        data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        assert "actions" in data
        assert isinstance(data["actions"], list)
        assert len(data["actions"]) >= 1

    def test_fixture_actions_have_required_fields(self):
        if not FIXTURE_PATH.exists():
            pytest.skip("Fixture not created yet")
        data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        for action in data["actions"]:
            assert "title" in action
            assert "type" in action
            assert "priority" in action
            assert "due_date" in action

    def test_fixture_action_types_are_valid(self):
        if not FIXTURE_PATH.exists():
            pytest.skip("Fixture not created yet")
        valid_types = {"OUTREACH", "RESEARCH", "FOLLOW_UP", "CALL"}
        data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        for action in data["actions"]:
            assert action["type"] in valid_types, (
                f"Invalid action type: {action['type']}"
            )

    def test_fixture_action_priorities_are_valid(self):
        if not FIXTURE_PATH.exists():
            pytest.skip("Fixture not created yet")
        valid_priorities = {"HIGH", "MEDIUM", "LOW"}
        data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        for action in data["actions"]:
            assert action["priority"] in valid_priorities, (
                f"Invalid priority: {action['priority']}"
            )


# ===========================================================================
# Output schema validation
# ===========================================================================

class TestActionGeneratorOutputSchema:

    @pytest.fixture(autouse=True)
    def _import(self):
        pytest.importorskip(_MODULE)

    def test_action_item_rejects_invalid_type(self):
        from app.agents.action_generator import ActionItem
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ActionItem(
                title="Do something",
                type="INVALID_TYPE",
                priority="HIGH",
                due_date="+3d",
            )

    def test_action_item_rejects_invalid_priority(self):
        from app.agents.action_generator import ActionItem
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ActionItem(
                title="Do something",
                type="RESEARCH",
                priority="CRITICAL",  # invalid
                due_date="+3d",
            )

    def test_valid_action_item_roundtrips(self):
        from app.agents.action_generator import ActionItem

        obj = ActionItem(
            title="Research McKinsey strategy team",
            type="RESEARCH",
            priority="HIGH",
            due_date="+2d",
        )
        data = obj.model_dump(mode="json")
        assert data["type"] == "RESEARCH"
        assert data["priority"] == "HIGH"

    def test_valid_output_roundtrips(self):
        from app.agents.action_generator import ActionGeneratorOutput, ActionItem

        obj = ActionGeneratorOutput(
            actions=[
                ActionItem(title="Research team", type="RESEARCH", priority="HIGH", due_date="+2d"),
                ActionItem(title="Draft outreach email", type="OUTREACH", priority="HIGH", due_date="+5d"),
            ]
        )
        data = obj.model_dump(mode="json")
        assert len(data["actions"]) == 2
