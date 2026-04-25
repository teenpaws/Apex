"""
BaseAgent — abstract base class for all Apex AI agents.

All concrete agents (SignalClassifier, OpportunityPredictor, etc.) extend this class.
Provides:
  - Mock mode detection (MOCK_AGENTS=true → load from fixtures, no API calls)
  - Retry logic (3x with exponential backoff) for Claude API calls
  - agent_runs audit log stub (to be wired to Supabase in Phase 2)
  - Prompt caching on system prompts (saves ~80% cost on repeated calls)
"""

import asyncio
import hashlib
import json
import logging
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Directory where fixture JSON files live (relative to this file's package root)
_FIXTURES_DIR = Path(__file__).parent / "fixtures"

# Max retries and backoff settings for Claude API calls
_MAX_RETRIES = 3
_BACKOFF_BASE_SECONDS = 1.0


class BaseAgent(ABC):
    """
    Abstract base class for all Apex Claude-powered agents.

    Subclasses must implement:
        async def run(self, input_data: dict) -> dict
    """

    # Subclasses set this to their registry key, e.g. "signal_classifier"
    agent_name: str = ""
    # Class-level default; overridden per-instance in __init__ from settings.
    # Declared here so unittest.mock.patch can target it at class level.
    _mock_mode: bool = True

    def __init__(self, settings: Any) -> None:
        """
        Args:
            settings: The Apex Settings instance (from app.core.config.get_settings()).
        """
        self.settings = settings
        self._mock_mode = getattr(settings, "MOCK_AGENTS", True)

    # ── Public interface ───────────────────────────────────────────────────────

    @abstractmethod
    async def run(self, input_data: dict) -> dict:
        """
        Execute the agent with the given input and return structured output.

        Concrete agents must:
          1. Check self._mock_mode — if True, call self._load_mock_fixture()
          2. Otherwise, call self._call_claude(prompt, model, system)
          3. Parse/validate output with Pydantic before returning

        Args:
            input_data: Agent-specific input payload.

        Returns:
            Agent-specific output dict (validated via Pydantic in concrete class).
        """
        ...

    # ── Mock support ───────────────────────────────────────────────────────────

    def _load_mock_fixture(self) -> dict:
        """
        Load the mock output fixture for this agent.

        Returns:
            Parsed JSON dict from fixtures/{agent_name}_mock_output.json

        Raises:
            FileNotFoundError if the fixture file is missing.
            ValueError if agent_name is not set on the subclass.
        """
        if not self.agent_name:
            raise ValueError(
                f"{self.__class__.__name__} must set 'agent_name' class attribute "
                "to match the AGENT_REGISTRY key."
            )
        fixture_path = _FIXTURES_DIR / f"{self.agent_name}_mock_output.json"
        if not fixture_path.exists():
            raise FileNotFoundError(
                f"Mock fixture not found: {fixture_path}. "
                "Create the file or set MOCK_AGENTS=false."
            )
        logger.debug("Loading mock fixture: %s", fixture_path)
        return json.loads(fixture_path.read_text(encoding="utf-8"))

    # ── Claude API call with retry ─────────────────────────────────────────────

    async def _call_claude(
        self,
        prompt: str,
        model: str,
        system: str = "",
        thinking_budget: int = 0,
    ) -> str:
        """
        Call the Anthropic Claude API with automatic retry (3x exponential backoff).

        In mock mode this method raises NotImplementedError — concrete agents
        should check self._mock_mode before calling this method.

        Args:
            prompt:          User-turn message content.
            model:           Model identifier from AGENT_REGISTRY (never hardcoded).
            system:          Optional system prompt. Prompt caching enabled on this.
            thinking_budget: When > 0, enables extended thinking with this token budget.
                             Only supported on claude-sonnet-4-6 and claude-opus-4-7.
                             Adds ~3x token cost — use only for complex reasoning agents.

        Returns:
            Raw text response from Claude (thinking blocks excluded).

        Raises:
            NotImplementedError: Always raised in mock mode.
            RuntimeError: If all retries are exhausted.
        """
        if self._mock_mode:
            raise NotImplementedError(
                "Mock mode is active (MOCK_AGENTS=true). "
                "Concrete agents must call _load_mock_fixture() instead of _call_claude()."
            )

        # Import here so the module is importable even without anthropic installed
        # during mock-only development.
        try:
            import anthropic  # noqa: PLC0415
        except ImportError as exc:
            raise RuntimeError(
                "anthropic package is not installed. "
                "Run: pip install -r requirements.txt"
            ) from exc

        client = anthropic.AsyncAnthropic(api_key=self.settings.ANTHROPIC_API_KEY)

        messages: list[dict] = [{"role": "user", "content": prompt}]

        last_exc: Exception | None = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                kwargs: dict[str, Any] = {
                    "model": model,
                    # When extended thinking is enabled, max_tokens must exceed
                    # budget_tokens — use 16000 to give the response room.
                    "max_tokens": 16000 if thinking_budget > 0 else 4096,
                    "messages": messages,
                }
                if system:
                    # Enable prompt caching for the system prompt — saves ~80% on
                    # repeated calls with the same system message.
                    kwargs["system"] = [
                        {
                            "type": "text",
                            "text": system,
                            "cache_control": {"type": "ephemeral"},
                        }
                    ]
                if thinking_budget > 0:
                    kwargs["thinking"] = {
                        "type": "enabled",
                        "budget_tokens": thinking_budget,
                    }

                response = await client.messages.create(**kwargs)

                # Extract text content — skip thinking blocks which appear first
                # when extended thinking is enabled.
                for block in response.content:
                    if getattr(block, "type", None) == "text":
                        return block.text
                return ""

            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                wait = _BACKOFF_BASE_SECONDS * (2 ** (attempt - 1))
                logger.warning(
                    "Claude API call failed (attempt %d/%d): %s. Retrying in %.1fs.",
                    attempt,
                    _MAX_RETRIES,
                    exc,
                    wait,
                )
                if attempt < _MAX_RETRIES:
                    await asyncio.sleep(wait)

        raise RuntimeError(
            f"Claude API call failed after {_MAX_RETRIES} attempts. "
            f"Last error: {last_exc}"
        ) from last_exc

    # ── Public audit helper (preferred over _log_agent_run) ───────────────────

    async def write_agent_run(
        self,
        *,
        user_id: str,
        model: str,
        input_data: dict,
        output_data: dict,
        tokens_in: int = 0,
        tokens_out: int = 0,
        cost_usd: float = 0.0,
        duration_ms: int = 0,
        status: str = "SUCCESS",
        error_message: str | None = None,
    ) -> None:
        """
        Public alias for _log_agent_run — preferred entry point for concrete agents.

        Inserts an audit record to `agent_runs` in Supabase (or logs under mock mode).
        The input/output are stored as SHA-256 hashes only — never raw content —
        to keep the table lightweight and avoid storing PII.

        Args:
            user_id:       Supabase user UUID (or surrogate ID in mock/test mode).
            model:         Model identifier used (from AGENT_REGISTRY).
            input_data:    Raw input dict — will be hashed, not stored.
            output_data:   Raw output dict — will be hashed, not stored.
            tokens_in:     Input token count from the API response.
            tokens_out:    Output token count from the API response.
            cost_usd:      Calculated cost at write time.
            duration_ms:   Wall-clock duration of the agent call in milliseconds.
            status:        "SUCCESS" | "FAILED" | "RETRIED"
            error_message: Populated when status is "FAILED".
        """
        await self._log_agent_run(
            user_id=user_id,
            model=model,
            input_data=input_data,
            output_data=output_data,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=cost_usd,
            duration_ms=duration_ms,
            status=status,
            error_message=error_message,
        )

    # ── Mock fixture loader (path-based variant) ───────────────────────────────

    def _get_mock_output(self, fixture_path: str) -> dict:
        """
        Load a mock output fixture from an explicit path.

        Unlike _load_mock_fixture() (which derives path from agent_name), this
        method accepts an explicit file path — useful when a single agent may
        have multiple fixture variants.

        Args:
            fixture_path: Absolute or relative path to a JSON fixture file.
                          Relative paths are resolved from the fixtures/ directory.

        Returns:
            Parsed JSON dict from the fixture file.

        Raises:
            FileNotFoundError: If the fixture file does not exist.
        """
        path = Path(fixture_path)
        if not path.is_absolute():
            path = _FIXTURES_DIR / fixture_path

        if not path.exists():
            raise FileNotFoundError(
                f"Mock fixture not found at: {path}. "
                "Create the fixture file or set MOCK_AGENTS=false."
            )
        logger.debug("Loading mock fixture (explicit path): %s", path)
        return json.loads(path.read_text(encoding="utf-8"))

    # ── Audit logging ──────────────────────────────────────────────────────────

    async def _log_agent_run(
        self,
        *,
        user_id: str,
        model: str,
        input_data: dict,
        output_data: dict,
        tokens_in: int = 0,
        tokens_out: int = 0,
        cost_usd: float = 0.0,
        duration_ms: int = 0,
        status: str = "SUCCESS",
        error_message: str | None = None,
    ) -> None:
        """
        Write an audit record to the agent_runs table in Supabase.

        This is a stub in Phase 1. In Phase 2, wire this to the Supabase client
        once the database schema is migrated.

        The input and output are stored as SHA-256 hashes only — never the raw
        content — to keep the audit table lightweight and avoid storing PII.

        Args:
            user_id:       Supabase user UUID.
            model:         Model identifier used for this run.
            input_data:    Raw input dict (will be hashed, not stored).
            output_data:   Raw output dict (will be hashed, not stored).
            tokens_in:     Input token count from the API response.
            tokens_out:    Output token count from the API response.
            cost_usd:      Calculated cost at write time.
            duration_ms:   Wall-clock duration of the agent call.
            status:        "SUCCESS" | "FAILED" | "RETRIED"
            error_message: Populated when status is "FAILED".
        """
        input_hash = hashlib.sha256(
            json.dumps(input_data, sort_keys=True).encode()
        ).hexdigest()
        output_hash = hashlib.sha256(
            json.dumps(output_data, sort_keys=True).encode()
        ).hexdigest()

        run_record = {
            "user_id": user_id,
            "agent_name": self.agent_name,
            "model_used": model,
            "input_hash": input_hash,
            "output_hash": output_hash,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "cost_usd": cost_usd,
            "duration_ms": duration_ms,
            "status": status,
            "error_message": error_message,
        }

        # TODO (Phase 2): Replace this log statement with a real Supabase insert:
        #   await supabase_client.table("agent_runs").insert(run_record).execute()
        logger.info(
            "agent_run [%s] user=%s status=%s tokens_in=%d tokens_out=%d cost=$%.6f",
            self.agent_name,
            user_id,
            status,
            tokens_in,
            tokens_out,
            cost_usd,
        )
        logger.debug("agent_run record (not yet persisted): %s", run_record)
