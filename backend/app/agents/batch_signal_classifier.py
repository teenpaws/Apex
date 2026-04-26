"""
Batch Signal Classifier Agent — classifies up to 10 signals per Claude Sonnet call.

Replaces the 1-signal/call Haiku approach. 10x fewer API calls.
Mock mode: all signals get the fixture result with their real signal_id.
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
_AGENT_KEY = "batch_signal_classifier"
_REGISTRY_CONFIG = AGENT_REGISTRY[_AGENT_KEY]

VALID_SIGNAL_TYPES = {
    "FUNDING", "EXEC_HIRE", "EXPANSION", "LAYOFF",
    "JOB_POSTING_PATTERN", "MA", "CONTRACT", "EARNINGS", "UNKNOWN",
}


class SignalBatchItem(BaseModel):
    signal_id: str
    title: str
    description: str
    source: str
    signal_date: str
    company_name: str


class BatchSignalClassifierInput(BaseModel):
    user_id: str
    user_target_industries: list[str] = Field(default_factory=list)
    user_target_roles: list[str] = Field(default_factory=list)
    signals: list[SignalBatchItem] = Field(default_factory=list)


class SignalClassificationResult(BaseModel):
    signal_id: str
    signal_type: str
    relevance_score: float = Field(ge=0.0, le=1.0)
    key_facts: list[str] = Field(default_factory=list)
    reasoning: str = ""


class BatchSignalClassifierOutput(BaseModel):
    results: list[SignalClassificationResult]


class BatchSignalClassifierAgent(BaseAgent):
    agent_name: str = _AGENT_KEY

    def __init__(self, settings: Any) -> None:
        super().__init__(settings)
        self._model: str = _REGISTRY_CONFIG["model"]
        self._system_prompt: str = self._load_system_prompt()

    async def classify_batch(self, input_data: BatchSignalClassifierInput) -> BatchSignalClassifierOutput:
        start_ms = int(time.monotonic() * 1000)

        if self._mock_mode:
            fixture = self._load_mock_fixture()
            mock_result = fixture["results"][0]
            results = [
                SignalClassificationResult(
                    signal_id=sig.signal_id,
                    signal_type=mock_result["signal_type"],
                    relevance_score=mock_result["relevance_score"],
                    key_facts=mock_result["key_facts"],
                    reasoning=mock_result["reasoning"],
                )
                for sig in input_data.signals
            ]
            output = BatchSignalClassifierOutput(results=results)
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
        raw_text = await self._call_claude(prompt=user_message, model=self._model, system=self._system_prompt)
        output = self._parse_response(raw_text, input_data.signals)
        duration_ms = int(time.monotonic() * 1000) - start_ms
        await self.write_agent_run(
            user_id=input_data.user_id,
            model=self._model,
            input_data=input_data.model_dump(mode="json"),
            output_data=output.model_dump(mode="json"),
            duration_ms=duration_ms,
            status="SUCCESS",
        )
        return output

    async def run(self, input_data: dict) -> dict:
        validated = BatchSignalClassifierInput(**input_data)
        output = await self.classify_batch(validated)
        return output.model_dump(mode="json")

    def _load_system_prompt(self) -> str:
        from pathlib import Path
        prompt_path = Path(__file__).parent / "prompts" / "batch_signal_classifier_v2.txt"
        if not prompt_path.exists():
            raise FileNotFoundError(f"Batch classifier prompt not found: {prompt_path}")
        return prompt_path.read_text(encoding="utf-8")

    def _build_user_message(self, input_data: BatchSignalClassifierInput) -> str:
        signals_json = json.dumps([s.model_dump(mode="json") for s in input_data.signals], indent=2)
        return (
            f"User target industries: {', '.join(input_data.user_target_industries) or 'Not specified'}\n"
            f"User target roles: {', '.join(input_data.user_target_roles) or 'Not specified'}\n\n"
            f"Signals to classify:\n{signals_json}\n\nReturn JSON as instructed."
        )

    def _parse_response(self, raw_text: str, original_signals: list[SignalBatchItem]) -> BatchSignalClassifierOutput:
        text = raw_text.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Batch classifier returned non-JSON: {raw_text[:300]}") from exc

        signal_ids = {s.signal_id for s in original_signals}
        results = []
        for item in data.get("results", []):
            if "signal_type" in item:
                item["signal_type"] = item["signal_type"].upper()
                if item["signal_type"] not in VALID_SIGNAL_TYPES:
                    item["signal_type"] = "UNKNOWN"
            if item.get("signal_id") in signal_ids:
                results.append(SignalClassificationResult(**item))

        # Fill UNKNOWN defaults for any signals Claude silently dropped —
        # ensures DB write always covers the full chunk with no silent data loss.
        returned_ids = {r.signal_id for r in results}
        for sig in original_signals:
            if sig.signal_id not in returned_ids:
                logger.warning(
                    "Batch classifier missing result for signal_id=%s; defaulting to UNKNOWN",
                    sig.signal_id,
                )
                results.append(SignalClassificationResult(
                    signal_id=sig.signal_id,
                    signal_type="UNKNOWN",
                    relevance_score=0.1,
                    key_facts=[],
                    reasoning="Missing from batch classifier response — defaulted to UNKNOWN",
                ))

        return BatchSignalClassifierOutput(results=results)
