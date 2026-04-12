"""
Unit tests for CareerFitScorerAgent.

Tests cover:
  - Mock mode: loads fixture, returns validated output (no Claude API calls)
  - MBA profile + strategy role → fit_score >= 70
  - Output schema validation via Pydantic
  - Fixture file matches expected output schema
  - No Claude API call made in mock mode
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

_MODULE = "app.agents.career_fit_scorer"

FIXTURE_PATH = (
    Path(__file__).parent.parent.parent
    / "app" / "agents" / "fixtures" / "career_fit_scorer_mock_output.json"
)


def _mba_strategy_input() -> dict:
    return {
        "user_id": "user-001",
        "opportunity_id": "opp-001",
        "opportunity": {
            "predicted_role": "VP of Strategy",
            "confidence": "HIGH",
            "why_fit": "MBA background aligns with strategy leadership needs.",
            "positioning_notes": "Lead with HEC Paris network.",
        },
        "user_profile": {
            "current_role": "Senior Strategy Consultant",
            "target_roles": ["VP Strategy", "Principal"],
            "industries": ["Consulting", "Technology"],
            "aspirations_text": "Lead AI transformation for global enterprises.",
            "skills": ["Strategy", "AI/ML", "Change Management", "Executive Presentations"],
            "embedding_summary": "Strategy-focused MBA profile with AI consulting experience.",
        },
    }


def _weak_fit_input() -> dict:
    return {
        "user_id": "user-001",
        "opportunity_id": "opp-002",
        "opportunity": {
            "predicted_role": "Senior Software Engineer (ML Infrastructure)",
            "confidence": "MEDIUM",
            "why_fit": "Company is building ML infra team.",
            "positioning_notes": "Technical background needed.",
        },
        "user_profile": {
            "current_role": "Marketing Manager",
            "target_roles": ["Senior Marketing Manager"],
            "industries": ["Consumer Goods"],
            "aspirations_text": "Grow into brand strategy leadership.",
            "skills": ["Brand Strategy", "Consumer Research", "Campaign Management"],
            "embedding_summary": "Marketing-focused profile, no engineering background.",
        },
    }


# ===========================================================================
# Mock mode tests
# ===========================================================================

class TestCareerFitScorerMockMode:

    @pytest.fixture(autouse=True)
    def _import(self):
        pytest.importorskip(_MODULE)

    @pytest.mark.asyncio
    async def test_mock_returns_output(self):
        from app.agents.career_fit_scorer import CareerFitScorerAgent
        from app.core.config import get_settings

        agent = CareerFitScorerAgent(settings=get_settings())
        result = await agent.score(_mba_strategy_input())
        assert result is not None

    @pytest.mark.asyncio
    async def test_mock_output_has_fit_score(self):
        from app.agents.career_fit_scorer import CareerFitScorerAgent
        from app.core.config import get_settings

        agent = CareerFitScorerAgent(settings=get_settings())
        result = await agent.score(_mba_strategy_input())
        assert isinstance(result.fit_score, float)
        assert 0.0 <= result.fit_score <= 100.0

    @pytest.mark.asyncio
    async def test_mba_strategy_profile_scores_above_70(self):
        """MBA + strategy profile scoring against a VP Strategy role should score >= 70."""
        from app.agents.career_fit_scorer import CareerFitScorerAgent
        from app.core.config import get_settings

        agent = CareerFitScorerAgent(settings=get_settings())
        result = await agent.score(_mba_strategy_input())
        # Default mock fixture has fit_score = 82.5
        assert result.fit_score >= 70, (
            f"Expected fit_score >= 70 for MBA strategy profile, got {result.fit_score}"
        )

    @pytest.mark.asyncio
    async def test_mock_output_has_fit_explanation(self):
        from app.agents.career_fit_scorer import CareerFitScorerAgent
        from app.core.config import get_settings

        agent = CareerFitScorerAgent(settings=get_settings())
        result = await agent.score(_mba_strategy_input())
        assert result.fit_explanation
        assert isinstance(result.fit_explanation, str)

    @pytest.mark.asyncio
    async def test_mock_output_skill_gaps_is_list(self):
        from app.agents.career_fit_scorer import CareerFitScorerAgent
        from app.core.config import get_settings

        agent = CareerFitScorerAgent(settings=get_settings())
        result = await agent.score(_mba_strategy_input())
        assert isinstance(result.skill_gaps, list)

    @pytest.mark.asyncio
    async def test_mock_no_claude_api_call(self):
        from app.agents.career_fit_scorer import CareerFitScorerAgent
        from app.core.config import get_settings

        with patch("anthropic.AsyncAnthropic") as mock_client:
            agent = CareerFitScorerAgent(settings=get_settings())
            await agent.score(_mba_strategy_input())
            mock_client.assert_not_called()

    @pytest.mark.asyncio
    async def test_run_method_returns_dict(self):
        from app.agents.career_fit_scorer import CareerFitScorerAgent
        from app.core.config import get_settings

        agent = CareerFitScorerAgent(settings=get_settings())
        result = await agent.run(_mba_strategy_input())
        assert isinstance(result, dict)
        assert "fit_score" in result

    @pytest.mark.asyncio
    async def test_mock_deterministic(self):
        """Mock output is deterministic — same fixture on repeated calls."""
        from app.agents.career_fit_scorer import CareerFitScorerAgent
        from app.core.config import get_settings

        agent = CareerFitScorerAgent(settings=get_settings())
        result1 = await agent.score(_mba_strategy_input())
        result2 = await agent.score(_mba_strategy_input())
        assert result1.fit_score == result2.fit_score


# ===========================================================================
# Low-relevance fixture injection test
# ===========================================================================

class TestCareerFitScorerLowFit:

    @pytest.fixture(autouse=True)
    def _import(self):
        pytest.importorskip(_MODULE)

    @pytest.mark.asyncio
    async def test_low_fit_score_when_injected(self):
        """Injecting a low-score fixture returns fit_score < 40."""
        from app.agents.career_fit_scorer import CareerFitScorerAgent
        from app.core.config import get_settings

        low_fit_fixture = {
            "fit_score": 22.0,
            "fit_explanation": "Profile has no engineering background for ML infra role.",
            "skill_gaps": ["Python", "ML Infrastructure", "Distributed Systems"],
        }

        agent = CareerFitScorerAgent(settings=get_settings())
        with patch.object(agent, "_load_mock_fixture", return_value=low_fit_fixture):
            result = await agent.score(_weak_fit_input())

        assert result.fit_score < 40


# ===========================================================================
# Fixture file tests
# ===========================================================================

class TestCareerFitScorerFixture:

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

    def test_fixture_has_fit_score(self):
        if not FIXTURE_PATH.exists():
            pytest.skip("Fixture not created yet")
        data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        assert "fit_score" in data
        assert isinstance(data["fit_score"], (int, float))
        assert 0.0 <= data["fit_score"] <= 100.0

    def test_fixture_has_fit_explanation(self):
        if not FIXTURE_PATH.exists():
            pytest.skip("Fixture not created yet")
        data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        assert "fit_explanation" in data
        assert isinstance(data["fit_explanation"], str)

    def test_fixture_has_skill_gaps_list(self):
        if not FIXTURE_PATH.exists():
            pytest.skip("Fixture not created yet")
        data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        assert "skill_gaps" in data
        assert isinstance(data["skill_gaps"], list)


# ===========================================================================
# Output schema validation
# ===========================================================================

class TestCareerFitScorerOutputSchema:

    @pytest.fixture(autouse=True)
    def _import(self):
        pytest.importorskip(_MODULE)

    def test_output_rejects_fit_score_above_100(self):
        from app.agents.career_fit_scorer import CareerFitScorerOutput
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            CareerFitScorerOutput(
                fit_score=105.0,
                fit_explanation="Test",
                skill_gaps=[],
            )

    def test_output_rejects_fit_score_below_0(self):
        from app.agents.career_fit_scorer import CareerFitScorerOutput
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            CareerFitScorerOutput(
                fit_score=-5.0,
                fit_explanation="Test",
                skill_gaps=[],
            )

    def test_valid_output_roundtrips(self):
        from app.agents.career_fit_scorer import CareerFitScorerOutput

        obj = CareerFitScorerOutput(
            fit_score=82.5,
            fit_explanation="Strong alignment on strategy and MBA background.",
            skill_gaps=["Industry-specific domain expertise"],
        )
        data = obj.model_dump(mode="json")
        assert data["fit_score"] == 82.5
        assert len(data["skill_gaps"]) == 1
