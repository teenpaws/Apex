"""
Action Generator Agent — converts opportunities into prioritised action items using Claude Haiku.

Input:  ActionGeneratorInput  (opportunity + fit_score + contacts)
Output: ActionGeneratorOutput (list of ActionItem objects)

Mock mode (MOCK_AGENTS=true): returns fixture data without any Claude API calls.
Live mode: calls Claude Haiku via AGENT_REGISTRY for model name.
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

_AGENT_KEY = "action_generator"
_REGISTRY_CONFIG = AGENT_REGISTRY[_AGENT_KEY]


# ── Pydantic v2 schemas ────────────────────────────────────────────────────────

class OpportunityForActions(BaseModel):
    """Opportunity fields the action generator needs."""

    predicted_role: str
    confidence: str
    timeline_weeks: int
    why_fit: str
    ideal_contact_title: str = ""
    company_name: str = ""


class ContactSummary(BaseModel):
    """A contact available at the target company."""

    name: str = ""
    title: str = ""
    linkedin_url: str = ""


class ActionGeneratorInput(BaseModel):
    """Input payload for the Action Generator agent."""

    user_id: str
    opportunity_id: str
    opportunity: OpportunityForActions
    fit_score: float = Field(ge=0.0, le=100.0)
    contacts: list[ContactSummary] = Field(default_factory=list)


class ActionItem(BaseModel):
    """A single prioritised action item."""

    title: str = Field(
        description="Short action title (under 60 chars), imperative verb"
    )
    type: Literal["OUTREACH", "RESEARCH", "FOLLOW_UP", "CALL"] = Field(
        description="Category of action"
    )
    priority: Literal["HIGH", "MEDIUM", "LOW"] = Field(
        description="Execution priority"
    )
    due_date: str = Field(
        description="Relative due date string, e.g. '+3d'"
    )


class ActionGeneratorOutput(BaseModel):
    """Validated output from the Action Generator agent."""

    actions: list[ActionItem] = Field(
        description="2–5 prioritised action items for this opportunity"
    )


# ── Agent implementation ────────────────────────────────────────────────────────

class ActionGeneratorAgent(BaseAgent):
    """
    Claude Haiku-powered action generator.

    Responsibilities:
      - Convert a predicted opportunity + fit score into 2–5 action items
      - Apply priority rules: urgency × confidence × fit_score
      - Always include at least one RESEARCH action before OUTREACH
      - Write to agent_runs audit log on every invocation

    Usage:
        agent = ActionGeneratorAgent(settings=get_settings())
        output = await agent.generate(input_data)
    """

    agent_name: str = _AGENT_KEY

    def __init__(self, settings: Any) -> None:
        super().__init__(settings)
        self._model: str = _REGISTRY_CONFIG["model"]
        self._system_prompt: str = self._load_system_prompt()

    # ── Public interface ──────────────────────────────────────────────────────

    async def generate(
        self, input_data: "ActionGeneratorInput | dict"
    ) -> ActionGeneratorOutput:
        """
        Generate prioritised action items for an opportunity.

        Args:
            input_data: ActionGeneratorInput or plain dict (will be coerced).

        Returns:
            Validated ActionGeneratorOutput.
        """
        if isinstance(input_data, dict):
            input_data = ActionGeneratorInput(**input_data)

        start_ms = int(time.monotonic() * 1000)

        if self._mock_mode:
            raw = self._load_mock_fixture()
            output = ActionGeneratorOutput(**raw)
            logger.info(
                "[mock] action_generator opportunity_id=%s → %d actions",
                input_data.opportunity_id,
                len(output.actions),
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
            user_id=input_data.user_id,
            model=self._model,
            input_data=input_data.model_dump(mode="json"),
            output_data=output.model_dump(mode="json"),
            duration_ms=duration_ms,
            status="SUCCESS",
        )

        logger.info(
            "action_generator opportunity_id=%s → %d actions (%.0fms)",
            input_data.opportunity_id,
            len(output.actions),
            duration_ms,
        )
        return output

    async def run(self, input_data: dict) -> dict:
        """BaseAgent.run() — thin wrapper over generate()."""
        output = await self.generate(ActionGeneratorInput(**input_data))
        return output.model_dump(mode="json")

    # ── Private helpers ───────────────────────────────────────────────────────

    def _load_system_prompt(self) -> str:
        from pathlib import Path
        prompt_path = Path(__file__).parent / "prompts" / "action_generator_v2.txt"
        if not prompt_path.exists():
            raise FileNotFoundError(
                f"Action generator prompt not found at {prompt_path}."
            )
        return prompt_path.read_text(encoding="utf-8")

    def _build_user_message(self, input_data: ActionGeneratorInput) -> str:
        opp_json = json.dumps(input_data.opportunity.model_dump(mode="json"), indent=2)
        contacts_json = json.dumps(
            [c.model_dump(mode="json") for c in input_data.contacts],
            indent=2,
        )
        return (
            f"opportunity:\n{opp_json}\n\n"
            f"fit_score: {input_data.fit_score}\n\n"
            f"contacts:\n{contacts_json}\n\n"
            f"user_id: {input_data.user_id}\n\n"
            "Generate action items and return JSON as instructed."
        )

    def _parse_response(self, raw_text: str) -> ActionGeneratorOutput:
        text = raw_text.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Action generator returned non-JSON response: {raw_text[:200]}"
            ) from exc

        # Normalise priority and type values to uppercase
        for action in data.get("actions", []):
            if "priority" in action:
                action["priority"] = action["priority"].upper()
            if "type" in action:
                action["type"] = action["type"].upper()

        return ActionGeneratorOutput(**data)


# Alias for convenience
ActionGenerator = ActionGeneratorAgent
