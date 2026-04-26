"""
Email Drafter Agent — generates 3-tone email variants using Claude Sonnet.

Input:  EmailDrafterInput  (action + contact + opportunity + user_profile + positioning)
Output: EmailDrafterOutput (list of 3 EmailVariant objects)

Mock mode (MOCK_AGENTS=true): returns fixture data without Claude API calls.
Live mode: calls Claude Sonnet via AGENT_REGISTRY for model name.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.agents.base_agent import BaseAgent
from app.agents.registry import AGENT_REGISTRY

logger = logging.getLogger(__name__)

_AGENT_KEY = "email_drafter"
_REGISTRY_CONFIG = AGENT_REGISTRY[_AGENT_KEY]


# ── Pydantic v2 schemas ────────────────────────────────────────────────────────

class ActionForEmail(BaseModel):
    title: str
    type: str
    description: str = ""


class ContactForEmail(BaseModel):
    name: str
    title: str
    company_name: str


class OpportunityForEmail(BaseModel):
    predicted_role: str
    why_fit: str
    approach_angle: str = ""


class UserProfileForEmail(BaseModel):
    full_name: str
    current_role: str
    aspirations_text: str = ""
    key_skills: list[str] = Field(default_factory=list)
    # Phase 15 enrichments — optional, populated from career_profiles when available
    key_achievements: list[dict] = Field(default_factory=list)
    cover_letter_narratives: list[dict] = Field(default_factory=list)


class PositioningContext(BaseModel):
    positioning_narrative: str = ""
    key_talking_points: list[str] = Field(default_factory=list)
    approach_angle: str = ""


class EmailDrafterInput(BaseModel):
    user_id: str
    action_id: str
    action: ActionForEmail
    contact: ContactForEmail
    opportunity: OpportunityForEmail
    user_profile: UserProfileForEmail
    positioning: PositioningContext = Field(default_factory=PositioningContext)


class EmailVariant(BaseModel):
    tone: Literal["Professional", "Warm", "Direct"]
    subject: str = Field(description="Email subject line, under 60 chars")
    body: str = Field(description="Full email body, 150-250 words")
    key_points_used: list[str] = Field(
        description="2-3 specific points from positioning woven in"
    )


class EmailDrafterOutput(BaseModel):
    variants: list[EmailVariant] = Field(
        description="Exactly 3 email variants: Professional, Warm, Direct"
    )


# ── Agent implementation ────────────────────────────────────────────────────────

class EmailDrafterAgent(BaseAgent):
    """
    Claude Sonnet-powered email drafter.

    Generates 3 tone-differentiated email variants (Professional, Warm, Direct)
    for a given outreach action + contact + opportunity.

    Usage:
        agent = EmailDrafterAgent(settings=get_settings())
        output = await agent.draft(input_data)
    """

    agent_name: str = _AGENT_KEY

    def __init__(self, settings: Any) -> None:
        super().__init__(settings)
        self._model: str = _REGISTRY_CONFIG["model"]
        self._system_prompt: str = self._load_system_prompt()

    async def draft(
        self, input_data: "EmailDrafterInput | dict"
    ) -> EmailDrafterOutput:
        """
        Generate 3 email variants for the given action + contact + opportunity.

        Args:
            input_data: EmailDrafterInput or plain dict (will be coerced).

        Returns:
            Validated EmailDrafterOutput with exactly 3 variants.
        """
        if isinstance(input_data, dict):
            input_data = EmailDrafterInput(**input_data)

        start_ms = int(time.monotonic() * 1000)

        if self._mock_mode:
            raw = self._load_mock_fixture()
            output = EmailDrafterOutput(**raw)
            logger.info(
                "[mock] email_drafter action_id=%s contact=%s -> %d variants",
                input_data.action_id,
                input_data.contact.name,
                len(output.variants),
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
            "email_drafter action_id=%s contact=%s -> %d variants (%.0fms)",
            input_data.action_id,
            input_data.contact.name,
            len(output.variants),
            duration_ms,
        )
        return output

    async def run(self, input_data: dict) -> dict:
        """BaseAgent.run() — thin wrapper over draft()."""
        output = await self.draft(EmailDrafterInput(**input_data))
        return output.model_dump(mode="json")

    def _load_system_prompt(self) -> str:
        prompt_path = Path(__file__).parent / "prompts" / "email_drafter_v2.txt"
        if not prompt_path.exists():
            raise FileNotFoundError(
                f"Email drafter prompt not found at {prompt_path}."
            )
        return prompt_path.read_text(encoding="utf-8")

    def _select_cover_letter_narrative(
        self,
        narratives: list[dict],
        opportunity: OpportunityForEmail,
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

    def _build_user_message(self, input_data: EmailDrafterInput) -> str:
        payload: dict = {
            "action": input_data.action.model_dump(mode="json"),
            "contact": input_data.contact.model_dump(mode="json"),
            "opportunity": input_data.opportunity.model_dump(mode="json"),
            "user_profile": input_data.user_profile.model_dump(mode="json"),
            "positioning": input_data.positioning.model_dump(mode="json"),
        }
        # Phase 15 enrichments — append when available
        best_narrative = self._select_cover_letter_narrative(
            input_data.user_profile.cover_letter_narratives,
            input_data.opportunity,
        )
        if best_narrative:
            payload["cover_letter_narrative"] = best_narrative
        if input_data.user_profile.key_achievements:
            payload["key_achievements"] = input_data.user_profile.key_achievements[:2]
        return json.dumps(payload, indent=2)

    def _parse_response(self, raw_text: str) -> EmailDrafterOutput:
        text = raw_text.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Email drafter returned non-JSON response: {raw_text[:200]}"
            ) from exc

        return EmailDrafterOutput(**data)


# Alias for convenience
EmailDrafter = EmailDrafterAgent
