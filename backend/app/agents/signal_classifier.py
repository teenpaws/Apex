"""
Signal Classifier Agent — classifies raw market signals using Claude Haiku.

Input:  SignalClassifierInput  (signal metadata + user career context)
Output: SignalClassifierOutput (signal_type, relevance_score, extracted entities)

Mock mode (MOCK_AGENTS=true): returns fixture data without any Claude API calls.
Live mode: calls Claude Haiku via AGENT_REGISTRY for model name.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from app.agents.base_agent import BaseAgent
from app.agents.registry import AGENT_REGISTRY

logger = logging.getLogger(__name__)

# Resolve prompt file path relative to this module's agents package
_AGENTS_DIR = Path(__file__).parent
_PROMPTS_DIR = _AGENTS_DIR / "prompts"

_AGENT_KEY = "signal_classifier"
_REGISTRY_CONFIG = AGENT_REGISTRY[_AGENT_KEY]


# ── Pydantic v2 schemas ────────────────────────────────────────────────────────

class SignalClassifierInput(BaseModel):
    """Input payload for the Signal Classifier agent."""

    signal_id: str
    title: str
    description: str
    source: str
    signal_date: datetime
    company_name: str
    user_target_industries: list[str] = Field(default_factory=list)
    user_target_roles: list[str] = Field(default_factory=list)


class SignalClassifierOutput(BaseModel):
    """Validated output from the Signal Classifier agent."""

    signal_type: str = Field(
        description="One of the SignalType enum values (e.g. FUNDING, EXEC_HIRE)"
    )
    relevance_score: float = Field(
        ge=0.0, le=1.0,
        description="0.0–1.0 score indicating relevance to user's career goals"
    )
    companies_mentioned: list[str] = Field(default_factory=list)
    people_mentioned: list[str] = Field(default_factory=list)
    key_facts: list[str] = Field(
        default_factory=list,
        description="3–5 concrete facts extracted from the signal"
    )
    reasoning: str = Field(
        description="Brief explanation of the classification and relevance score"
    )


# ── Agent implementation ────────────────────────────────────────────────────────

class SignalClassifierAgent(BaseAgent):
    """
    Claude Haiku-powered signal classifier.

    Responsibilities:
      - Classify a raw signal into one of 8 SignalType categories
      - Score relevance to user's target industries and roles (0–1)
      - Extract companies, people, and key facts
      - Write to agent_runs audit log on every invocation

    Usage:
        agent = SignalClassifierAgent(settings=get_settings())
        output = await agent.classify(input_data)
    """

    agent_name: str = _AGENT_KEY

    def __init__(self, settings: Any) -> None:
        super().__init__(settings)
        self._model: str = _REGISTRY_CONFIG["model"]
        self._system_prompt: str = self._load_system_prompt()

    # ── Public interface ──────────────────────────────────────────────────────

    async def classify(
        self, input_data: "SignalClassifierInput | dict"
    ) -> SignalClassifierOutput:
        """
        Classify a signal and return structured output.

        Args:
            input_data: SignalClassifierInput or a plain dict (will be coerced).

        Returns:
            Validated SignalClassifierOutput.
        """
        if isinstance(input_data, dict):
            input_data = SignalClassifierInput(
                signal_id=input_data.get("signal_id", "unknown"),
                **{k: v for k, v in input_data.items() if k != "signal_id"},
            )
        start_ms = int(time.monotonic() * 1000)

        if self._mock_mode:
            raw = self._load_mock_fixture()
            output = SignalClassifierOutput(**raw)
            logger.info(
                "[mock] signal_classifier signal_id=%s → type=%s relevance=%.2f",
                input_data.signal_id,
                output.signal_type,
                output.relevance_score,
            )
            await self.write_agent_run(
                user_id="mock-user",
                model=self._model,
                input_data=input_data.model_dump(mode="json"),
                output_data=output.model_dump(mode="json"),
                duration_ms=int(time.monotonic() * 1000) - start_ms,
                status="SUCCESS",
            )
            return output

        # Live mode — call Claude Haiku
        user_message = self._build_user_message(input_data)
        raw_text = await self._call_claude(
            prompt=user_message,
            model=self._model,
            system=self._system_prompt,
        )
        output = self._parse_response(raw_text)

        duration_ms = int(time.monotonic() * 1000) - start_ms
        await self.write_agent_run(
            user_id=input_data.signal_id,  # use signal_id as proxy when user_id unavailable
            model=self._model,
            input_data=input_data.model_dump(mode="json"),
            output_data=output.model_dump(mode="json"),
            duration_ms=duration_ms,
            status="SUCCESS",
        )

        logger.info(
            "signal_classifier signal_id=%s → type=%s relevance=%.2f (%.0fms)",
            input_data.signal_id,
            output.signal_type,
            output.relevance_score,
            duration_ms,
        )
        return output

    async def run(self, input_data: dict) -> dict:
        """
        BaseAgent.run() implementation — thin wrapper over classify().

        Accepts a raw dict and returns a raw dict so the base class contract
        is satisfied. Prefer calling classify() directly for type safety.
        """
        validated_input = SignalClassifierInput(**input_data)
        output = await self.classify(validated_input)
        return output.model_dump(mode="json")

    # ── Private helpers ───────────────────────────────────────────────────────

    def _load_system_prompt(self) -> str:
        """Load the system prompt from the prompts directory."""
        prompt_path = _PROMPTS_DIR / "signal_classifier_v1.txt"
        if not prompt_path.exists():
            raise FileNotFoundError(
                f"Signal classifier prompt not found at {prompt_path}. "
                "Ensure backend/app/agents/prompts/signal_classifier_v1.txt exists."
            )
        return prompt_path.read_text(encoding="utf-8")

    def _build_user_message(self, input_data: SignalClassifierInput) -> str:
        """Format the user turn message from input data."""
        return (
            f"Signal ID: {input_data.signal_id}\n"
            f"Company: {input_data.company_name}\n"
            f"Source: {input_data.source}\n"
            f"Date: {input_data.signal_date.isoformat()}\n"
            f"Title: {input_data.title}\n"
            f"Description: {input_data.description}\n\n"
            f"User's target industries: {', '.join(input_data.user_target_industries) or 'Not specified'}\n"
            f"User's target roles: {', '.join(input_data.user_target_roles) or 'Not specified'}\n\n"
            "Classify this signal and return JSON as instructed."
        )

    def _parse_response(self, raw_text: str) -> SignalClassifierOutput:
        """
        Parse Claude's JSON response into a validated SignalClassifierOutput.

        Raises:
            ValueError: If the response is not valid JSON or fails schema validation.
        """
        # Strip any accidental markdown fences Claude may add
        text = raw_text.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            # Drop first and last fence lines
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Signal classifier returned non-JSON response: {raw_text[:200]}"
            ) from exc

        # Normalise signal_type to uppercase for enum safety
        if "signal_type" in data:
            data["signal_type"] = data["signal_type"].upper()

        return SignalClassifierOutput(**data)

# Alias for backward-compatible imports
SignalClassifier = SignalClassifierAgent
