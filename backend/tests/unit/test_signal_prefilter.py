"""Unit tests for SignalPreFilter — keyword-based signal relevance pre-screening."""
import pytest
from app.services.signal_prefilter import SignalPreFilter, PreFilterResult


def test_passes_signal_matching_industry():
    pf = SignalPreFilter(
        target_industries=["Fintech", "SaaS", "Consulting"],
        target_roles=["Strategy", "Operations"],
        tracked_companies=["Stripe"],
    )
    result = pf.screen(
        title="Stripe Raises $1B Series H",
        description="Fintech giant Stripe closes massive round to expand globally.",
        company_name="Stripe",
    )
    assert result.passes is True
    assert result.matched_keywords != []


def test_fails_signal_with_no_match():
    pf = SignalPreFilter(
        target_industries=["Fintech"],
        target_roles=["Strategy"],
        tracked_companies=[],
    )
    result = pf.screen(
        title="Local Bakery Opens New Branch",
        description="A family-run bakery in rural Iowa opens its fifth location.",
        company_name="Joe's Bakery",
    )
    assert result.passes is False
    assert result.relevance_score == 0.05


def test_passes_signal_matching_tracked_company():
    pf = SignalPreFilter(
        target_industries=["Fintech"],
        target_roles=["Strategy"],
        tracked_companies=["Sequoia"],
    )
    result = pf.screen(
        title="Sequoia Partners With New Fund",
        description="General market announcement about investment activities.",
        company_name="Sequoia",
    )
    assert result.passes is True


def test_case_insensitive_matching():
    pf = SignalPreFilter(
        target_industries=["Fintech", "SaaS"],
        target_roles=["Strategy"],
        tracked_companies=[],
    )
    result = pf.screen(
        title="FINTECH startup expands",
        description="saas company raises round",
        company_name="Unknown Co",
    )
    assert result.passes is True


def test_matched_keywords_listed():
    pf = SignalPreFilter(
        target_industries=["Consulting"],
        target_roles=["Strategy"],
        tracked_companies=[],
    )
    result = pf.screen(
        title="Consulting firm hires 200 strategy leads",
        description="McKinsey opens operations division.",
        company_name="McKinsey",
    )
    assert len(result.matched_keywords) > 0


def test_empty_profile_passes_nothing():
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
