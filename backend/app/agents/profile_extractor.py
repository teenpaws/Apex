"""
Profile Extractor Agent — extracts structured career data from resume + cover letter text.

Input:  ProfileExtractorInput  (resume_text + cover_letters + existing_profile)
Output: ProfileExtractorOutput (years_of_experience, seniority_band, work_history, etc.)

Mock mode (MOCK_AGENTS=true): returns fixture data without any Claude API calls.
Live mode: calls Claude Sonnet via AGENT_REGISTRY. One-time cost ~$0.04/user.
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

_AGENT_KEY = "profile_extractor"
_REGISTRY_CONFIG = AGENT_REGISTRY[_AGENT_KEY]


# ── Pydantic v2 schemas ────────────────────────────────────────────────────────

class CoverLetterInput(BaseModel):
    text: str
    target_context: str


class ProfileExtractorInput(BaseModel):
    user_id: str
    resume_text: str
    cover_letters: list[CoverLetterInput] = Field(default_factory=list)
    existing_profile: dict[str, Any] = Field(default_factory=dict)


class EducationEntry(BaseModel):
    degree: str
    institution: str
    year: int | None = None
    field: str = ""


class WorkHistoryEntry(BaseModel):
    company: str
    title: str
    start_year: int | None = None
    end_year: int | None = None
    summary: str = ""


class KeyAchievement(BaseModel):
    achievement: str
    impact: str = ""
    context: str = ""


class CoverLetterNarrative(BaseModel):
    target_context: str
    core_narrative: str


SeniorityBand = Literal["ANALYST", "ASSOCIATE", "MANAGER", "DIRECTOR", "VP_PLUS"]


class ProfileExtractorOutput(BaseModel):
    years_of_experience: int = Field(ge=0)
    seniority_band: SeniorityBand
    education: list[EducationEntry] = Field(default_factory=list)
    work_history: list[WorkHistoryEntry] = Field(default_factory=list)
    key_achievements: list[KeyAchievement] = Field(default_factory=list)
    inferred_skills: list[str] = Field(default_factory=list)
    cover_letter_narratives: list[CoverLetterNarrative] = Field(default_factory=list)


# ── Agent ────────────────────────────────────────────────────────────────────

class ProfileExtractorAgent(BaseAgent):
    """
    Claude Sonnet-powered resume and cover letter profile extractor.

    Responsibilities:
      - Extract years_of_experience, seniority_band, work_history, key_achievements
      - Parse cover letter positioning narratives per target_context
      - Write to agent_runs audit log on every invocation

    Usage:
        agent = ProfileExtractorAgent(settings=get_settings())
        output = await agent.extract(input_data)
    """

    agent_name: str = _AGENT_KEY

    def __init__(self, settings: Any) -> None:
        super().__init__(settings)
        self._model: str = _REGISTRY_CONFIG["model"]
        self._system_prompt: str = self._load_system_prompt()

    # ── Public interface ──────────────────────────────────────────────────────

    async def extract(
        self, input_data: "ProfileExtractorInput | dict"
    ) -> ProfileExtractorOutput:
        """
        Extract structured career data from resume + cover letter text.

        Args:
            input_data: ProfileExtractorInput or plain dict (will be coerced).

        Returns:
            Validated ProfileExtractorOutput.
        """
        if isinstance(input_data, dict):
            input_data = ProfileExtractorInput(**input_data)

        start_ms = int(time.monotonic() * 1000)

        if self._mock_mode:
            raw = self._load_mock_fixture()
            output = ProfileExtractorOutput(**raw)
            logger.info(
                "[mock] profile_extractor user_id=%s → seniority=%s years=%d",
                input_data.user_id,
                output.seniority_band,
                output.years_of_experience,
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
            "profile_extractor user_id=%s → seniority=%s years=%d (%.0fms)",
            input_data.user_id,
            output.seniority_band,
            output.years_of_experience,
            duration_ms,
        )
        return output

    async def run(self, input_data: dict) -> dict:
        """BaseAgent.run() — thin wrapper over extract()."""
        output = await self.extract(ProfileExtractorInput(**input_data))
        return output.model_dump(mode="json")

    # ── Private helpers ───────────────────────────────────────────────────────

    def _load_system_prompt(self) -> str:
        from pathlib import Path
        prompt_path = Path(__file__).parent / "prompts" / "profile_extractor_v1.txt"
        if not prompt_path.exists():
            raise FileNotFoundError(
                f"Profile extractor prompt not found at {prompt_path}."
            )
        return prompt_path.read_text(encoding="utf-8")

    def _build_user_message(self, input_data: ProfileExtractorInput) -> str:
        parts = [f"RESUME TEXT:\n{input_data.resume_text}"]
        for cl in input_data.cover_letters:
            parts.append(
                f"COVER LETTER (target_context: {cl.target_context!r}):\n{cl.text}"
            )
        if input_data.existing_profile:
            parts.append(
                f"EXISTING PROFILE (for context only — do not overwrite explicit data with this):\n"
                f"{json.dumps(input_data.existing_profile, indent=2)}"
            )
        return "\n\n---\n\n".join(parts)

    def _parse_response(self, raw_text: str) -> ProfileExtractorOutput:
        """Parse Claude's JSON response into ProfileExtractorOutput."""
        text = raw_text.strip()
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            logger.error(
                "profile_extractor non-JSON response (first 200 chars): %s",
                text[:200],
            )
            raise ValueError(
                f"ProfileExtractor returned non-JSON: {text[:200]}"
            ) from exc
        return ProfileExtractorOutput(**data)


# Alias for convenience
ProfileExtractor = ProfileExtractorAgent
