"""
Opportunity Predictor Agent — predicts hiring opportunities using Claude Sonnet.

Input:  OpportunityPredictorInput  (company signals + user career profile)
Output: OpportunityPredictorOutput (predicted role, confidence, timeline, fit notes,
                                     ideal contact title)

Per CLAUDE.md: contact_identifier was merged into this agent. The predictor outputs
both the predicted role AND the ideal contact title/search query in a single call.

Mock mode (MOCK_AGENTS=true): returns fixture data without any Claude API calls.
Live mode: calls Claude Sonnet via AGENT_REGISTRY for model name.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.agents.base_agent import BaseAgent
from app.agents.registry import AGENT_REGISTRY

logger = logging.getLogger(__name__)

_AGENT_KEY = "opportunity_predictor"
_REGISTRY_CONFIG = AGENT_REGISTRY[_AGENT_KEY]


# ── Pydantic v2 schemas ────────────────────────────────────────────────────────

class SignalSummary(BaseModel):
    """A compact signal summary passed to the predictor."""

    signal_id: str
    signal_type: str
    title: str
    description: str
    signal_date: str
    relevance_score: float = Field(ge=0.0, le=1.0)


class UserProfileSummary(BaseModel):
    """Career profile fields the predictor needs."""

    current_role: str = ""
    target_roles: list[str] = Field(default_factory=list)
    industries: list[str] = Field(default_factory=list)
    aspirations_text: str = ""
    skills: list[str] = Field(default_factory=list)


class OpportunityPredictorInput(BaseModel):
    """Input payload for the Opportunity Predictor agent."""

    user_id: str
    company_id: str
    company_name: str
    company_signals: list[SignalSummary] = Field(default_factory=list)
    user_profile: UserProfileSummary


class OpportunityPredictorOutput(BaseModel):
    """Validated output from the Opportunity Predictor agent."""

    predicted_role: str = Field(
        description="Specific job title the company is most likely to hire for"
    )
    confidence: Literal["HIGH", "MEDIUM", "SPECULATIVE"] = Field(
        description="Confidence level based on signal strength"
    )
    timeline_weeks: int = Field(
        ge=1, le=52,
        description="Estimated weeks until the role opens"
    )
    why_fit: str = Field(
        description="2-3 sentences explaining why the user's background fits"
    )
    positioning_notes: str = Field(
        description="1-2 sentences on what angle the user should lead with"
    )
    ideal_contact_title: str = Field(
        description="Job title of the likely hiring manager or champion"
    )


# ── Agent implementation ────────────────────────────────────────────────────────

class OpportunityPredictorAgent(BaseAgent):
    """
    Claude Sonnet-powered opportunity predictor.

    Responsibilities:
      - Analyze company signals to predict likely hiring needs
      - Score opportunity confidence (HIGH / MEDIUM / SPECULATIVE)
      - Identify ideal contact title for outreach (merged from contact_identifier)
      - Write to agent_runs audit log on every invocation

    Usage:
        agent = OpportunityPredictorAgent(settings=get_settings())
        output = await agent.predict(input_data)
    """

    agent_name: str = _AGENT_KEY

    def __init__(self, settings: Any) -> None:
        super().__init__(settings)
        self._model: str = _REGISTRY_CONFIG["model"]
        self._system_prompt: str = self._load_system_prompt()

    # ── Public interface ──────────────────────────────────────────────────────

    async def predict(
        self, input_data: "OpportunityPredictorInput | dict"
    ) -> OpportunityPredictorOutput:
        """
        Predict a hiring opportunity from company signals and user profile.

        Args:
            input_data: OpportunityPredictorInput or plain dict (will be coerced).

        Returns:
            Validated OpportunityPredictorOutput.
        """
        if isinstance(input_data, dict):
            input_data = OpportunityPredictorInput(**input_data)

        start_ms = int(time.monotonic() * 1000)

        if self._mock_mode:
            raw = self._load_mock_fixture()
            output = OpportunityPredictorOutput(**raw)
            logger.info(
                "[mock] opportunity_predictor company=%s → role=%s confidence=%s",
                input_data.company_name,
                output.predicted_role,
                output.confidence,
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
            "opportunity_predictor company=%s → role=%s confidence=%s (%.0fms)",
            input_data.company_name,
            output.predicted_role,
            output.confidence,
            duration_ms,
        )
        return output

    async def run(self, input_data: dict) -> dict:
        """BaseAgent.run() — thin wrapper over predict()."""
        output = await self.predict(OpportunityPredictorInput(**input_data))
        return output.model_dump(mode="json")

    # ── Private helpers ───────────────────────────────────────────────────────

    def _load_system_prompt(self) -> str:
        from pathlib import Path
        prompt_path = Path(__file__).parent / "prompts" / "opportunity_predictor_v1.txt"
        if not prompt_path.exists():
            raise FileNotFoundError(
                f"Opportunity predictor prompt not found at {prompt_path}."
            )
        return prompt_path.read_text(encoding="utf-8")

    def _build_user_message(self, input_data: OpportunityPredictorInput) -> str:
        signals_json = json.dumps(
            [s.model_dump(mode="json") for s in input_data.company_signals],
            indent=2,
        )
        profile_json = json.dumps(input_data.user_profile.model_dump(mode="json"), indent=2)
        return (
            f"Company: {input_data.company_name}\n\n"
            f"company_signals:\n{signals_json}\n\n"
            f"user_profile:\n{profile_json}\n\n"
            "Predict the hiring opportunity and return JSON as instructed."
        )

    def _parse_response(self, raw_text: str) -> OpportunityPredictorOutput:
        text = raw_text.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Opportunity predictor returned non-JSON response: {raw_text[:200]}"
            ) from exc

        if "confidence" in data:
            data["confidence"] = data["confidence"].upper()

        return OpportunityPredictorOutput(**data)


# Alias for convenience
OpportunityPredictor = OpportunityPredictorAgent
