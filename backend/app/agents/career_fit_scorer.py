"""
Career Fit Scorer Agent — scores how well a user fits a predicted opportunity.

Input:  CareerFitScorerInput  (predicted opportunity + user profile)
Output: CareerFitScorerOutput (fit_score 0–100, fit_explanation, skill_gaps)

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

_AGENT_KEY = "career_fit_scorer"
_REGISTRY_CONFIG = AGENT_REGISTRY[_AGENT_KEY]


# ── Pydantic v2 schemas ────────────────────────────────────────────────────────

class OpportunitySummary(BaseModel):
    """Compact opportunity data needed for fit scoring."""

    predicted_role: str
    confidence: str
    why_fit: str
    approach_angle: str = ""


class UserProfileForScoring(BaseModel):
    """User profile fields used by the fit scorer."""

    current_role: str = ""
    target_roles: list[str] = Field(default_factory=list)
    industries: list[str] = Field(default_factory=list)
    aspirations_text: str = ""
    skills: list[str] = Field(default_factory=list)
    embedding_summary: str = ""
    # Phase 15 enrichments — optional, populated from career_profiles when available
    seniority_band: str | None = None
    work_history: list[dict] = Field(default_factory=list)
    key_achievements: list[dict] = Field(default_factory=list)


class CareerFitScorerInput(BaseModel):
    """Input payload for the Career Fit Scorer agent."""

    user_id: str
    opportunity_id: str
    opportunity: OpportunitySummary
    user_profile: UserProfileForScoring


class CareerFitScorerOutput(BaseModel):
    """Validated output from the Career Fit Scorer agent."""

    fit_score: float = Field(
        ge=0.0, le=100.0,
        description="0–100 score indicating how well the user fits the opportunity"
    )
    fit_explanation: str = Field(
        description="2-3 sentences explaining the score rationale"
    )
    skill_gaps: list[str] = Field(
        default_factory=list,
        description="0-3 specific skills or experiences the user is missing"
    )


# ── Agent implementation ────────────────────────────────────────────────────────

class CareerFitScorerAgent(BaseAgent):
    """
    Claude Sonnet-powered career fit scorer.

    Responsibilities:
      - Score how well a user's profile fits a predicted opportunity (0–100)
      - Identify specific, actionable skill gaps
      - Write to agent_runs audit log on every invocation

    Usage:
        agent = CareerFitScorerAgent(settings=get_settings())
        output = await agent.score(input_data)
    """

    agent_name: str = _AGENT_KEY

    def __init__(self, settings: Any) -> None:
        super().__init__(settings)
        self._model: str = _REGISTRY_CONFIG["model"]
        self._system_prompt: str = self._load_system_prompt()

    # ── Public interface ──────────────────────────────────────────────────────

    async def score(
        self, input_data: "CareerFitScorerInput | dict"
    ) -> CareerFitScorerOutput:
        """
        Score a user's career fit for a predicted opportunity.

        Args:
            input_data: CareerFitScorerInput or plain dict (will be coerced).

        Returns:
            Validated CareerFitScorerOutput.
        """
        if isinstance(input_data, dict):
            input_data = CareerFitScorerInput(**input_data)

        start_ms = int(time.monotonic() * 1000)

        if self._mock_mode:
            raw = self._load_mock_fixture()
            output = CareerFitScorerOutput(**raw)
            logger.info(
                "[mock] career_fit_scorer opportunity_id=%s → fit_score=%.1f",
                input_data.opportunity_id,
                output.fit_score,
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
            "career_fit_scorer opportunity_id=%s → fit_score=%.1f (%.0fms)",
            input_data.opportunity_id,
            output.fit_score,
            duration_ms,
        )
        return output

    async def run(self, input_data: dict) -> dict:
        """BaseAgent.run() — thin wrapper over score()."""
        output = await self.score(CareerFitScorerInput(**input_data))
        return output.model_dump(mode="json")

    # ── Private helpers ───────────────────────────────────────────────────────

    def _load_system_prompt(self) -> str:
        from pathlib import Path
        prompt_path = Path(__file__).parent / "prompts" / "career_fit_scorer_v1.txt"
        if not prompt_path.exists():
            raise FileNotFoundError(
                f"Career fit scorer prompt not found at {prompt_path}."
            )
        return prompt_path.read_text(encoding="utf-8")

    def _build_user_message(self, input_data: CareerFitScorerInput) -> str:
        opp_json = json.dumps(input_data.opportunity.model_dump(mode="json"), indent=2)
        profile_json = json.dumps(input_data.user_profile.model_dump(mode="json"), indent=2)
        parts = [
            f"opportunity:\n{opp_json}",
            f"user_profile:\n{profile_json}",
        ]
        # Phase 15 enrichments — include when available
        if input_data.user_profile.seniority_band:
            parts.append(f"seniority_band: {input_data.user_profile.seniority_band}")
        if input_data.user_profile.work_history:
            parts.append(
                f"work_history: {json.dumps(input_data.user_profile.work_history[:3])}"
            )
        if input_data.user_profile.key_achievements:
            parts.append(
                f"key_achievements: {json.dumps(input_data.user_profile.key_achievements[:3])}"
            )
        parts.append("Score the career fit and return JSON as instructed.")
        return "\n\n".join(parts)

    def _parse_response(self, raw_text: str) -> CareerFitScorerOutput:
        text = raw_text.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Career fit scorer returned non-JSON response: {raw_text[:200]}"
            ) from exc

        return CareerFitScorerOutput(**data)


# Alias for convenience
CareerFitScorer = CareerFitScorerAgent
