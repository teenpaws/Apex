"""Integration tests: pre-filter → batch classify pipeline logic."""
import pytest
from app.services.signal_prefilter import SignalPreFilter


def test_prefilter_skips_irrelevant_signals():
    pf = SignalPreFilter(target_industries=["Fintech"], target_roles=["Strategy"], tracked_companies=[])
    result = pf.screen(title="Weather update: storms in midwest", description="National weather service issues advisory.", company_name="NWS")
    assert result.passes is False
    assert result.relevance_score == 0.05


def test_prefilter_passes_relevant_signals():
    pf = SignalPreFilter(target_industries=["Fintech"], target_roles=["Strategy"], tracked_companies=[])
    result = pf.screen(title="Fintech startup raises Series B", description="Company plans to expand strategy team.", company_name="PayCo")
    assert result.passes is True


def test_batch_size_chunking():
    signals = [{"id": str(i)} for i in range(25)]
    batch_size = 10
    chunks = [signals[i:i + batch_size] for i in range(0, len(signals), batch_size)]
    assert len(chunks) == 3
    assert len(chunks[0]) == 10
    assert len(chunks[1]) == 10
    assert len(chunks[2]) == 5
