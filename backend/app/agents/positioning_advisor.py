"""
Positioning Advisor Agent — generates a personalised positioning narrative using Claude Sonnet.

Input:  PositioningAdvisorInput  (user profile + opportunity + company signals)
Output: PositioningAdvisorOutput (positioning_narrative, key_talking_points, approach_angle)

Mock mode (MOCK_AGENTS=true): returns fixture data without any Claude API calls.
Live mode: calls Claude Sonnet via AGENT_REGISTRY for model name.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from pydantic import BaseModel, Field

from app.agents.base_agent import BaseAgent
from app.agents.registry import AGENT_REGISTRY

logger = logging.getLogger(__name__)

_AGENT_KEY = "positioning_advisor"
_REGISTRY_CONFIG = AGENT_REGISTRY[_AGENT_KEY]


# ── Pydantic v2 schemas ────────────────────────────────────────────────────────

class UserProfileForPositioning(BaseModel):
    """User profile fields used by the positioning advisor."""

    current_role: str = ""
    aspirations_text: str = ""
    skills: list[str] = Field(default_factory=list)
    career_history_summary: str = ""
    # Phase 15 enrichments — optional, populated from career_profiles when available
    cover_letter_narratives: list[dict] = Field(default_factory=list)
    key_achievements: list[dict] = Field(default_factory=list)


class OpportunityForPositioning(BaseModel):
    """Opportunity fields the positioning advisor needs."""

    predicted_role: str
    confidence: str
    why_fit: str
    ideal_contact_title: str = ""


class CompanySignalForPositioning(BaseModel):
    """A compact signal used as context for positioning."""

    signal_type: str
    title: str
    description: str
    signal_date: str


class PositioningAdvisorInput(BaseModel):
    """Input payload for the Positioning Advisor agent."""

    user_id: str
    opportunity_id: str
    user_profile: UserProfileForPositioning
    opportunity: OpportunityForPositioning
    company_signals: list[CompanySignalForPositioning] = Field(default_factory=list)


class PositioningAdvisorOutput(BaseModel):
    """Validated output from the Positioning Advisor agent."""

    positioning_narrative: str = Field(
        description="3–5 sentence first-person narrative ready to adapt into outreach"
    )
    key_talking_points: list[str] = Field(
        description="3–5 specific, concrete talking points to emphasise"
    )
    approach_angle: str = Field(
        description="1 sentence strategic angle for the outreach"
    )


# ── Agent implementation ────────────────────────────────────────────────────────

class PositioningAdvisorAgent(BaseAgent):
    """
    Claude Sonnet-powered positioning advisor.

    Responsibilities:
      - Generate a compelling, research-backed positioning narrative
      - Derive concrete talking points from the user's background + company signals
      - Write to agent_runs audit log on every invocation

    Usage:
        agent = PositioningAdvisorAgent(settings=get_settings())
        output = await agent.advise(input_data)
    """

    agent_name: str = _AGENT_KEY

    def __init__(self, settings: Any) -> None:
        super().__init__(settings)
        self._model: str = _REGISTRY_CONFIG["model"]
        self._system_prompt: str = self._load_system_prompt()

    # ── Public interface ──────────────────────────────────────────────────────

    async def advise(
        self, input_data: "PositioningAdvisorInput | dict"
    ) -> PositioningAdvisorOutput:
        """
        Generate a positioning narrative for the user → company outreach.

        Args:
            input_data: PositioningAdvisorInput or plain dict (will be coerced).

        Returns:
            Validated PositioningAdvisorOutput.
        """
        if isinstance(input_data, dict):
            input_data = PositioningAdvisorInput(**input_data)

        start_ms = int(time.monotonic() * 1000)

        if self._mock_mode:
            raw = self._load_mock_fixture()
            output = PositioningAdvisorOutput(**raw)
            logger.info(
                "[mock] positioning_advisor opportunity_id=%s → approach=%s",
                input_data.opportunity_id,
                output.approach_angle[:60],
            )
            await self.write_agent_run(
                user_id=input_data.user_id,
                model=self._model,
                input_data=input_data.model_dump(mode="json"),
                output_data=output.model_dump(mode="json"),
                duration_ms=int(time.monotonic() * 1000) - start_ms,
                status="SUCCESS",
            )
            return output

        # Live mode — call Claude Sonnet
        user_message = self._build_user_message(input_data)
        raw_text = await self._call_claude(
            prompt=user_message,
            model=self._model,
            system=self._system_prompt,
        )
        output = self._parse_response(raw_text)

        duration_ms = int(time.monotonic() * 1000) - start_ms
        await self.write_agent_run(
            user_id=input_data.user_id,
            model=self._model,
            input_data=input_data.model_dump(mode="json"),
            output_data=output.model_dump(mode="json"),
            duration_ms=duration_ms,
            status="SUCCESS",
        )

        logger.info(
            "positioning_advisor opportunity_id=%s (%.0fms)",
            input_data.opportunity_id,
            duration_ms,
        )
        return output

    async def run(self, input_data: dict) -> dict:
        """BaseAgent.run() — thin wrapper over advise()."""
        output = await self.advise(PositioningAdvisorInput(**input_data))
        return output.model_dump(mode="json")

    # ── Private helpers ───────────────────────────────────────────────────────

    def _load_system_prompt(self) -> str:
        from pathlib import Path
        prompt_path = Path(__file__).parent / "prompts" / "positioning_advisor_v1.txt"
        if not prompt_path.exists():
            raise FileNotFoundError(
                f"Positioning advisor prompt not found at {prompt_path}."
            )
        return prompt_path.read_text(encoding="utf-8")

    def _select_cover_letter_narrative(
        self,
        narratives: list[dict],
        opportunity: "OpportunityForPositioning",
    ) -> dict | None:
        """Return the best-matching cover letter narrative for the opportunity context.

        Matching logic: find the narrative whose ``target_context`` appears as a
        substring (case-insensitive) in the opportunity's ``why_fit`` text.  Falls
        back to the first narrative when no match is found.
        """
        if not narratives:
            return None
        why_fit_lower = (opportunity.why_fit or "").lower()
        for narrative in narratives:
            target_ctx = (narrative.get("target_context") or "").lower()
            if target_ctx and target_ctx in why_fit_lower:
                return narrative
        return narratives[0]

    def _build_user_message(self, input_data: PositioningAdvisorInput) -> str:
        profile_json = json.dumps(input_data.user_profile.model_dump(mode="json"), indent=2)
        opp_json = json.dumps(input_data.opportunity.model_dump(mode="json"), indent=2)
        signals_json = json.dumps(
            [s.model_dump(mode="json") for s in input_data.company_signals],
            indent=2,
        )
        parts = [
            f"user_profile:\n{profile_json}",
            f"opportunity:\n{opp_json}",
            f"company_signals:\n{signals_json}",
        ]
        # Phase 15 enrichments — include when available
        best_narrative = self._select_cover_letter_narrative(
            input_data.user_profile.cover_letter_narratives,
            input_data.opportunity,
        )
        if best_narrative:
            parts.append(
                f"cover_letter_narrative: {json.dumps(best_narrative)}"
            )
        if input_data.user_profile.key_achievements:
            parts.append(
                f"key_achievements: {json.dumps(input_data.user_profile.key_achievements[:3])}"
            )
        parts.append("Generate the positioning narrative and return JSON as instructed.")
        return "\n\n".join(parts)

    def _parse_response(self, raw_text: str) -> PositioningAdvisorOutput:
        text = raw_text.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Positioning advisor returned non-JSON response: {raw_text[:200]}"
            ) from exc

        return PositioningAdvisorOutput(**data)


# Alias for convenience
PositioningAdvisor = PositioningAdvisorAgent
