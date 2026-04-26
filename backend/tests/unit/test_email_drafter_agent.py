"""
Unit tests for EmailDrafterAgent.

Tests cover:
  - Mock mode returns 3 variants from fixture (no Claude API calls)
  - Output validated by Pydantic (EmailDrafterOutput schema)
  - Each variant has tone, subject, body, key_points_used fields
  - Tones are exactly: Professional, Warm, Direct
  - Live mode calls _call_claude (verified via mock)
  - write_agent_run is called on each invocation
  - Invalid Claude output raises ValueError (parse error path)
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

_MODULE = "app.agents.email_drafter"

FIXTURE_PATH = (
    Path(__file__).parent.parent.parent
    / "app" / "agents" / "fixtures" / "email_drafter_mock_output.json"
)


def _valid_input() -> dict:
    return {
        "user_id": "user-001",
        "action_id": "action-001",
        "action": {
            "title": "Reach out to Sarah Chen at Stripe",
            "type": "OUTREACH",
            "description": "Introduce yourself and mention EMEA expansion interest",
        },
        "contact": {
            "name": "Sarah Chen",
            "title": "VP Strategy",
            "company_name": "Stripe",
        },
        "opportunity": {
            "predicted_role": "Head of EMEA Strategy",
            "why_fit": "MBA in Finance + M&A integration background aligns with Stripe's EMEA expansion.",
            "approach_angle": "Lead with EMEA payments market knowledge.",
        },
        "user_profile": {
            "full_name": "Alex Dubois",
            "current_role": "M&A Associate, BNP Paribas",
            "aspirations_text": "Move into fintech strategy at a high-growth startup.",
            "key_skills": ["M&A", "Financial modelling", "Payments"],
        },
        "positioning": {
            "positioning_narrative": "Unique blend of banking rigour and fintech ambition.",
            "key_talking_points": ["EMEA expansion", "M&A integration", "Payments experience"],
            "approach_angle": "Reference Stripe's Series H as the trigger.",
        },
    }


class TestEmailDrafterMockMode:

    @pytest.fixture(autouse=True)
    def _import(self):
        pytest.importorskip(_MODULE)

    @pytest.mark.asyncio
    async def test_mock_returns_three_variants(self):
        from app.agents.email_drafter import EmailDrafterAgent
        from app.core.config import get_settings
        agent = EmailDrafterAgent(settings=get_settings())
        output = await agent.draft(_valid_input())
        assert len(output.variants) == 3

    @pytest.mark.asyncio
    async def test_mock_variant_has_required_fields(self):
        from app.agents.email_drafter import EmailDrafterAgent
        from app.core.config import get_settings
        agent = EmailDrafterAgent(settings=get_settings())
        output = await agent.draft(_valid_input())
        for variant in output.variants:
            assert variant.tone in ("Professional", "Warm", "Direct")
            assert len(variant.subject) > 0
            assert len(variant.body) > 0
            assert isinstance(variant.key_points_used, list)
            assert len(variant.key_points_used) >= 1

    @pytest.mark.asyncio
    async def test_mock_does_not_call_claude_api(self):
        from app.agents.email_drafter import EmailDrafterAgent
        from app.core.config import get_settings
        agent = EmailDrafterAgent(settings=get_settings())
        with patch.object(agent, "_call_claude", new_callable=AsyncMock) as mock_claude:
            await agent.draft(_valid_input())
        mock_claude.assert_not_called()

    @pytest.mark.asyncio
    async def test_mock_calls_write_agent_run(self):
        from app.agents.email_drafter import EmailDrafterAgent
        from app.core.config import get_settings
        agent = EmailDrafterAgent(settings=get_settings())
        with patch.object(agent, "write_agent_run", new_callable=AsyncMock) as mock_run:
            await agent.draft(_valid_input())
        mock_run.assert_called_once()

    def test_fixture_file_exists(self):
        assert FIXTURE_PATH.exists(), f"Fixture missing: {FIXTURE_PATH}"

    def test_fixture_has_three_variants(self):
        import json
        data = json.loads(FIXTURE_PATH.read_text())
        assert "variants" in data
        assert len(data["variants"]) == 3


class TestEmailDrafterLiveMode:

    @pytest.fixture(autouse=True)
    def _import(self):
        pytest.importorskip(_MODULE)

    @pytest.mark.asyncio
    async def test_live_mode_calls_claude(self):
        from app.agents.email_drafter import EmailDrafterAgent
        from app.core.config import get_settings
        import json

        mock_response = json.dumps({
            "variants": [
                {
                    "tone": "Professional",
                    "subject": "Strategy at Stripe",
                    "body": "Hi Sarah, I noticed your Series H and believe my background in EMEA payments could add value to your expansion. Would you be open to a 20-minute call? Best, Alex",
                    "key_points_used": ["Series H", "EMEA"],
                },
                {
                    "tone": "Warm",
                    "subject": "Congrats on the Series H",
                    "body": "Hi Sarah, just saw the Series H news — exciting milestone for Stripe. My background in EMEA payments M&A made me reach out. Would love to hear your perspective on the expansion plans.",
                    "key_points_used": ["Series H"],
                },
                {
                    "tone": "Direct",
                    "subject": "EMEA strategy hire?",
                    "body": "Sarah, Stripe's Series H signals rapid EMEA expansion. My M&A background at BNP Paribas is directly relevant. Happy to send a one-pager if helpful.",
                    "key_points_used": ["Funding"],
                },
            ]
        })

        settings = get_settings()
        agent = EmailDrafterAgent(settings=settings)
        agent._mock_mode = False

        with patch.object(agent, "_call_claude", new_callable=AsyncMock, return_value=mock_response):
            with patch.object(agent, "write_agent_run", new_callable=AsyncMock):
                output = await agent.draft(_valid_input())

        assert len(output.variants) == 3
        assert output.variants[0].tone == "Professional"

    @pytest.mark.asyncio
    async def test_live_mode_raises_on_invalid_json(self):
        from app.agents.email_drafter import EmailDrafterAgent
        from app.core.config import get_settings

        settings = get_settings()
        agent = EmailDrafterAgent(settings=settings)
        agent._mock_mode = False

        with patch.object(agent, "_call_claude", new_callable=AsyncMock, return_value="not json at all"):
            with patch.object(agent, "write_agent_run", new_callable=AsyncMock):
                with pytest.raises(ValueError, match="non-JSON"):
                    await agent.draft(_valid_input())
