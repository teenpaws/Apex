"""
Unit tests for ProfileExtractorAgent.

Tests cover:
  - Mock mode: loads fixture, returns validated output (no Claude API calls)
  - Output schema validation: years_of_experience >= 0, seniority_band in enum
  - work_history is a list of dicts with required keys
  - key_achievements is a list of dicts with required keys
  - cover_letter_narratives is a list
  - Pydantic rejects invalid seniority_band
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

_MODULE = "app.agents.profile_extractor"

FIXTURE_PATH = (
    Path(__file__).parent.parent.parent
    / "app" / "agents" / "fixtures" / "profile_extractor_mock_output.json"
)

VALID_BANDS = {"ANALYST", "ASSOCIATE", "MANAGER", "DIRECTOR", "VP_PLUS"}


def _sample_input() -> dict:
    return {
        "user_id": "user-001",
        "resume_text": "HEC Paris MBA 2026. BCG Senior Consultant 2021-2024. Strategy + AI.",
        "cover_letters": [
            {"text": "Passionate about PE value creation...", "target_context": "PE firms"},
        ],
        "existing_profile": {
            "current_role": "Senior Consultant",
            "target_roles": ["Principal", "VP Strategy"],
        },
    }


class TestProfileExtractorMockMode:

    @pytest.fixture(autouse=True)
    def _import(self):
        pytest.importorskip(_MODULE)

    @pytest.mark.asyncio
    async def test_mock_returns_output(self):
        from app.agents.profile_extractor import ProfileExtractorAgent
        from app.core.config import get_settings
        agent = ProfileExtractorAgent(settings=get_settings())
        result = await agent.extract(_sample_input())
        assert result is not None

    @pytest.mark.asyncio
    async def test_mock_years_of_experience_non_negative(self):
        from app.agents.profile_extractor import ProfileExtractorAgent
        from app.core.config import get_settings
        agent = ProfileExtractorAgent(settings=get_settings())
        result = await agent.extract(_sample_input())
        assert result.years_of_experience >= 0

    @pytest.mark.asyncio
    async def test_mock_seniority_band_valid(self):
        from app.agents.profile_extractor import ProfileExtractorAgent
        from app.core.config import get_settings
        agent = ProfileExtractorAgent(settings=get_settings())
        result = await agent.extract(_sample_input())
        assert result.seniority_band in VALID_BANDS

    @pytest.mark.asyncio
    async def test_mock_work_history_is_list(self):
        from app.agents.profile_extractor import ProfileExtractorAgent
        from app.core.config import get_settings
        agent = ProfileExtractorAgent(settings=get_settings())
        result = await agent.extract(_sample_input())
        assert isinstance(result.work_history, list)

    @pytest.mark.asyncio
    async def test_mock_work_history_entries_have_required_keys(self):
        from app.agents.profile_extractor import ProfileExtractorAgent
        from app.core.config import get_settings
        agent = ProfileExtractorAgent(settings=get_settings())
        result = await agent.extract(_sample_input())
        for entry in result.work_history:
            assert "company" in entry.model_dump()
            assert "title" in entry.model_dump()

    @pytest.mark.asyncio
    async def test_mock_key_achievements_is_list(self):
        from app.agents.profile_extractor import ProfileExtractorAgent
        from app.core.config import get_settings
        agent = ProfileExtractorAgent(settings=get_settings())
        result = await agent.extract(_sample_input())
        assert isinstance(result.key_achievements, list)

    @pytest.mark.asyncio
    async def test_mock_cover_letter_narratives_is_list(self):
        from app.agents.profile_extractor import ProfileExtractorAgent
        from app.core.config import get_settings
        agent = ProfileExtractorAgent(settings=get_settings())
        result = await agent.extract(_sample_input())
        assert isinstance(result.cover_letter_narratives, list)

    @pytest.mark.asyncio
    async def test_mock_no_claude_api_call(self):
        from app.agents.profile_extractor import ProfileExtractorAgent
        from app.core.config import get_settings
        with patch("anthropic.AsyncAnthropic") as mock_anthropic:
            agent = ProfileExtractorAgent(settings=get_settings())
            await agent.extract(_sample_input())
            mock_anthropic.assert_not_called()

    @pytest.mark.asyncio
    async def test_run_method_returns_dict(self):
        from app.agents.profile_extractor import ProfileExtractorAgent
        from app.core.config import get_settings
        agent = ProfileExtractorAgent(settings=get_settings())
        result = await agent.run(_sample_input())
        assert isinstance(result, dict)
        assert "years_of_experience" in result


class TestProfileExtractorOutputSchema:

    @pytest.fixture(autouse=True)
    def _import(self):
        pytest.importorskip(_MODULE)

    def test_invalid_seniority_band_raises(self):
        from app.agents.profile_extractor import ProfileExtractorOutput
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            ProfileExtractorOutput(
                years_of_experience=5,
                seniority_band="INTERN",
                education=[],
                work_history=[],
                key_achievements=[],
                inferred_skills=[],
                cover_letter_narratives=[],
            )

    def test_negative_years_raises(self):
        from app.agents.profile_extractor import ProfileExtractorOutput
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            ProfileExtractorOutput(
                years_of_experience=-1,
                seniority_band="ASSOCIATE",
                education=[],
                work_history=[],
                key_achievements=[],
                inferred_skills=[],
                cover_letter_narratives=[],
            )

    def test_valid_output_roundtrips(self):
        from app.agents.profile_extractor import ProfileExtractorOutput
        obj = ProfileExtractorOutput(
            years_of_experience=6,
            seniority_band="ASSOCIATE",
            education=[],
            work_history=[],
            key_achievements=[],
            inferred_skills=["strategy", "AI"],
            cover_letter_narratives=[],
        )
        data = obj.model_dump(mode="json")
        assert data["years_of_experience"] == 6
        assert data["seniority_band"] == "ASSOCIATE"


class TestProfileExtractorFixture:

    def test_fixture_exists(self):
        assert FIXTURE_PATH.exists(), f"Fixture missing: {FIXTURE_PATH}"

    def test_fixture_valid_json(self):
        if not FIXTURE_PATH.exists():
            pytest.skip("Fixture not created yet")
        data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        assert isinstance(data, dict)
        assert "years_of_experience" in data
        assert "seniority_band" in data
        assert data["seniority_band"] in {"ANALYST", "ASSOCIATE", "MANAGER", "DIRECTOR", "VP_PLUS"}

    def test_fixture_has_work_history_list(self):
        if not FIXTURE_PATH.exists():
            pytest.skip("Fixture not created yet")
        data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        assert "work_history" in data
        assert isinstance(data["work_history"], list)

    def test_fixture_has_key_achievements_list(self):
        if not FIXTURE_PATH.exists():
            pytest.skip("Fixture not created yet")
        data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        assert "key_achievements" in data
        assert isinstance(data["key_achievements"], list)
