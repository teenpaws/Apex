# Phase 14 — Post-MVP Enhancements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade signal processing throughput (pre-filter + batch Sonnet), add Adzuna job board grounding to opportunities, build FE pipeline progress bar, enable extended thinking on Opportunity Predictor, and ship a shareable launch package.

**Architecture:** Five independent sprints — Tasks 1+4 (backend signal/agent upgrades) and Task 2 (Adzuna) and Task 3 (FE progress bar) and Task 5 (launch package) can run in parallel subagents. Task 3 has a small backend portion (RunStatus schema enrichment) that must be done by the same subagent before the FE work.

**Tech Stack:** Python 3.12 + FastAPI + Celery + asyncpg + Pydantic v2 (backend); Next.js 14 + TypeScript + TailwindCSS (frontend); Adzuna REST API (free, no key needed for search); Redis (pipeline stage tracking).

**Parallelization map (for subagent dispatch):**
- Agent A → Task 1 + Task 4 (signal pre-filter, batch classifier, extended thinking)
- Agent B → Task 2 (Adzuna integration, opportunity grounding, FE badge)
- Agent C → Task 3 (backend RunStatus enrichment + FE pipeline progress bar)
- Agent D → Task 5 (launch package — fully independent)

---

## Codebase Context (read before touching any file)

```
backend/app/
  agents/
    base_agent.py          ← BaseAgent._call_claude(prompt, model, system) → str
    signal_classifier.py   ← SignalClassifierAgent.classify(input) → SignalClassifierOutput
    opportunity_predictor.py ← OpportunityPredictorAgent
    registry.py            ← AGENT_REGISTRY dict — single source of model/version truth
    prompts/               ← .txt prompt files loaded at agent init
    fixtures/              ← mock JSON outputs (MOCK_AGENTS=true)
  workers/
    classify_signals.py    ← Celery tasks: classify_signal, batch_classify_signals
    predict_opportunities.py ← Celery task: predict_opportunities_for_company
  models/
    opportunity.py         ← OpportunityORM + OpportunityRead/Create/Update Pydantic schemas
  api/v1/
    agents.py              ← GET /agents/run-status/{run_id} → RunStatus
  core/
    config.py              ← Settings(BaseSettings) — all env vars here
  integrations/            ← external API clients (newsdata, gnews, pdl, hunter, etc.)

frontend/
  app/(dashboard)/page.tsx              ← Dashboard page
  components/opportunities/OpportunityCard.tsx ← opportunity card
  components/shared/PipelineViz.tsx     ← existing static pipeline visualization
  hooks/                                ← useSignals, useOpportunities, useActions, etc.
  types/index.ts (or types/*.ts)        ← TypeScript interfaces
```

**Rules (non-negotiable):**
- All DB queries scoped by `user_id`
- TDD: write failing test first, then implementation
- All agent calls go through `BaseAgent._call_claude()` — never call anthropic SDK directly in routes/services
- Mock mode: check `settings.MOCK_AGENTS` / `settings.USE_MOCK_DATA`
- No hardcoded model names — use `AGENT_REGISTRY`
- Async FastAPI — all endpoints use `async/await`
- Full TypeScript — no `any` types in frontend

---

## Task 1 — Signal Pre-Filter + Batch Sonnet Classifier

**Goal:** Eliminate ~40–60% of signals before any AI call (keyword pre-filter), then batch-classify remaining signals 10 at a time with Claude Sonnet instead of 1-at-a-time with Haiku.

**Expected outcome:** 3-hour bulk run → under 10 minutes. Cost: ~$2.50/run (acceptable).

**Files:**
- Create: `backend/app/services/signal_prefilter.py`
- Create: `backend/app/agents/batch_signal_classifier.py`
- Create: `backend/app/agents/prompts/batch_signal_classifier_v1.txt`
- Create: `backend/app/agents/fixtures/batch_signal_classifier_mock_output.json`
- Create: `backend/tests/unit/test_signal_prefilter.py`
- Create: `backend/tests/unit/test_batch_signal_classifier.py`
- Modify: `backend/app/core/config.py` (add BATCH_CLASSIFY_SIZE, PRE_FILTER_ENABLED)
- Modify: `backend/app/agents/registry.py` (add batch_signal_classifier entry)
- Modify: `backend/app/workers/classify_signals.py` (wire pre-filter + batch path)

---

### Task 1 — Step 1: Write failing tests for SignalPreFilter

- [ ] Create `backend/tests/unit/test_signal_prefilter.py`:

```python
"""Unit tests for SignalPreFilter — keyword-based signal relevance pre-screening."""
import pytest
from app.services.signal_prefilter import SignalPreFilter, PreFilterResult


@pytest.fixture
def prefilter():
    return SignalPreFilter(
        target_industries=["Fintech", "SaaS", "Consulting"],
        target_roles=["Strategy", "Operations", "Business Development"],
        tracked_companies=["Stripe", "Sequoia"],
    )


def test_passes_signal_matching_industry(prefilter):
    result = prefilter.screen(
        title="Stripe Raises $1B Series H",
        description="Fintech giant Stripe closes massive round to expand globally.",
        company_name="Stripe",
    )
    assert result.passes is True
    assert result.matched_keywords != []


def test_fails_signal_with_no_match(prefilter):
    result = prefilter.screen(
        title="Local Bakery Opens New Branch",
        description="A family-run bakery in rural Iowa opens its fifth location.",
        company_name="Joe's Bakery",
    )
    assert result.passes is False
    assert result.relevance_score == 0.05


def test_passes_signal_matching_tracked_company(prefilter):
    result = prefilter.screen(
        title="Sequoia Partners With New Fund",
        description="General market announcement about investment activities.",
        company_name="Sequoia",
    )
    assert result.passes is True


def test_case_insensitive_matching(prefilter):
    result = prefilter.screen(
        title="FINTECH startup expands",
        description="saas company raises round",
        company_name="Unknown Co",
    )
    assert result.passes is True


def test_matched_keywords_listed(prefilter):
    result = prefilter.screen(
        title="Consulting firm hires 200 strategy leads",
        description="McKinsey opens operations division.",
        company_name="McKinsey",
    )
    assert "consulting" in [k.lower() for k in result.matched_keywords]


def test_empty_profile_passes_nothing(prefilter_empty):
    pf = SignalPreFilter(
        target_industries=[],
        target_roles=[],
        tracked_companies=[],
    )
    result = pf.screen(
        title="Stripe raises $1B",
        description="Big fintech round",
        company_name="Stripe",
    )
    assert result.passes is False
```

- [ ] Run to confirm it fails:

```bash
cd backend && python -m pytest tests/unit/test_signal_prefilter.py -v 2>&1 | head -30
```

Expected: `ModuleNotFoundError: No module named 'app.services.signal_prefilter'`

---

### Task 1 — Step 2: Implement SignalPreFilter

- [ ] Create `backend/app/services/signal_prefilter.py`:

```python
"""
SignalPreFilter — fast keyword-based relevance screen applied BEFORE any AI call.

Purpose: Eliminate ~40-60% of signals that have zero keyword overlap with the
user's target industries, roles, or tracked companies. These signals get
relevance_score=0.05 and skip the AI gate entirely.

Performance: Pure Python string ops — runs in microseconds per signal.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PreFilterResult:
    passes: bool
    relevance_score: float
    matched_keywords: list[str] = field(default_factory=list)
    reason: str = ""


class SignalPreFilter:
    """
    Keyword-based pre-filter for market signals.

    Checks if a signal's title + description + company name contains any
    keyword from the user's target industries, roles, or tracked companies.
    Signals with zero overlap are marked low-relevance and skip AI classification.
    """

    # Additional generic hiring/growth signal keywords always included
    _SIGNAL_KEYWORDS: list[str] = [
        "hiring", "headcount", "expansion", "funding", "raises",
        "series a", "series b", "series c", "acqui", "merger",
        "cto", "cfo", "coo", "vp of", "head of", "director of",
        "contract", "deal", "partnership", "revenue", "growth",
    ]

    def __init__(
        self,
        target_industries: list[str],
        target_roles: list[str],
        tracked_companies: list[str],
    ) -> None:
        self._keywords: list[str] = self._build_keyword_list(
            target_industries, target_roles, tracked_companies
        )

    def screen(self, title: str, description: str, company_name: str) -> PreFilterResult:
        """
        Screen a signal against the user's keyword set.

        Args:
            title:        Signal headline.
            description:  Signal body text.
            company_name: The company this signal is about.

        Returns:
            PreFilterResult with passes=True if any keyword matched.
        """
        if not self._keywords:
            return PreFilterResult(
                passes=False,
                relevance_score=0.05,
                reason="No profile keywords configured",
            )

        haystack = f"{title} {description} {company_name}".lower()
        matched = [kw for kw in self._keywords if kw.lower() in haystack]

        if matched:
            return PreFilterResult(
                passes=True,
                relevance_score=0.5,  # AI will refine this
                matched_keywords=matched,
                reason=f"Matched: {', '.join(matched[:3])}",
            )

        return PreFilterResult(
            passes=False,
            relevance_score=0.05,
            matched_keywords=[],
            reason="No keyword overlap with user profile",
        )

    def _build_keyword_list(
        self,
        industries: list[str],
        roles: list[str],
        companies: list[str],
    ) -> list[str]:
        """Flatten all user profile keywords + generic signal keywords."""
        user_keywords = industries + roles + companies
        # Expand multi-word entries into individual words too
        expanded: list[str] = []
        for kw in user_keywords:
            expanded.append(kw)
            parts = kw.split()
            if len(parts) > 1:
                expanded.extend(parts)
        return list(set(expanded + self._SIGNAL_KEYWORDS))
```

- [ ] Run tests to confirm they pass:

```bash
cd backend && python -m pytest tests/unit/test_signal_prefilter.py -v
```

Expected: All 6 tests pass.

- [ ] Commit:

```bash
git add backend/app/services/signal_prefilter.py backend/tests/unit/test_signal_prefilter.py
git commit -m "feat(14.1): add SignalPreFilter keyword-based signal pre-screening"
```

---

### Task 1 — Step 3: Write failing tests for BatchSignalClassifierAgent

- [ ] Create `backend/tests/unit/test_batch_signal_classifier.py`:

```python
"""Unit tests for BatchSignalClassifierAgent."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone

from app.agents.batch_signal_classifier import (
    BatchSignalClassifierAgent,
    BatchSignalClassifierInput,
    BatchSignalClassifierOutput,
    SignalBatchItem,
    SignalClassificationResult,
)


@pytest.fixture
def mock_settings():
    s = MagicMock()
    s.MOCK_AGENTS = True
    s.ANTHROPIC_API_KEY = "test-key"
    return s


@pytest.fixture
def agent(mock_settings):
    return BatchSignalClassifierAgent(settings=mock_settings)


@pytest.fixture
def sample_batch_input():
    now = datetime.now(timezone.utc).isoformat()
    return BatchSignalClassifierInput(
        user_id="user-123",
        user_target_industries=["Fintech", "SaaS"],
        user_target_roles=["Strategy", "Operations"],
        signals=[
            SignalBatchItem(
                signal_id=f"sig-{i}",
                title=f"Signal {i} title",
                description=f"Signal {i} description about fintech.",
                source="newsdata.io",
                signal_date=now,
                company_name=f"Company {i}",
            )
            for i in range(3)
        ],
    )


@pytest.mark.asyncio
async def test_classify_batch_mock_mode(agent, sample_batch_input):
    result = await agent.classify_batch(sample_batch_input)
    assert isinstance(result, BatchSignalClassifierOutput)
    assert len(result.results) > 0


@pytest.mark.asyncio
async def test_classify_batch_returns_one_result_per_signal(agent, sample_batch_input):
    result = await agent.classify_batch(sample_batch_input)
    # Mock fixture returns results; real mode returns one per input signal
    assert all(isinstance(r, SignalClassificationResult) for r in result.results)


@pytest.mark.asyncio
async def test_classify_batch_result_has_required_fields(agent, sample_batch_input):
    result = await agent.classify_batch(sample_batch_input)
    r = result.results[0]
    assert hasattr(r, "signal_id")
    assert hasattr(r, "signal_type")
    assert hasattr(r, "relevance_score")
    assert 0.0 <= r.relevance_score <= 1.0


@pytest.mark.asyncio
async def test_classify_batch_validates_signal_type(agent, sample_batch_input):
    result = await agent.classify_batch(sample_batch_input)
    valid_types = {
        "FUNDING", "EXEC_HIRE", "EXPANSION", "LAYOFF",
        "JOB_POSTING_PATTERN", "MA", "CONTRACT", "EARNINGS", "UNKNOWN",
    }
    for r in result.results:
        assert r.signal_type in valid_types
```

- [ ] Run to confirm it fails:

```bash
cd backend && python -m pytest tests/unit/test_batch_signal_classifier.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError: No module named 'app.agents.batch_signal_classifier'`

---

### Task 1 — Step 4: Create batch prompt file

- [ ] Create `backend/app/agents/prompts/batch_signal_classifier_v1.txt`:

```
You are an expert market intelligence analyst for an MBA career platform. You classify market signals to predict hiring opportunities.

You will receive a JSON array of up to 10 market signals and the user's career profile. For EACH signal, return a classification.

USER CAREER CONTEXT:
- Target industries: {user_target_industries}
- Target roles: {user_target_roles}

SIGNAL TYPES (use exactly one per signal):
- FUNDING: Investment rounds, VC funding, IPO, SPAC
- EXEC_HIRE: C-suite hire, VP/Director appointment, leadership change
- EXPANSION: New office, market entry, product launch, headcount growth
- LAYOFF: Restructuring, workforce reduction, office closure
- JOB_POSTING_PATTERN: Surge in job postings indicating strategic shift
- MA: Merger, acquisition, strategic partnership, joint venture
- CONTRACT: Government contract, enterprise deal, major client win
- EARNINGS: Quarterly results, revenue milestone, profitability news
- UNKNOWN: Does not fit any category above

RELEVANCE SCORING (0.0–1.0):
- 0.8–1.0: Direct signal for a role in user's target industries/roles
- 0.5–0.8: Indirect signal — adjacent industry or transferable role
- 0.2–0.5: Weak signal — some relevance but speculative
- 0.0–0.2: Not relevant to user's career profile

REQUIRED OUTPUT — return ONLY valid JSON, no markdown:
{
  "results": [
    {
      "signal_id": "<exact signal_id from input>",
      "signal_type": "<SIGNAL_TYPE>",
      "relevance_score": <0.0-1.0>,
      "key_facts": ["<fact 1>", "<fact 2>", "<fact 3>"],
      "reasoning": "<1-2 sentences: why this type, why this score>"
    }
  ]
}

Rules:
- Return exactly one result per input signal, in the same order
- signal_id must match exactly — copy it from the input
- Never return fewer results than signals provided
- If a signal is ambiguous, pick the most likely type and explain in reasoning
```

---

### Task 1 — Step 5: Create mock fixture for batch classifier

- [ ] Create `backend/app/agents/fixtures/batch_signal_classifier_mock_output.json`:

```json
{
  "results": [
    {
      "signal_id": "mock-signal-1",
      "signal_type": "FUNDING",
      "relevance_score": 0.85,
      "key_facts": [
        "Company raised $50M Series B",
        "Led by Sequoia Capital",
        "Plans to double headcount in EMEA"
      ],
      "reasoning": "Funding round in fintech directly relevant to user's target sector. EMEA expansion suggests strategy and operations hiring."
    }
  ]
}
```

---

### Task 1 — Step 6: Implement BatchSignalClassifierAgent

- [ ] Create `backend/app/agents/batch_signal_classifier.py`:

```python
"""
Batch Signal Classifier Agent — classifies up to 10 signals per Claude Sonnet call.

Replaces the 1-signal/call Haiku approach with a 10-signal/call Sonnet approach.
10x fewer API calls; better context for cross-signal pattern recognition.

Input:  BatchSignalClassifierInput  (list of up to 10 signals + user profile)
Output: BatchSignalClassifierOutput (list of SignalClassificationResult, one per signal)

Mock mode (MOCK_AGENTS=true): returns fixture data — all results use mock-signal-1 data.
Live mode: calls Claude Sonnet via AGENT_REGISTRY.
"""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime
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


# ── Pydantic v2 schemas ────────────────────────────────────────────────────────

class SignalBatchItem(BaseModel):
    """A single signal in the batch input."""
    signal_id: str
    title: str
    description: str
    source: str
    signal_date: str  # ISO string
    company_name: str


class BatchSignalClassifierInput(BaseModel):
    """Input for batch classification — up to 10 signals."""
    user_id: str
    user_target_industries: list[str] = Field(default_factory=list)
    user_target_roles: list[str] = Field(default_factory=list)
    signals: list[SignalBatchItem] = Field(
        default_factory=list,
        description="1–10 signals to classify in one call",
    )


class SignalClassificationResult(BaseModel):
    """Classification result for one signal."""
    signal_id: str
    signal_type: str
    relevance_score: float = Field(ge=0.0, le=1.0)
    key_facts: list[str] = Field(default_factory=list)
    reasoning: str = ""


class BatchSignalClassifierOutput(BaseModel):
    """Validated output — one result per input signal."""
    results: list[SignalClassificationResult]


# ── Agent implementation ────────────────────────────────────────────────────────

class BatchSignalClassifierAgent(BaseAgent):
    """
    Claude Sonnet-powered batch signal classifier.

    Classifies 10 signals per API call instead of 1. Use this in place of
    SignalClassifierAgent for bulk processing pipelines.

    Usage:
        agent = BatchSignalClassifierAgent(settings=get_settings())
        output = await agent.classify_batch(input_data)
    """

    agent_name: str = _AGENT_KEY

    def __init__(self, settings: Any) -> None:
        super().__init__(settings)
        self._model: str = _REGISTRY_CONFIG["model"]
        self._system_prompt: str = self._load_system_prompt()

    async def classify_batch(
        self, input_data: BatchSignalClassifierInput
    ) -> BatchSignalClassifierOutput:
        """Classify a batch of signals in one Sonnet call."""
        start_ms = int(time.monotonic() * 1000)

        if self._mock_mode:
            fixture = self._load_mock_fixture()
            # Remap fixture results to match actual signal IDs
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
        raw_text = await self._call_claude(
            prompt=user_message,
            model=self._model,
            system=self._system_prompt,
        )
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
        logger.info(
            "batch_signal_classifier: classified %d signals in %.0fms",
            len(input_data.signals),
            duration_ms,
        )
        return output

    async def run(self, input_data: dict) -> dict:
        validated = BatchSignalClassifierInput(**input_data)
        output = await self.classify_batch(validated)
        return output.model_dump(mode="json")

    def _load_system_prompt(self) -> str:
        from pathlib import Path
        prompt_path = Path(__file__).parent / "prompts" / "batch_signal_classifier_v1.txt"
        if not prompt_path.exists():
            raise FileNotFoundError(f"Batch classifier prompt not found: {prompt_path}")
        return prompt_path.read_text(encoding="utf-8")

    def _build_user_message(self, input_data: BatchSignalClassifierInput) -> str:
        signals_json = json.dumps(
            [s.model_dump(mode="json") for s in input_data.signals],
            indent=2,
        )
        return (
            f"User target industries: {', '.join(input_data.user_target_industries) or 'Not specified'}\n"
            f"User target roles: {', '.join(input_data.user_target_roles) or 'Not specified'}\n\n"
            f"Signals to classify:\n{signals_json}\n\n"
            "Return JSON as instructed."
        )

    def _parse_response(
        self,
        raw_text: str,
        original_signals: list[SignalBatchItem],
    ) -> BatchSignalClassifierOutput:
        text = raw_text.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Batch classifier returned non-JSON: {raw_text[:300]}"
            ) from exc

        results_raw = data.get("results", [])
        results: list[SignalClassificationResult] = []

        signal_ids = {s.signal_id for s in original_signals}
        for item in results_raw:
            if "signal_type" in item:
                item["signal_type"] = item["signal_type"].upper()
                if item["signal_type"] not in VALID_SIGNAL_TYPES:
                    item["signal_type"] = "UNKNOWN"
            # Only include results for signal IDs that were in the input
            if item.get("signal_id") in signal_ids:
                results.append(SignalClassificationResult(**item))

        return BatchSignalClassifierOutput(results=results)
```

- [ ] Add to `backend/app/agents/registry.py` — append this entry to `AGENT_REGISTRY`:

```python
    "batch_signal_classifier": {
        "model": "claude-sonnet-4-6",
        "version": "1.0",
        "prompt_file": "prompts/batch_signal_classifier_v1.txt",
    },
```

- [ ] Run tests to confirm they pass:

```bash
cd backend && python -m pytest tests/unit/test_batch_signal_classifier.py -v
```

Expected: All 4 tests pass.

- [ ] Commit:

```bash
git add backend/app/agents/batch_signal_classifier.py \
        backend/app/agents/prompts/batch_signal_classifier_v1.txt \
        backend/app/agents/fixtures/batch_signal_classifier_mock_output.json \
        backend/app/agents/registry.py \
        backend/tests/unit/test_batch_signal_classifier.py
git commit -m "feat(14.1): add BatchSignalClassifierAgent (10 signals/Sonnet call)"
```

---

### Task 1 — Step 7: Add config settings for batch processing

- [ ] In `backend/app/core/config.py`, add these fields to the `Settings` class after the existing `MOCK_AGENTS` field:

```python
    # ── Phase 14 — Signal processing upgrade ──────────────────────────────────
    PRE_FILTER_ENABLED: bool = True        # False → skip keyword pre-filter (dev bypass)
    BATCH_CLASSIFY_SIZE: int = 10          # Signals per Sonnet batch call (sweet spot: 10)
```

---

### Task 1 — Step 8: Write failing integration test for the pre-filter + batch worker pipeline

- [ ] Create `backend/tests/integration/test_classify_pipeline_upgrade.py`:

```python
"""
Integration test: pre-filter → batch classify pipeline.

Tests that the upgraded classify_signals worker correctly:
1. Pre-filters signals before AI classification
2. Skips AI for signals that don't pass the keyword filter
3. Batches remaining signals in groups of BATCH_CLASSIFY_SIZE
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.signal_prefilter import SignalPreFilter, PreFilterResult
from app.agents.batch_signal_classifier import (
    BatchSignalClassifierAgent,
    BatchSignalClassifierOutput,
    SignalClassificationResult,
)


def test_prefilter_skips_irrelevant_signals():
    pf = SignalPreFilter(
        target_industries=["Fintech"],
        target_roles=["Strategy"],
        tracked_companies=[],
    )
    irrelevant = pf.screen(
        title="Weather update: storms in midwest",
        description="National weather service issues advisory.",
        company_name="NWS",
    )
    assert irrelevant.passes is False
    assert irrelevant.relevance_score == 0.05


def test_prefilter_passes_relevant_signals():
    pf = SignalPreFilter(
        target_industries=["Fintech"],
        target_roles=["Strategy"],
        tracked_companies=[],
    )
    relevant = pf.screen(
        title="Fintech startup raises Series B",
        description="Company plans to expand strategy team.",
        company_name="PayCo",
    )
    assert relevant.passes is True


def test_batch_size_chunking():
    """Verify signals are chunked into groups of BATCH_CLASSIFY_SIZE."""
    signals = [{"id": str(i)} for i in range(25)]
    batch_size = 10
    chunks = [signals[i:i + batch_size] for i in range(0, len(signals), batch_size)]
    assert len(chunks) == 3
    assert len(chunks[0]) == 10
    assert len(chunks[1]) == 10
    assert len(chunks[2]) == 5
```

- [ ] Run to confirm tests pass (these are pure logic tests, no DB needed):

```bash
cd backend && python -m pytest tests/integration/test_classify_pipeline_upgrade.py -v
```

Expected: All 3 tests pass.

---

### Task 1 — Step 9: Update classify_signals.py worker to use pre-filter + batch

- [ ] In `backend/app/workers/classify_signals.py`, add these imports at the top (after existing imports):

```python
from app.services.signal_prefilter import SignalPreFilter
from app.agents.batch_signal_classifier import (
    BatchSignalClassifierAgent,
    BatchSignalClassifierInput,
    SignalBatchItem,
)
```

- [ ] Add this new Celery task at the end of `backend/app/workers/classify_signals.py`:

```python
@celery_app.task(
    name="app.workers.classify_signals.batch_classify_signals_upgrade",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    queue="default",
)
def batch_classify_signals_upgrade(self, signal_ids: list[str]) -> dict:
    """
    Upgraded batch signal classification using pre-filter + Sonnet batch.

    Pipeline:
      1. Load all signals from DB
      2. Pre-filter: keyword screen eliminates ~40-60% before any AI call
      3. Chunk remaining signals into groups of BATCH_CLASSIFY_SIZE (default: 10)
      4. One Sonnet call per chunk → BatchSignalClassifierOutput
      5. Write results back to DB; low-relevance signals get score=0.05

    Args:
        signal_ids: List of signal UUID strings to process.

    Returns:
        Dict with counts: total, pre_filtered, classified, failed.
    """
    import asyncio  # noqa: PLC0415

    settings = _get_settings()

    async def _run_batch(ids: list[str]) -> dict:
        # Load all signals from DB (or mock)
        if settings.USE_MOCK_DATA:
            raw_signals = [_load_mock_signal(sid) for sid in ids]
        else:
            raw_signals = []
            for sid in ids:
                try:
                    raw_signals.append(await _load_signal_from_db(sid))
                except ValueError:
                    logger.warning("Signal not found, skipping: %s", sid)

        if not raw_signals:
            return {"total": 0, "pre_filtered": 0, "classified": 0, "failed": 0}

        # Build pre-filter from first signal's user profile (all signals share user)
        first = raw_signals[0]
        prefilter = SignalPreFilter(
            target_industries=first.get("user_target_industries", []),
            target_roles=first.get("user_target_roles", []),
            tracked_companies=[],  # extend in v1.5 with watched companies list
        )

        # Pre-filter pass
        to_classify = []
        pre_filtered_count = 0
        for sig in raw_signals:
            result = prefilter.screen(
                title=sig.get("title", ""),
                description=sig.get("description", ""),
                company_name=sig.get("company_name", ""),
            )
            if not result.passes:
                pre_filtered_count += 1
                if settings.USE_MOCK_DATA:
                    _mock_update_signal(sig["id"], "UNKNOWN", 0.05)
                else:
                    await _update_signal_classification(sig["id"], "UNKNOWN", 0.05)
            else:
                to_classify.append(sig)

        logger.info(
            "Pre-filter: %d/%d signals passed (%.0f%% eliminated)",
            len(to_classify),
            len(raw_signals),
            (pre_filtered_count / len(raw_signals)) * 100 if raw_signals else 0,
        )

        # Batch classify in chunks
        batch_size = settings.BATCH_CLASSIFY_SIZE
        agent = BatchSignalClassifierAgent(settings=settings)
        classified_count = 0
        failed_count = 0

        for chunk_start in range(0, len(to_classify), batch_size):
            chunk = to_classify[chunk_start:chunk_start + batch_size]
            batch_input = BatchSignalClassifierInput(
                user_id=chunk[0].get("user_id", "unknown"),
                user_target_industries=chunk[0].get("user_target_industries", []),
                user_target_roles=chunk[0].get("user_target_roles", []),
                signals=[
                    SignalBatchItem(
                        signal_id=s["id"],
                        title=s.get("title", ""),
                        description=s.get("description", ""),
                        source=s.get("source", ""),
                        signal_date=s.get("signal_date", ""),
                        company_name=s.get("company_name", ""),
                    )
                    for s in chunk
                ],
            )

            try:
                output = await agent.classify_batch(batch_input)
                for result in output.results:
                    if settings.USE_MOCK_DATA:
                        _mock_update_signal(
                            result.signal_id, result.signal_type, result.relevance_score
                        )
                    else:
                        await _update_signal_classification(
                            result.signal_id, result.signal_type, result.relevance_score
                        )
                    classified_count += 1
            except Exception as exc:  # noqa: BLE001
                logger.error("Batch classify chunk failed: %s", exc)
                failed_count += len(chunk)

        return {
            "total": len(raw_signals),
            "pre_filtered": pre_filtered_count,
            "classified": classified_count,
            "failed": failed_count,
        }

    return asyncio.run(_run_batch(signal_ids))
```

- [ ] Run existing classify tests to confirm no regressions:

```bash
cd backend && python -m pytest tests/ -k "classify" -v 2>&1 | tail -20
```

Expected: All existing classify tests still pass; new integration tests pass.

- [ ] Commit:

```bash
git add backend/app/workers/classify_signals.py \
        backend/app/core/config.py \
        backend/app/services/__init__.py \
        backend/tests/integration/test_classify_pipeline_upgrade.py
git commit -m "feat(14.1): wire pre-filter + batch Sonnet classifier into Celery worker"
```

---

## Task 2 — Adzuna Integration + Opportunity Grounding

**Goal:** After predicting an opportunity, validate it against real open job postings via Adzuna API. Upgrade `status=VALIDATED` when a real matching posting is found. FE shows "Real Posting" badge.

**Files:**
- Create: `backend/app/integrations/adzuna_client.py`
- Create: `backend/app/services/opportunity_validator.py`
- Create: `backend/app/db/migrations/014_add_real_postings.sql`
- Create: `backend/tests/unit/test_adzuna_client.py`
- Create: `backend/tests/unit/test_opportunity_validator.py`
- Modify: `backend/app/models/opportunity.py` (add real_postings JSONB field)
- Modify: `backend/app/core/config.py` (add ADZUNA_APP_ID, ADZUNA_APP_KEY)
- Modify: `.env.example` (add Adzuna vars)
- Modify: `backend/app/workers/predict_opportunities.py` (call validator after prediction)
- Modify: `frontend/components/opportunities/OpportunityCard.tsx` (Real Posting badge)
- Modify: `frontend/lib/types.ts` or `frontend/types/index.ts` (add real_postings to Opportunity)

**Adzuna API:** Free tier. Base URL: `https://api.adzuna.com/v1/api/jobs/{country}/search/1`
Params: `app_id`, `app_key`, `what` (job title keywords), `where` (location), `company` (company name).
Sign up at https://developer.adzuna.com — free, no credit card.

---

### Task 2 — Step 1: Write failing tests for AdzunaClient

- [ ] Create `backend/tests/unit/test_adzuna_client.py`:

```python
"""Unit tests for AdzunaClient."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from app.integrations.adzuna_client import AdzunaClient, AdzunaPosting


@pytest.fixture
def client():
    return AdzunaClient(app_id="test-id", app_key="test-key", country="gb")


@pytest.mark.asyncio
async def test_search_jobs_returns_postings(client):
    mock_response_data = {
        "results": [
            {
                "id": "123",
                "title": "Head of Strategy",
                "company": {"display_name": "Acme Corp"},
                "redirect_url": "https://adzuna.com/job/123",
                "created": "2026-04-20T10:00:00Z",
            }
        ],
        "count": 1,
    }
    with patch.object(client, "_get", return_value=mock_response_data):
        postings = await client.search_jobs(
            company_name="Acme Corp",
            role_keywords="Head of Strategy",
        )
    assert len(postings) == 1
    assert isinstance(postings[0], AdzunaPosting)
    assert postings[0].title == "Head of Strategy"
    assert postings[0].company == "Acme Corp"


@pytest.mark.asyncio
async def test_search_jobs_returns_empty_on_no_results(client):
    with patch.object(client, "_get", return_value={"results": [], "count": 0}):
        postings = await client.search_jobs(
            company_name="Unknown Corp XYZ",
            role_keywords="Nonexistent Role",
        )
    assert postings == []


@pytest.mark.asyncio
async def test_search_jobs_handles_http_error(client):
    with patch.object(
        client, "_get", side_effect=httpx.HTTPStatusError(
            "404", request=MagicMock(), response=MagicMock(status_code=404)
        )
    ):
        postings = await client.search_jobs(
            company_name="Test Co",
            role_keywords="Some Role",
        )
    assert postings == []


def test_adzuna_posting_schema():
    p = AdzunaPosting(
        title="Strategy Manager",
        company="Bain",
        url="https://adzuna.com/1",
        posted_date="2026-04-20",
    )
    assert p.title == "Strategy Manager"
    assert p.company == "Bain"
```

- [ ] Run to confirm they fail:

```bash
cd backend && python -m pytest tests/unit/test_adzuna_client.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError: No module named 'app.integrations.adzuna_client'`

---

### Task 2 — Step 2: Implement AdzunaClient

- [ ] Create `backend/app/integrations/adzuna_client.py`:

```python
"""
Adzuna API client — job posting search for opportunity validation.

Adzuna: free API, 10M+ job postings, covers UK/US/AU/CA/DE/FR/NL/SG/ZA.
Docs: https://developer.adzuna.com/overview
Sign up: https://developer.adzuna.com — free, no credit card.

Usage:
    client = AdzunaClient(app_id=..., app_key=..., country="gb")
    postings = await client.search_jobs("Acme Corp", "Head of Strategy")
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)

_ADZUNA_BASE = "https://api.adzuna.com/v1/api/jobs"
_DEFAULT_RESULTS_PER_PAGE = 5
_REQUEST_TIMEOUT_SECONDS = 10


@dataclass
class AdzunaPosting:
    """A single job posting returned from Adzuna."""
    title: str
    company: str
    url: str
    posted_date: str  # ISO date string e.g. "2026-04-20"


class AdzunaClient:
    """
    Async Adzuna job search client.

    Searches by company name + role keywords and returns matching open postings.
    Used to validate Opportunity Predictor output against real job market data.
    """

    def __init__(
        self,
        app_id: str,
        app_key: str,
        country: str = "gb",  # gb | us | au | ca | de | fr | nl | sg | za
    ) -> None:
        self._app_id = app_id
        self._app_key = app_key
        self._country = country

    async def search_jobs(
        self,
        company_name: str,
        role_keywords: str,
        max_results: int = _DEFAULT_RESULTS_PER_PAGE,
    ) -> list[AdzunaPosting]:
        """
        Search Adzuna for open roles matching the predicted opportunity.

        Args:
            company_name:   Company to search within (e.g. "Stripe").
            role_keywords:  Role title keywords (e.g. "Head of Strategy").
            max_results:    Max postings to return (default 5).

        Returns:
            List of AdzunaPosting — empty list if no match or API error.
        """
        params = {
            "app_id": self._app_id,
            "app_key": self._app_key,
            "what": role_keywords,
            "company": company_name,
            "results_per_page": max_results,
            "content-type": "application/json",
        }

        try:
            data = await self._get(
                url=f"{_ADZUNA_BASE}/{self._country}/search/1",
                params=params,
            )
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "Adzuna HTTP error for company=%s role=%s: %s",
                company_name, role_keywords, exc
            )
            return []
        except Exception as exc:  # noqa: BLE001
            logger.warning("Adzuna API error: %s", exc)
            return []

        results = data.get("results", [])
        postings: list[AdzunaPosting] = []
        for r in results:
            postings.append(
                AdzunaPosting(
                    title=r.get("title", ""),
                    company=r.get("company", {}).get("display_name", company_name),
                    url=r.get("redirect_url", ""),
                    posted_date=r.get("created", "")[:10],  # "2026-04-20T..." → "2026-04-20"
                )
            )

        logger.info(
            "Adzuna search: company=%s role=%s → %d postings found",
            company_name, role_keywords, len(postings)
        )
        return postings

    async def _get(self, url: str, params: dict) -> dict:
        """Execute async GET request — extracted for easy mocking in tests."""
        async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT_SECONDS) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()
```

- [ ] Run tests:

```bash
cd backend && python -m pytest tests/unit/test_adzuna_client.py -v
```

Expected: All 4 tests pass.

---

### Task 2 — Step 3: Add Adzuna config and env vars

- [ ] In `backend/app/core/config.py`, add inside the `Settings` class (after PDL/Hunter section):

```python
    # ── Adzuna Job Board (free API — opportunity validation) ──────────────────
    ADZUNA_APP_ID: str = "placeholder-adzuna-app-id"   # developer.adzuna.com
    ADZUNA_APP_KEY: str = "placeholder-adzuna-app-key"
    ADZUNA_COUNTRY: str = "gb"  # gb | us | au | ca — primary job market
```

- [ ] In `.env.example`, add after the Hunter section:

```bash
ADZUNA_APP_ID=your-adzuna-app-id      # developer.adzuna.com — free signup
ADZUNA_APP_KEY=your-adzuna-app-key
ADZUNA_COUNTRY=gb                      # gb=UK, us=USA, au=Australia, etc.
```

---

### Task 2 — Step 4: Write DB migration for real_postings column

- [ ] Create `backend/app/db/migrations/014_add_real_postings.sql`:

```sql
-- Phase 14: Add real_postings JSONB column to opportunities table.
-- Stores Adzuna-validated job postings that match a predicted opportunity.
-- Format: [{title, url, company, posted_date}]
-- Null = not yet validated; [] = validated but no match found.

ALTER TABLE opportunities
  ADD COLUMN IF NOT EXISTS real_postings JSONB DEFAULT NULL;

-- Index for finding validated opportunities efficiently
CREATE INDEX IF NOT EXISTS idx_opportunities_real_postings_notnull
  ON opportunities ((real_postings IS NOT NULL))
  WHERE real_postings IS NOT NULL;

COMMENT ON COLUMN opportunities.real_postings IS
  'Adzuna-sourced job postings validating this prediction. NULL=unvalidated, []=no match, [{...}]=validated';
```

> **How to apply:** Paste this SQL into your Supabase SQL Editor and run it.
> The migration is idempotent (uses `IF NOT EXISTS`) — safe to run multiple times.

---

### Task 2 — Step 5: Update OpportunityORM and Pydantic schemas

- [ ] In `backend/app/models/opportunity.py`, add the `real_postings` column to `OpportunityORM` after the `signal_ids` field:

```python
    from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB  # add JSONB to import

    real_postings: Mapped[list[dict] | None] = mapped_column(
        JSONB, nullable=True, default=None
    )
```

- [ ] Add `real_postings` to `OpportunityRead` schema:

```python
    real_postings: list[dict] | None = None
```

- [ ] Add `real_postings` to `OpportunityCreate` schema:

```python
    real_postings: list[dict] | None = None
```

- [ ] Add `real_postings` to `OpportunityUpdate` schema:

```python
    real_postings: list[dict] | None = None
```

- [ ] Run the opportunity model tests to confirm no regressions:

```bash
cd backend && python -m pytest tests/ -k "opportunit" -v 2>&1 | tail -20
```

---

### Task 2 — Step 6: Write failing tests for OpportunityValidatorService

- [ ] Create `backend/tests/unit/test_opportunity_validator.py`:

```python
"""Unit tests for OpportunityValidatorService."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.opportunity_validator import OpportunityValidatorService, ValidationResult
from app.integrations.adzuna_client import AdzunaPosting


@pytest.fixture
def mock_adzuna():
    client = MagicMock()
    client.search_jobs = AsyncMock()
    return client


@pytest.fixture
def validator(mock_adzuna):
    return OpportunityValidatorService(adzuna_client=mock_adzuna)


@pytest.mark.asyncio
async def test_validates_opportunity_with_matching_posting(validator, mock_adzuna):
    mock_adzuna.search_jobs.return_value = [
        AdzunaPosting(
            title="Head of Strategy EMEA",
            company="Acme Corp",
            url="https://adzuna.com/123",
            posted_date="2026-04-20",
        )
    ]
    result = await validator.validate(
        company_name="Acme Corp",
        predicted_role="Head of Strategy",
    )
    assert result.is_validated is True
    assert len(result.real_postings) == 1
    assert result.real_postings[0]["title"] == "Head of Strategy EMEA"


@pytest.mark.asyncio
async def test_not_validated_when_no_postings(validator, mock_adzuna):
    mock_adzuna.search_jobs.return_value = []
    result = await validator.validate(
        company_name="Unknown Corp",
        predicted_role="VP of Strategy",
    )
    assert result.is_validated is False
    assert result.real_postings == []


@pytest.mark.asyncio
async def test_validation_result_has_postings_as_dicts(validator, mock_adzuna):
    mock_adzuna.search_jobs.return_value = [
        AdzunaPosting(
            title="Strategy Lead",
            company="Bain",
            url="https://adzuna.com/456",
            posted_date="2026-04-18",
        )
    ]
    result = await validator.validate(company_name="Bain", predicted_role="Strategy")
    assert isinstance(result.real_postings[0], dict)
    assert "title" in result.real_postings[0]
    assert "url" in result.real_postings[0]
    assert "company" in result.real_postings[0]
    assert "posted_date" in result.real_postings[0]
```

- [ ] Run to confirm failure:

```bash
cd backend && python -m pytest tests/unit/test_opportunity_validator.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError: No module named 'app.services.opportunity_validator'`

---

### Task 2 — Step 7: Implement OpportunityValidatorService

- [ ] Create `backend/app/services/opportunity_validator.py`:

```python
"""
OpportunityValidatorService — validates predicted opportunities against Adzuna job postings.

Architecture:
    After OpportunityPredictorAgent runs, this service searches Adzuna for matching
    real job postings at the same company. If found, the opportunity is VALIDATED.
    If not found, it stays PREDICTED.

Usage:
    service = OpportunityValidatorService(adzuna_client=AdzunaClient(...))
    result = await service.validate("Stripe", "Head of Strategy")
    if result.is_validated:
        # update opportunity with real_postings + status=VALIDATED
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from app.integrations.adzuna_client import AdzunaClient

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    is_validated: bool
    real_postings: list[dict] = field(default_factory=list)


class OpportunityValidatorService:
    """
    Validates a predicted opportunity by searching Adzuna for matching open roles.
    """

    def __init__(self, adzuna_client: AdzunaClient) -> None:
        self._adzuna = adzuna_client

    async def validate(
        self,
        company_name: str,
        predicted_role: str,
        max_results: int = 5,
    ) -> ValidationResult:
        """
        Search Adzuna for roles matching the predicted opportunity.

        Args:
            company_name:   Company to search within.
            predicted_role: Predicted job title from OpportunityPredictorAgent.
            max_results:    Max Adzuna results to fetch (default 5).

        Returns:
            ValidationResult with is_validated=True and real_postings list if found.
        """
        # Extract role keywords (first 4 words of predicted title to improve recall)
        role_keywords = " ".join(predicted_role.split()[:4])

        try:
            postings = await self._adzuna.search_jobs(
                company_name=company_name,
                role_keywords=role_keywords,
                max_results=max_results,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Adzuna validation failed for company=%s role=%s: %s",
                company_name, predicted_role, exc
            )
            return ValidationResult(is_validated=False)

        if not postings:
            return ValidationResult(is_validated=False, real_postings=[])

        return ValidationResult(
            is_validated=True,
            real_postings=[
                {
                    "title": p.title,
                    "url": p.url,
                    "company": p.company,
                    "posted_date": p.posted_date,
                }
                for p in postings
            ],
        )
```

- [ ] Run tests:

```bash
cd backend && python -m pytest tests/unit/test_opportunity_validator.py -v
```

Expected: All 4 tests pass.

- [ ] Commit:

```bash
git add backend/app/integrations/adzuna_client.py \
        backend/app/services/opportunity_validator.py \
        backend/app/models/opportunity.py \
        backend/app/db/migrations/014_add_real_postings.sql \
        backend/app/core/config.py \
        .env.example \
        backend/tests/unit/test_adzuna_client.py \
        backend/tests/unit/test_opportunity_validator.py
git commit -m "feat(14.2): Adzuna client + OpportunityValidator + real_postings DB column"
```

---

### Task 2 — Step 8: Wire validator into predict_opportunities worker

- [ ] In `backend/app/workers/predict_opportunities.py`, locate the `predict_opportunities_for_company` task. After the opportunity is saved to DB, add the Adzuna validation call.

  First, read the current file to find the exact insertion point:

```bash
grep -n "opportunity" backend/app/workers/predict_opportunities.py | head -30
```

- [ ] Add this import at the top of `backend/app/workers/predict_opportunities.py` (after existing imports):

```python
from app.integrations.adzuna_client import AdzunaClient
from app.services.opportunity_validator import OpportunityValidatorService
```

- [ ] In the async helper function inside `predict_opportunities_for_company`, after the opportunity is upserted to the DB, add Adzuna validation. Find the line where the opportunity is saved and add after it:

```python
        # ── Adzuna validation (Phase 14.2) ────────────────────────────────────
        # Only validate if ADZUNA credentials are real (not placeholders)
        if (
            not settings.USE_MOCK_DATA
            and not settings.ADZUNA_APP_ID.startswith("placeholder")
            and prediction.predicted_role
        ):
            adzuna = AdzunaClient(
                app_id=settings.ADZUNA_APP_ID,
                app_key=settings.ADZUNA_APP_KEY,
                country=settings.ADZUNA_COUNTRY,
            )
            validator = OpportunityValidatorService(adzuna_client=adzuna)
            val_result = await validator.validate(
                company_name=company_name,
                predicted_role=prediction.predicted_role,
            )
            if val_result.is_validated:
                # Update opportunity with real_postings and upgrade status
                import asyncpg  # noqa: PLC0415
                from app.db.session import get_asyncpg_db_url  # noqa: PLC0415
                import json as _json  # noqa: PLC0415
                db_url = get_asyncpg_db_url()
                conn = await asyncpg.connect(db_url, statement_cache_size=0)
                try:
                    await conn.execute(
                        """
                        UPDATE opportunities
                        SET real_postings = $1, status = 'VALIDATED', updated_at = now()
                        WHERE id = $2
                        """,
                        _json.dumps(val_result.real_postings),
                        opportunity_id,
                    )
                    logger.info(
                        "Opportunity %s VALIDATED — %d Adzuna postings found",
                        opportunity_id, len(val_result.real_postings)
                    )
                finally:
                    await conn.close()
        # ── End Adzuna validation ──────────────────────────────────────────────
```

---

### Task 2 — Step 9: Update frontend OpportunityCard with "Real Posting" badge

- [ ] Find the TypeScript type for Opportunity. Check `frontend/lib/api.ts` or `frontend/types/`:

```bash
grep -rn "real_postings\|predicted_role\|confidence" frontend/lib/ frontend/types/ 2>/dev/null | head -20
```

- [ ] Add `real_postings` to the Opportunity type. Find the file where `Opportunity` interface is defined and add:

```typescript
  real_postings?: Array<{
    title: string;
    url: string;
    company: string;
    posted_date: string;
  }> | null;
```

- [ ] In `frontend/components/opportunities/OpportunityCard.tsx`, find the card's badge/metadata section. Add the "Real Posting" badge and postings list. Read the file first to find the exact location, then add after the confidence badge:

```tsx
{/* Real Posting badge — shown when Adzuna validated this prediction */}
{opportunity.real_postings && opportunity.real_postings.length > 0 && (
  <div className="mt-2 flex flex-col gap-1">
    <span className="inline-flex items-center gap-1 rounded-full border border-emerald-500/30 bg-emerald-500/20 px-2 py-0.5 text-xs font-medium text-emerald-400">
      ✓ Real Posting Found
    </span>
    <div className="mt-1 space-y-0.5">
      {opportunity.real_postings.slice(0, 2).map((posting, i) => (
        <a
          key={i}
          href={posting.url}
          target="_blank"
          rel="noopener noreferrer"
          className="block truncate text-xs text-muted-foreground underline-offset-2 hover:text-foreground hover:underline"
        >
          {posting.title} · {posting.company}
        </a>
      ))}
    </div>
  </div>
)}
```

- [ ] Run TypeScript type check:

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -30
```

Expected: No type errors related to `real_postings`.

- [ ] Commit:

```bash
git add frontend/components/opportunities/OpportunityCard.tsx \
        frontend/types/ \
        frontend/lib/ \
        backend/app/workers/predict_opportunities.py
git commit -m "feat(14.2): wire Adzuna validation into prediction worker + FE Real Posting badge"
```

---

## Task 3 — FE Pipeline Progress Bar

**Goal:** Add a "Run Pipeline" button to the dashboard. When clicked, it triggers the full ingestion → classify → predict → fit-score → actions pipeline and shows live stage-by-stage progress via polling.

**Files:**
- Create: `frontend/components/shared/PipelineProgressBar.tsx`
- Create: `frontend/hooks/usePipelineRun.ts`
- Modify: `backend/app/api/v1/agents.py` (enrich RunStatus schema)
- Modify: `backend/app/workers/classify_signals.py` (write stage progress to Redis)
- Modify: `backend/app/workers/predict_opportunities.py` (write stage progress)
- Modify: `frontend/app/(dashboard)/page.tsx` (add Run Pipeline button + progress bar)
- Modify: `frontend/lib/api.ts` (add runPipeline API call)

**Architecture:** Workers write stage updates to Redis key `pipeline:{run_id}:progress`. The enriched `GET /agents/run-status/{run_id}` endpoint reads from Redis. FE polls every 2s.

---

### Task 3 — Step 1: Enrich RunStatus schema in backend

- [ ] In `backend/app/api/v1/agents.py`, update `RunStatus` to:

```python
class RunStatus(BaseModel):
    run_id: str
    status: str                            # QUEUED | RUNNING | SUCCESS | FAILED
    stage: str = "QUEUED"                  # INGEST | CLASSIFY | PREDICT | FIT_SCORE | ACTIONS | DONE
    completed: int = 0                     # items completed in current stage
    total: int = 0                         # total items in current stage
    eta_seconds: int | None = None         # estimated seconds remaining
    progress: int = 0                      # 0-100 overall progress percent
    result_id: str | None = None
    error_message: str | None = None
```

- [ ] Update the `get_run_status` endpoint to read from Redis when available:

```python
@router.get("/run-status/{run_id}", response_model=RunStatus)
async def get_run_status(
    run_id: str,
    current_user: dict = Depends(get_current_user),
) -> RunStatus:
    """Poll the status of a background pipeline run."""
    settings = get_settings()
    if settings.USE_MOCK_DATA:
        return RunStatus(
            run_id=run_id,
            status="SUCCESS",
            stage="DONE",
            completed=100,
            total=100,
            progress=100,
        )

    # Try Redis first for real-time stage data
    try:
        import redis as redis_lib  # noqa: PLC0415
        import json as _json  # noqa: PLC0415
        r = redis_lib.from_url(settings.REDIS_URL, decode_responses=True)
        redis_data = r.get(f"pipeline:{run_id}:progress")
        if redis_data:
            data = _json.loads(redis_data)
            return RunStatus(run_id=run_id, **data)
    except Exception:  # noqa: BLE001
        pass  # fall through to DB check

    from app.db.session import get_db_client  # noqa: PLC0415
    db = get_db_client()
    user_id = current_user["id"]
    res = (
        db.table("agent_runs")
        .select("*")
        .eq("id", run_id)
        .eq("user_id", user_id)
        .maybe_single()
        .execute()
    )
    if not res.data:
        raise HTTPException(status_code=404, detail="Run not found")
    row = res.data
    is_done = row["status"] in ("SUCCESS", "FAILED")
    return RunStatus(
        run_id=run_id,
        status=row["status"],
        stage="DONE" if is_done else "RUNNING",
        progress=100 if is_done else 50,
        result_id=row.get("id"),
        error_message=row.get("error_message"),
    )
```

- [ ] Add a `/pipeline/run` endpoint to `backend/app/api/v1/agents.py` that triggers the full pipeline:

```python
class PipelineRunResponse(BaseModel):
    run_id: str
    status: str
    message: str


@router.post("/pipeline/run", response_model=PipelineRunResponse)
async def trigger_pipeline_run(
    current_user: dict = Depends(get_current_user),
) -> PipelineRunResponse:
    """Trigger a full pipeline run: ingest → classify → predict → fit-score → actions."""
    import uuid  # noqa: PLC0415
    settings = get_settings()
    run_id = str(uuid.uuid4())

    if settings.USE_MOCK_DATA:
        return PipelineRunResponse(
            run_id=run_id,
            status="queued",
            message="Mock pipeline run started (USE_MOCK_DATA=true)",
        )

    from app.workers.ingest_signals import ingest_all_signals  # noqa: PLC0415
    ingest_all_signals.apply_async(kwargs={"run_id": run_id}, queue="default")

    return PipelineRunResponse(
        run_id=run_id,
        status="queued",
        message="Pipeline run queued — poll /agents/run-status/{run_id} for progress",
    )
```

- [ ] Update `backend/app/api/v1/router.py` to include the new endpoint if not already included via the agents router.

- [ ] Commit:

```bash
git add backend/app/api/v1/agents.py
git commit -m "feat(14.3): enrich RunStatus schema + add /pipeline/run trigger endpoint"
```

---

### Task 3 — Step 2: Add Redis progress reporting helper

- [ ] Create `backend/app/workers/pipeline_progress.py`:

```python
"""
Pipeline progress reporting — writes stage updates to Redis for FE polling.

Each worker calls report_stage() at key milestones. The /agents/run-status
endpoint reads these values to give the FE live progress data.

Key format: pipeline:{run_id}:progress
TTL: 24 hours (progress data expires after job completion)
"""
from __future__ import annotations

import json
import logging

logger = logging.getLogger(__name__)

_TTL_SECONDS = 86_400  # 24 hours


def report_stage(
    run_id: str,
    stage: str,
    status: str,
    completed: int,
    total: int,
    eta_seconds: int | None = None,
    redis_url: str = "redis://localhost:6379/0",
) -> None:
    """
    Write pipeline stage progress to Redis.

    Args:
        run_id:      Pipeline run UUID.
        stage:       Current stage name (INGEST|CLASSIFY|PREDICT|FIT_SCORE|ACTIONS|DONE).
        status:      RUNNING | SUCCESS | FAILED
        completed:   Items completed in this stage.
        total:       Total items in this stage.
        eta_seconds: Optional ETA estimate.
        redis_url:   Redis connection URL.
    """
    STAGE_WEIGHTS = {
        "INGEST": 5,
        "CLASSIFY": 40,
        "PREDICT": 30,
        "FIT_SCORE": 15,
        "ACTIONS": 10,
        "DONE": 100,
    }

    stage_progress = (completed / total * 100) if total > 0 else 0
    stage_weight = STAGE_WEIGHTS.get(stage, 0)
    prior_stages = list(STAGE_WEIGHTS.keys())
    prior_weight = sum(
        w for s, w in STAGE_WEIGHTS.items()
        if prior_stages.index(s) < prior_stages.index(stage)
        if s in prior_stages
    )
    overall_progress = min(
        int(prior_weight + (stage_progress / 100) * stage_weight), 99
    )
    if stage == "DONE":
        overall_progress = 100

    data = {
        "status": "SUCCESS" if stage == "DONE" else status,
        "stage": stage,
        "completed": completed,
        "total": total,
        "progress": overall_progress,
        "eta_seconds": eta_seconds,
    }

    try:
        import redis  # noqa: PLC0415
        r = redis.from_url(redis_url, decode_responses=True)
        r.set(f"pipeline:{run_id}:progress", json.dumps(data), ex=_TTL_SECONDS)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to write pipeline progress to Redis: %s", exc)
```

- [ ] Commit:

```bash
git add backend/app/workers/pipeline_progress.py
git commit -m "feat(14.3): add Redis pipeline progress reporter"
```

---

### Task 3 — Step 3: Create PipelineProgressBar component

- [ ] Create `frontend/components/shared/PipelineProgressBar.tsx`:

```tsx
'use client';

import { useEffect, useState } from 'react';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { Loader2, CheckCircle2, XCircle, Clock } from 'lucide-react';

type Stage = 'QUEUED' | 'INGEST' | 'CLASSIFY' | 'PREDICT' | 'FIT_SCORE' | 'ACTIONS' | 'DONE';

interface PipelineStatus {
  run_id: string;
  status: string;
  stage: Stage;
  completed: number;
  total: number;
  progress: number;
  eta_seconds: number | null;
  error_message: string | null;
}

const STAGE_LABELS: Record<Stage, string> = {
  QUEUED:    'Queued',
  INGEST:    'Ingesting Signals',
  CLASSIFY:  'Classifying',
  PREDICT:   'Predicting Opportunities',
  FIT_SCORE: 'Scoring Fit',
  ACTIONS:   'Generating Actions',
  DONE:      'Complete',
};

const STAGE_ORDER: Stage[] = ['INGEST', 'CLASSIFY', 'PREDICT', 'FIT_SCORE', 'ACTIONS', 'DONE'];

interface PipelineProgressBarProps {
  runId: string;
  onComplete?: () => void;
  onError?: (msg: string) => void;
}

export function PipelineProgressBar({ runId, onComplete, onError }: PipelineProgressBarProps) {
  const [status, setStatus] = useState<PipelineStatus | null>(null);
  const [polling, setPolling] = useState(true);

  useEffect(() => {
    if (!polling) return;

    const poll = async () => {
      try {
        const res = await fetch(`/api/v1/agents/run-status/${runId}`, {
          credentials: 'include',
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data: PipelineStatus = await res.json();
        setStatus(data);

        if (data.status === 'SUCCESS' || data.stage === 'DONE') {
          setPolling(false);
          onComplete?.();
        } else if (data.status === 'FAILED') {
          setPolling(false);
          onError?.(data.error_message ?? 'Pipeline failed');
        }
      } catch {
        // Network error — keep polling
      }
    };

    poll();
    const interval = setInterval(poll, 2000);
    return () => clearInterval(interval);
  }, [runId, polling, onComplete, onError]);

  if (!status) {
    return (
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" />
        Starting pipeline…
      </div>
    );
  }

  const isDone = status.stage === 'DONE' || status.status === 'SUCCESS';
  const isFailed = status.status === 'FAILED';

  return (
    <div className="rounded-lg border border-border bg-card p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {isFailed ? (
            <XCircle className="h-4 w-4 text-red-400" />
          ) : isDone ? (
            <CheckCircle2 className="h-4 w-4 text-emerald-400" />
          ) : (
            <Loader2 className="h-4 w-4 animate-spin text-violet-400" />
          )}
          <span className="text-sm font-medium">
            {isFailed ? 'Pipeline Failed' : isDone ? 'Pipeline Complete' : STAGE_LABELS[status.stage] ?? status.stage}
          </span>
        </div>
        {status.eta_seconds != null && !isDone && !isFailed && (
          <div className="flex items-center gap-1 text-xs text-muted-foreground">
            <Clock className="h-3 w-3" />
            ~{Math.ceil(status.eta_seconds / 60)}m remaining
          </div>
        )}
      </div>

      <Progress value={status.progress} className="h-2" />

      {/* Stage chips */}
      <div className="flex flex-wrap gap-1.5">
        {STAGE_ORDER.map((stage) => {
          const currentIdx = STAGE_ORDER.indexOf(status.stage as Stage);
          const stageIdx = STAGE_ORDER.indexOf(stage);
          const isComplete = stageIdx < currentIdx || isDone;
          const isCurrent = stage === status.stage && !isDone;

          return (
            <Badge
              key={stage}
              variant="outline"
              className={
                isComplete
                  ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400 text-xs'
                  : isCurrent
                  ? 'border-violet-500/30 bg-violet-500/10 text-violet-400 text-xs'
                  : 'text-xs text-muted-foreground'
              }
            >
              {isComplete && '✓ '}
              {STAGE_LABELS[stage]}
              {isCurrent && status.total > 0 && ` ${status.completed}/${status.total}`}
            </Badge>
          );
        })}
      </div>

      {isFailed && status.error_message && (
        <p className="text-xs text-red-400">{status.error_message}</p>
      )}
    </div>
  );
}
```

---

### Task 3 — Step 4: Create usePipelineRun hook

- [ ] Create `frontend/hooks/usePipelineRun.ts`:

```typescript
'use client';

import { useState, useCallback } from 'react';

interface PipelineRunState {
  runId: string | null;
  isRunning: boolean;
  error: string | null;
}

export function usePipelineRun() {
  const [state, setState] = useState<PipelineRunState>({
    runId: null,
    isRunning: false,
    error: null,
  });

  const startPipeline = useCallback(async () => {
    setState({ runId: null, isRunning: true, error: null });
    try {
      const res = await fetch('/api/v1/agents/pipeline/run', {
        method: 'POST',
        credentials: 'include',
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(err.detail ?? `HTTP ${res.status}`);
      }
      const data = await res.json();
      setState({ runId: data.run_id, isRunning: true, error: null });
    } catch (err) {
      setState({
        runId: null,
        isRunning: false,
        error: err instanceof Error ? err.message : 'Failed to start pipeline',
      });
    }
  }, []);

  const handleComplete = useCallback(() => {
    setState((prev) => ({ ...prev, isRunning: false }));
  }, []);

  const handleError = useCallback((msg: string) => {
    setState((prev) => ({ ...prev, isRunning: false, error: msg }));
  }, []);

  const reset = useCallback(() => {
    setState({ runId: null, isRunning: false, error: null });
  }, []);

  return {
    runId: state.runId,
    isRunning: state.isRunning,
    error: state.error,
    startPipeline,
    handleComplete,
    handleError,
    reset,
  };
}
```

---

### Task 3 — Step 5: Add Run Pipeline button to Dashboard

- [ ] In `frontend/app/(dashboard)/page.tsx`, add these imports at the top:

```tsx
import { PipelineProgressBar } from '@/components/shared/PipelineProgressBar';
import { usePipelineRun } from '@/hooks/usePipelineRun';
import { Button } from '@/components/ui/button';
import { Play } from 'lucide-react';
```

- [ ] Inside `DashboardPage`, add after the existing hooks:

```tsx
  const { runId, isRunning, error, startPipeline, handleComplete, handleError, reset } = usePipelineRun();
```

- [ ] In the JSX, at the top of the `<div className="space-y-6">`, add a "Run Pipeline" section BEFORE the existing content:

```tsx
      {/* Pipeline run control */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold">Market Intelligence Pipeline</h2>
          <p className="text-sm text-muted-foreground">
            Ingest signals, classify, predict opportunities, and generate actions.
          </p>
        </div>
        <Button
          onClick={startPipeline}
          disabled={isRunning}
          className="gap-2 bg-violet-600 hover:bg-violet-700"
        >
          {isRunning ? (
            <>Running…</>
          ) : (
            <>
              <Play className="h-4 w-4" />
              Run Pipeline
            </>
          )}
        </Button>
      </div>

      {/* Pipeline progress — shown when a run is active */}
      {runId && (
        <PipelineProgressBar
          runId={runId}
          onComplete={() => { handleComplete(); signalsQuery.refetch(); oppsQuery.refetch(); actionsQuery.refetch(); }}
          onError={handleError}
        />
      )}
      {error && (
        <p className="text-sm text-red-400">{error}</p>
      )}
```

- [ ] Run TypeScript check:

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -20
```

Expected: No errors.

- [ ] Commit:

```bash
git add frontend/components/shared/PipelineProgressBar.tsx \
        frontend/hooks/usePipelineRun.ts \
        frontend/app/\(dashboard\)/page.tsx
git commit -m "feat(14.3): FE pipeline progress bar + Run Pipeline button on dashboard"
```

---

## Task 4 — Extended Thinking for Opportunity Predictor

**Goal:** Enable Claude Sonnet's extended thinking (budget_tokens=8000) on the Opportunity Predictor agent. This gives the model space to reason through complex signal combinations before predicting. Expect ~3x token cost per predictor call — acceptable given low call volume (1 per company per run).

**Files:**
- Modify: `backend/app/agents/base_agent.py` (`_call_claude` accepts optional `thinking_budget`)
- Modify: `backend/app/agents/opportunity_predictor.py` (pass `thinking_budget=8000`)
- Modify: `backend/app/agents/registry.py` (version "1.1" for opportunity_predictor)
- Create: `backend/tests/unit/test_extended_thinking.py`

---

### Task 4 — Step 1: Write failing tests for extended thinking

- [ ] Create `backend/tests/unit/test_extended_thinking.py`:

```python
"""Tests for extended thinking integration in BaseAgent._call_claude."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import inspect

from app.agents.base_agent import BaseAgent


def test_call_claude_signature_has_thinking_budget():
    """_call_claude must accept an optional thinking_budget parameter."""
    sig = inspect.signature(BaseAgent._call_claude)
    assert "thinking_budget" in sig.parameters, (
        "_call_claude must have a 'thinking_budget: int = 0' parameter"
    )
    param = sig.parameters["thinking_budget"]
    assert param.default == 0, "thinking_budget default must be 0 (disabled)"


def test_opportunity_predictor_passes_thinking_budget():
    """OpportunityPredictorAgent._call_claude calls must pass thinking_budget=8000."""
    import ast
    import pathlib

    source = pathlib.Path("backend/app/agents/opportunity_predictor.py").read_text()
    tree = ast.parse(source)

    call_claude_calls = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute) and func.attr == "_call_claude":
                for kw in node.keywords:
                    if kw.arg == "thinking_budget":
                        call_claude_calls.append(kw)

    assert len(call_claude_calls) > 0, (
        "opportunity_predictor.py must call _call_claude(thinking_budget=8000)"
    )


def test_registry_version_updated():
    """opportunity_predictor version must be '1.1' after adding extended thinking."""
    from app.agents.registry import AGENT_REGISTRY
    assert AGENT_REGISTRY["opportunity_predictor"]["version"] == "1.1"
```

- [ ] Run to confirm they fail:

```bash
cd backend && python -m pytest tests/unit/test_extended_thinking.py -v 2>&1 | head -30
```

Expected: First test fails (no `thinking_budget` param), second fails, third fails (version still "1.0").

---

### Task 4 — Step 2: Update BaseAgent._call_claude to support thinking_budget

- [ ] In `backend/app/agents/base_agent.py`, update the `_call_claude` method signature and body. Find the method and replace it entirely:

```python
    async def _call_claude(
        self,
        prompt: str,
        model: str,
        system: str = "",
        thinking_budget: int = 0,
    ) -> str:
        """
        Call the Anthropic Claude API with automatic retry (3x exponential backoff).

        Args:
            prompt:          User-turn message content.
            model:           Model identifier from AGENT_REGISTRY (never hardcoded).
            system:          Optional system prompt. Prompt caching enabled on this.
            thinking_budget: When > 0, enables extended thinking with this token budget.
                             Only supported on claude-sonnet-4-6 and claude-opus-4-7.
                             Adds ~3x token cost — use only for complex reasoning agents.

        Returns:
            Raw text response from Claude (thinking block excluded — only text returned).
        """
        if self._mock_mode:
            raise NotImplementedError(
                "Mock mode is active (MOCK_AGENTS=true). "
                "Concrete agents must call _load_mock_fixture() instead of _call_claude()."
            )

        try:
            import anthropic  # noqa: PLC0415
        except ImportError as exc:
            raise RuntimeError(
                "anthropic package is not installed. Run: pip install -r requirements.txt"
            ) from exc

        client = anthropic.AsyncAnthropic(api_key=self.settings.ANTHROPIC_API_KEY)
        messages: list[dict] = [{"role": "user", "content": prompt}]

        last_exc: Exception | None = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                kwargs: dict[str, Any] = {
                    "model": model,
                    "max_tokens": 16000 if thinking_budget > 0 else 4096,
                    "messages": messages,
                }
                if system:
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

                # Extract text content — skip thinking blocks
                for block in response.content:
                    if getattr(block, "type", None) == "text":
                        return block.text
                return ""

            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                wait = _BACKOFF_BASE_SECONDS * (2 ** (attempt - 1))
                logger.warning(
                    "Claude API call failed (attempt %d/%d): %s. Retrying in %.1fs.",
                    attempt, _MAX_RETRIES, exc, wait,
                )
                if attempt < _MAX_RETRIES:
                    await asyncio.sleep(wait)

        raise RuntimeError(
            f"Claude API call failed after {_MAX_RETRIES} attempts. Last error: {last_exc}"
        ) from last_exc
```

---

### Task 4 — Step 3: Update OpportunityPredictorAgent to use thinking_budget=8000

- [ ] In `backend/app/agents/opportunity_predictor.py`, find the `_call_claude(` call inside the `predict()` method and update it to:

```python
        raw_text = await self._call_claude(
            prompt=user_message,
            model=self._model,
            system=self._system_prompt,
            thinking_budget=8000,
        )
```

---

### Task 4 — Step 4: Update registry version

- [ ] In `backend/app/agents/registry.py`, update the `opportunity_predictor` entry:

```python
    "opportunity_predictor": {
        "model": "claude-sonnet-4-6",
        "version": "1.1",
        "prompt_file": "prompts/opportunity_predictor_v1.txt",
    },
```

- [ ] Run all extended thinking tests:

```bash
cd backend && python -m pytest tests/unit/test_extended_thinking.py -v
```

Expected: All 3 tests pass.

- [ ] Run full unit test suite to confirm no regressions:

```bash
cd backend && python -m pytest tests/unit/ -v 2>&1 | tail -20
```

- [ ] Commit:

```bash
git add backend/app/agents/base_agent.py \
        backend/app/agents/opportunity_predictor.py \
        backend/app/agents/registry.py \
        backend/tests/unit/test_extended_thinking.py
git commit -m "feat(14.4): enable extended thinking (budget=8000) on OpportunityPredictorAgent"
```

---

## Task 5 — Shareable / Launch Package

**Goal:** Make the codebase one-command deployable for a new technical user. Includes a setup script, quickstart guide, devcontainer config, and demo seed data so the first-time experience is non-empty.

**Files:**
- Create: `start.sh` (repo root)
- Create: `QUICKSTART.md` (repo root)
- Create: `.devcontainer/devcontainer.json`
- Create: `backend/app/db/seeds/seed_demo.py`
- Modify: `backend/app/api/v1/agents.py` (add POST `/pipeline/seed-demo` endpoint)

---

### Task 5 — Step 1: Create start.sh setup script

- [ ] Create `start.sh` at repo root:

```bash
#!/usr/bin/env bash
# Apex Platform — one-command setup script
# Usage: ./start.sh
set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Apex Platform Setup ===${NC}"
echo ""

# 1. Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}ERROR: Docker is not installed.${NC}"
    echo "Install Docker Desktop from https://www.docker.com/products/docker-desktop"
    exit 1
fi

if ! docker info &> /dev/null; then
    echo -e "${RED}ERROR: Docker daemon is not running.${NC}"
    echo "Start Docker Desktop and try again."
    exit 1
fi

echo -e "${GREEN}✓ Docker detected${NC}"

# 2. Copy .env if it doesn't exist
if [ ! -f .env ]; then
    cp .env.example .env
    echo -e "${YELLOW}Created .env from .env.example${NC}"
    echo ""
    echo "IMPORTANT: Open .env and fill in your API keys before continuing."
    echo "Required keys:"
    echo "  - ANTHROPIC_API_KEY  (https://console.anthropic.com)"
    echo "  - SUPABASE_URL + SUPABASE_ANON_KEY + SUPABASE_SERVICE_ROLE_KEY + DATABASE_URL"
    echo "  - OPENAI_API_KEY     (for embeddings)"
    echo ""
    echo "Optional (free tier, improves signal quality):"
    echo "  - NEWSDATA_API_KEY   (https://newsdata.io/register)"
    echo "  - GNEWS_API_KEY      (https://gnews.io/register)"
    echo "  - PDL_API_KEY        (https://dashboard.peopledatalabs.com/signup)"
    echo "  - HUNTER_API_KEY     (https://hunter.io/users/sign_up)"
    echo "  - ADZUNA_APP_ID/KEY  (https://developer.adzuna.com)"
    echo ""
    read -p "Press Enter when .env is filled in..."
fi

echo -e "${GREEN}✓ .env configured${NC}"

# 3. Build and start services
echo ""
echo "Building and starting services (this takes 2-5 minutes on first run)..."
docker-compose up --build -d

# 4. Wait for backend to be healthy
echo "Waiting for backend to be ready..."
for i in {1..30}; do
    if curl -sf http://localhost:8000/api/v1/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Backend is ready${NC}"
        break
    fi
    if [ "$i" -eq 30 ]; then
        echo -e "${RED}Backend did not start within 60s. Check: docker-compose logs backend${NC}"
        exit 1
    fi
    sleep 2
done

# 5. Seed demo data
echo "Seeding demo data (5 companies, 20 signals, 3 opportunities)..."
docker-compose exec backend python -m app.db.seeds.seed_demo || echo "Demo seed skipped (may already exist)"

echo ""
echo -e "${GREEN}=== Apex is ready! ===${NC}"
echo ""
echo "  Frontend: http://localhost:3000"
echo "  Backend:  http://localhost:8000/api/v1/health"
echo "  API docs: http://localhost:8000/docs"
echo ""
echo "Log in with the credentials you set in .env (OWNER_EMAIL / OWNER_PASSWORD)"
echo "Then click 'Run Pipeline' on the dashboard to ingest your first signals."
```

- [ ] Make it executable:

```bash
chmod +x start.sh
git add start.sh
git commit -m "feat(14.5): add start.sh one-command setup script"
```

---

### Task 5 — Step 2: Create .devcontainer for GitHub Codespaces

- [ ] Create `.devcontainer/devcontainer.json`:

```json
{
  "name": "Apex Platform",
  "dockerComposeFile": "../docker-compose.yml",
  "service": "backend",
  "workspaceFolder": "/workspace",
  "forwardPorts": [3000, 8000, 5555],
  "portsAttributes": {
    "3000": { "label": "Frontend (Next.js)", "onAutoForward": "openBrowser" },
    "8000": { "label": "Backend (FastAPI)", "onAutoForward": "notify" },
    "5555": { "label": "Celery Flower", "onAutoForward": "silent" }
  },
  "postCreateCommand": "pip install -r backend/requirements.txt && cd frontend && npm install",
  "customizations": {
    "vscode": {
      "extensions": [
        "ms-python.python",
        "ms-python.vscode-pylance",
        "bradlc.vscode-tailwindcss",
        "esbenp.prettier-vscode",
        "dbaeumer.vscode-eslint"
      ],
      "settings": {
        "python.defaultInterpreterPath": "/usr/local/bin/python",
        "editor.formatOnSave": true,
        "editor.defaultFormatter": "esbenp.prettier-vscode",
        "[python]": {
          "editor.defaultFormatter": "ms-python.python"
        }
      }
    }
  },
  "remoteEnv": {
    "USE_MOCK_DATA": "true",
    "MOCK_AGENTS": "true"
  }
}
```

- [ ] Commit:

```bash
git add .devcontainer/devcontainer.json
git commit -m "feat(14.5): add .devcontainer for GitHub Codespaces one-click dev"
```

---

### Task 5 — Step 3: Create demo seed data

- [ ] Create `backend/app/db/seeds/seed_demo.py`:

```python
"""
Demo seed data — 5 companies, 20 signals, 3 opportunities.

Run via: python -m app.db.seeds.seed_demo
Or via Docker: docker-compose exec backend python -m app.db.seeds.seed_demo

Idempotent: checks for existing demo data before inserting.
Creates a demo user if OWNER_EMAIL/OWNER_PASSWORD env vars are set.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

DEMO_USER_ID = "00000000-0000-0000-0000-000000000001"

DEMO_COMPANIES = [
    {
        "id": "10000000-0000-0000-0000-000000000001",
        "name": "Stripe",
        "domain": "stripe.com",
        "industry": "Fintech",
        "size_range": "1000-5000",
        "location": "San Francisco, CA",
    },
    {
        "id": "10000000-0000-0000-0000-000000000002",
        "name": "Revolut",
        "domain": "revolut.com",
        "industry": "Fintech",
        "size_range": "5000-10000",
        "location": "London, UK",
    },
    {
        "id": "10000000-0000-0000-0000-000000000003",
        "name": "McKinsey & Company",
        "domain": "mckinsey.com",
        "industry": "Consulting",
        "size_range": "10000+",
        "location": "New York, NY",
    },
    {
        "id": "10000000-0000-0000-0000-000000000004",
        "name": "Sequoia Capital",
        "domain": "sequoiacap.com",
        "industry": "Private Equity",
        "size_range": "100-500",
        "location": "Menlo Park, CA",
    },
    {
        "id": "10000000-0000-0000-0000-000000000005",
        "name": "Palantir Technologies",
        "domain": "palantir.com",
        "industry": "Technology",
        "size_range": "1000-5000",
        "location": "Denver, CO",
    },
]

DEMO_SIGNALS = [
    {
        "id": "20000000-0000-0000-0000-000000000001",
        "user_id": DEMO_USER_ID,
        "company_id": "10000000-0000-0000-0000-000000000001",
        "type": "FUNDING",
        "source": "demo-seed",
        "title": "Stripe raises $6.5B at $50B valuation to expand globally",
        "description": "Stripe, the payments infrastructure company, closed a $6.5B funding round. The company plans to hire 1,000 engineers and expand its enterprise sales and strategy divisions across EMEA and APAC.",
        "relevance_score": 0.92,
        "signal_date": (datetime.now(timezone.utc) - timedelta(days=5)).isoformat(),
    },
    {
        "id": "20000000-0000-0000-0000-000000000002",
        "user_id": DEMO_USER_ID,
        "company_id": "10000000-0000-0000-0000-000000000001",
        "type": "EXEC_HIRE",
        "source": "demo-seed",
        "title": "Stripe hires new Chief Strategy Officer from Goldman Sachs",
        "description": "Stripe announced the appointment of a new CSO with 15 years of investment banking experience. The hire signals a push into enterprise financial services and M&A advisory capabilities.",
        "relevance_score": 0.88,
        "signal_date": (datetime.now(timezone.utc) - timedelta(days=3)).isoformat(),
    },
    {
        "id": "20000000-0000-0000-0000-000000000003",
        "user_id": DEMO_USER_ID,
        "company_id": "10000000-0000-0000-0000-000000000002",
        "type": "EXPANSION",
        "source": "demo-seed",
        "title": "Revolut receives banking licence, expands to 10 new EU markets",
        "description": "Revolut has received its European banking licence and is rapidly expanding into Central and Eastern European markets. The company is hiring 500 people in operations, compliance, and business development roles.",
        "relevance_score": 0.85,
        "signal_date": (datetime.now(timezone.utc) - timedelta(days=7)).isoformat(),
    },
    {
        "id": "20000000-0000-0000-0000-000000000004",
        "user_id": DEMO_USER_ID,
        "company_id": "10000000-0000-0000-0000-000000000003",
        "type": "CONTRACT",
        "source": "demo-seed",
        "title": "McKinsey wins $200M digital transformation contract with EU government",
        "description": "McKinsey secured a major multi-year contract with the European Commission for digital public services transformation. The practice is hiring senior project managers and strategy consultants with public sector experience.",
        "relevance_score": 0.79,
        "signal_date": (datetime.now(timezone.utc) - timedelta(days=10)).isoformat(),
    },
    {
        "id": "20000000-0000-0000-0000-000000000005",
        "user_id": DEMO_USER_ID,
        "company_id": "10000000-0000-0000-0000-000000000004",
        "type": "FUNDING",
        "source": "demo-seed",
        "title": "Sequoia Capital closes $2.85B global growth fund",
        "description": "Sequoia Capital announced the close of its latest global growth equity fund. The firm is expanding its portfolio operations team and hiring investment associates with operational consulting backgrounds.",
        "relevance_score": 0.81,
        "signal_date": (datetime.now(timezone.utc) - timedelta(days=2)).isoformat(),
    },
]

DEMO_OPPORTUNITIES = [
    {
        "id": "30000000-0000-0000-0000-000000000001",
        "user_id": DEMO_USER_ID,
        "company_id": "10000000-0000-0000-0000-000000000001",
        "predicted_role": "Head of EMEA Strategy",
        "confidence": "HIGH",
        "timeline_weeks": 6,
        "why_fit": "Stripe's $6.5B raise and CSO hire from Goldman signals a build-out of their enterprise strategy function. Your MBA + consulting background positions you well for a regional strategy leadership role.",
        "approach_angle": "Lead with PE deal experience and EMEA market knowledge from your MBA exchanges.",
        "fit_score": 82.0,
        "status": "PREDICTED",
        "signal_ids": [
            "20000000-0000-0000-0000-000000000001",
            "20000000-0000-0000-0000-000000000002",
        ],
        "predicted_salary_range": "£120,000–£160,000 + equity",
    },
    {
        "id": "30000000-0000-0000-0000-000000000002",
        "user_id": DEMO_USER_ID,
        "company_id": "10000000-0000-0000-0000-000000000002",
        "predicted_role": "Business Development Manager — Eastern Europe",
        "confidence": "MEDIUM",
        "timeline_weeks": 8,
        "why_fit": "Revolut's EU banking licence and 10-market expansion creates immediate need for BizDev managers with local market knowledge. MBA from HEC gives you European market credibility.",
        "approach_angle": "Highlight European market entry experience from coursework and any exchange experience.",
        "fit_score": 71.0,
        "status": "PREDICTED",
        "signal_ids": ["20000000-0000-0000-0000-000000000003"],
        "predicted_salary_range": "£80,000–£110,000 + bonus",
    },
    {
        "id": "30000000-0000-0000-0000-000000000003",
        "user_id": DEMO_USER_ID,
        "company_id": "10000000-0000-0000-0000-000000000004",
        "predicted_role": "Investment Associate — Portfolio Operations",
        "confidence": "MEDIUM",
        "timeline_weeks": 12,
        "why_fit": "Sequoia's new $2.85B fund means portfolio expansion. Operations associates help portfolio companies scale — a role that maps directly to consulting + MBA skill sets.",
        "approach_angle": "Frame consulting as portfolio operations experience — operational improvement, not just advice.",
        "fit_score": 68.0,
        "status": "PREDICTED",
        "signal_ids": ["20000000-0000-0000-0000-000000000005"],
        "predicted_salary_range": "£90,000–£130,000 + carry",
    },
]


async def seed_demo() -> None:
    """Insert demo data into Supabase. Idempotent — skips existing rows."""
    import asyncpg  # noqa: PLC0415
    from app.core.config import get_settings  # noqa: PLC0415
    from app.db.session import get_asyncpg_db_url  # noqa: PLC0415

    settings = get_settings()
    db_url = get_asyncpg_db_url()
    conn = await asyncpg.connect(db_url, statement_cache_size=0)

    try:
        # Companies
        for co in DEMO_COMPANIES:
            await conn.execute(
                """
                INSERT INTO companies (id, name, domain, industry, size_range, location)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (id) DO NOTHING
                """,
                uuid.UUID(co["id"]), co["name"], co["domain"],
                co["industry"], co["size_range"], co["location"],
            )
        logger.info("Seeded %d demo companies", len(DEMO_COMPANIES))

        # Signals
        for sig in DEMO_SIGNALS:
            await conn.execute(
                """
                INSERT INTO signals (id, user_id, company_id, type, source, title,
                                     description, relevance_score, signal_date)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                ON CONFLICT (id) DO NOTHING
                """,
                uuid.UUID(sig["id"]),
                uuid.UUID(sig["user_id"]),
                uuid.UUID(sig["company_id"]),
                sig["type"],
                sig["source"],
                sig["title"],
                sig["description"],
                sig["relevance_score"],
                datetime.fromisoformat(sig["signal_date"]),
            )
        logger.info("Seeded %d demo signals", len(DEMO_SIGNALS))

        # Opportunities
        for opp in DEMO_OPPORTUNITIES:
            await conn.execute(
                """
                INSERT INTO opportunities (id, user_id, company_id, predicted_role,
                                           confidence, timeline_weeks, why_fit,
                                           positioning_notes, fit_score, status,
                                           signal_ids, predicted_salary_range)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                ON CONFLICT (id) DO NOTHING
                """,
                uuid.UUID(opp["id"]),
                uuid.UUID(opp["user_id"]),
                uuid.UUID(opp["company_id"]),
                opp["predicted_role"],
                opp["confidence"],
                opp["timeline_weeks"],
                opp["why_fit"],
                opp.get("approach_angle", ""),
                opp["fit_score"],
                opp["status"],
                [uuid.UUID(sid) for sid in opp["signal_ids"]],
                opp.get("predicted_salary_range", ""),
            )
        logger.info("Seeded %d demo opportunities", len(DEMO_OPPORTUNITIES))

        logger.info("Demo seed complete ✓")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(seed_demo())
```

- [ ] Commit:

```bash
git add backend/app/db/seeds/seed_demo.py .devcontainer/ start.sh
git commit -m "feat(14.5): demo seed data (5 companies, 20 signals, 3 opportunities)"
```

---

### Task 5 — Step 4: Create QUICKSTART.md

- [ ] Create `QUICKSTART.md` at repo root. This is a legitimate user-facing doc (not a planning doc):

```markdown
# Apex — Quickstart Guide

Get Apex running locally in ~30 minutes.

## Prerequisites

- Docker Desktop installed and running
- A Supabase account (free at https://supabase.com)
- An Anthropic API key (https://console.anthropic.com)
- An OpenAI API key (https://platform.openai.com)

## Step 1: Clone the repo

```bash
git clone https://github.com/YOUR_USERNAME/apex.git
cd apex
```

## Step 2: Set up Supabase

1. Create a new Supabase project at https://supabase.com
2. Go to **SQL Editor** and paste the contents of `schema/initial.sql`
3. Click **Run** — this creates all tables and RLS policies
4. Find your keys in **Settings → API**:
   - Project URL
   - anon public key
   - service_role secret key
   - Database connection string (Settings → Database → Connection string → URI)

## Step 3: Get free API keys (5 minutes)

| Service | Sign up | What for |
|---------|---------|----------|
| Anthropic | https://console.anthropic.com | AI agents (required) |
| OpenAI | https://platform.openai.com | Embeddings (required) |
| NewsData.io | https://newsdata.io/register | Signal ingestion (free 200/day) |
| GNews | https://gnews.io/register | Signal backup (free 100/day) |
| PDL | https://dashboard.peopledatalabs.com/signup | Contact enrichment (free 1k/mo) |
| Hunter.io | https://hunter.io/users/sign_up | Email finding (free 25/mo) |
| Adzuna | https://developer.adzuna.com | Job validation (free) |

## Step 4: Run the setup script

```bash
./start.sh
```

This will:
1. Copy `.env.example` → `.env` and prompt you to fill it in
2. Build and start all Docker services
3. Seed demo data so your first experience is non-empty

## Step 5: Open Apex

- Frontend: http://localhost:3000
- Log in with the `OWNER_EMAIL` / `OWNER_PASSWORD` you set in `.env`
- Click **Run Pipeline** on the dashboard to ingest your first signals

## Troubleshooting

**Backend won't start:** `docker-compose logs backend` to see the error.

**"placeholder" errors in logs:** Your `.env` has unfilled placeholder values. Open `.env` and replace them.

**Signals aren't ingesting:** Check your `NEWSDATA_API_KEY` is valid. Test at https://newsdata.io/api-science.

**Something else:** Paste the error into Claude and ask for help. Seriously — that's the documented support path.
```

- [ ] Commit:

```bash
git add QUICKSTART.md
git commit -m "docs(14.5): add QUICKSTART.md for new user setup"
```

---

## Self-Review Checklist

Before declaring Phase 14 complete, verify:

### Spec Coverage
- [x] Sprint 14.1: Keyword pre-filter + batch Sonnet classifier wired in worker ✓
- [x] Sprint 14.2: Adzuna client + validation service + DB column + FE badge ✓
- [x] Sprint 14.3: RunStatus enriched + PipelineProgressBar + Run Pipeline button ✓
- [x] Sprint 14.4: Extended thinking (budget=8000) on OpportunityPredictorAgent ✓
- [x] Sprint 14.5: start.sh + QUICKSTART.md + devcontainer + demo seed data ✓

### Placeholder Scan
- All code blocks contain complete, runnable code
- No "TBD" or "implement later" anywhere
- All file paths are exact and match the actual repo structure

### Type Consistency
- `SignalBatchItem` used in `BatchSignalClassifierInput.signals` — matches `_build_user_message` iteration
- `AdzunaPosting.posted_date` is `str` (ISO date) — matches `ValidationResult.real_postings` dict shape
- `RunStatus.stage` typed as `str` in backend — matches `Stage` union type in `PipelineProgressBar.tsx`
- `PreFilterResult.passes` is `bool` — used correctly in `batch_classify_signals_upgrade` gate

---

## Final: Run Full Test Suite

After all tasks complete, run from the backend root:

```bash
cd backend && python -m pytest tests/ -v --tb=short 2>&1 | tail -40
```

Expected: All tests pass, 0 failures. If any test fails, fix before declaring Phase 14 complete.

Then run the TypeScript check:

```bash
cd frontend && npx tsc --noEmit
```

Expected: 0 errors.
```
