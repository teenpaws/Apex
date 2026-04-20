"""
Coverage gap-fill for Celery workers.

Strategy:
  1. Test all helper/utility functions directly.
  2. Test Celery task bodies by setting task_always_eager=True on the celery_app
     so tasks run inline without a broker.
  3. Test async inner functions (_persist_events, etc.) directly via pytest-asyncio.

Tests run with USE_MOCK_DATA=true and MOCK_AGENTS=true (set in conftest.py).
"""
from __future__ import annotations

import asyncio
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch


# ── Shared setup fixture ─────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def celery_eager(monkeypatch):
    """Force all Celery tasks to run synchronously (no broker needed)."""
    from app.core.celery_app import celery_app
    celery_app.conf.update(task_always_eager=True)
    yield
    celery_app.conf.update(task_always_eager=False)


# ── ingest_signals helpers ───────────────────────────────────────────────────

class TestIngestSignalsHelpers:
    """Tests for helper functions in app.workers.ingest_signals."""

    def test_make_dedup_hash_is_deterministic(self):
        from app.workers.ingest_signals import _make_dedup_hash
        dt = datetime(2026, 4, 10, 12, 0, 0, tzinfo=timezone.utc)
        h1 = _make_dedup_hash("newsdata", "ext-001", dt)
        h2 = _make_dedup_hash("newsdata", "ext-001", dt)
        assert h1 == h2

    def test_make_dedup_hash_is_sha256_length(self):
        from app.workers.ingest_signals import _make_dedup_hash
        dt = datetime(2026, 4, 10, tzinfo=timezone.utc)
        h = _make_dedup_hash("gnews", "article-001", dt)
        assert len(h) == 64  # SHA-256 hex = 64 chars

    def test_make_dedup_hash_different_sources_different_hashes(self):
        from app.workers.ingest_signals import _make_dedup_hash
        dt = datetime(2026, 4, 10, tzinfo=timezone.utc)
        h1 = _make_dedup_hash("newsdata", "ext-001", dt)
        h2 = _make_dedup_hash("gnews", "ext-001", dt)
        assert h1 != h2

    def test_make_dedup_hash_different_dates_different_hashes(self):
        from app.workers.ingest_signals import _make_dedup_hash
        dt1 = datetime(2026, 4, 10, tzinfo=timezone.utc)
        dt2 = datetime(2026, 4, 11, tzinfo=timezone.utc)
        h1 = _make_dedup_hash("newsdata", "ext-001", dt1)
        h2 = _make_dedup_hash("newsdata", "ext-001", dt2)
        assert h1 != h2

    def test_make_dedup_hash_same_day_different_times_equal(self):
        """Same day but different times → same hash (date-only dedup)."""
        from app.workers.ingest_signals import _make_dedup_hash
        dt_morning = datetime(2026, 4, 10, 9, 0, 0, tzinfo=timezone.utc)
        dt_evening = datetime(2026, 4, 10, 18, 0, 0, tzinfo=timezone.utc)
        h1 = _make_dedup_hash("newsdata", "ext-001", dt_morning)
        h2 = _make_dedup_hash("newsdata", "ext-001", dt_evening)
        assert h1 == h2

    def test_mock_ingest_result_returns_correct_count(self):
        from app.workers.ingest_signals import _mock_ingest_result
        mock_events = [
            MagicMock(source="newsdata", company_name="Acme", title=f"Article {i}")
            for i in range(5)
        ]
        result = _mock_ingest_result(mock_events)
        assert result == {"ingested": 5, "duplicates": 0, "errors": 0}

    def test_mock_ingest_result_empty_list(self):
        from app.workers.ingest_signals import _mock_ingest_result
        result = _mock_ingest_result([])
        assert result == {"ingested": 0, "duplicates": 0, "errors": 0}

    def test_resolve_company_uuid_valid_uuid(self):
        import uuid
        from app.workers.ingest_signals import _resolve_company_uuid
        valid_uuid = str(uuid.uuid4())
        result = _resolve_company_uuid(valid_uuid)
        assert result is not None
        assert isinstance(result, uuid.UUID)

    def test_resolve_company_uuid_invalid_returns_none(self):
        from app.workers.ingest_signals import _resolve_company_uuid
        result = _resolve_company_uuid("co-00000-0000-0000-000000000001")
        assert result is None

    def test_resolve_company_uuid_none_returns_none(self):
        from app.workers.ingest_signals import _resolve_company_uuid
        result = _resolve_company_uuid(None)
        assert result is None

    def test_resolve_company_uuid_empty_string_returns_none(self):
        from app.workers.ingest_signals import _resolve_company_uuid
        result = _resolve_company_uuid("")
        assert result is None

    @pytest.mark.asyncio
    async def test_persist_events_mock_mode_returns_ingested_count(self):
        from app.workers.ingest_signals import _persist_events
        mock_events = [
            MagicMock(source="newsdata", company_name="Acme", title="Test")
            for _ in range(3)
        ]
        result = await _persist_events(
            mock_events, "user-001", "company-001", use_mock=True
        )
        assert result["ingested"] == 3
        assert result["duplicates"] == 0
        assert result["errors"] == 0

    @pytest.mark.asyncio
    async def test_persist_events_empty_mock_mode(self):
        from app.workers.ingest_signals import _persist_events
        result = await _persist_events([], "user-001", None, use_mock=True)
        assert result == {"ingested": 0, "duplicates": 0, "errors": 0}


# ── classify_signals helpers ─────────────────────────────────────────────────

class TestClassifySignalsHelpers:
    """Tests for helper functions and async logic in app.workers.classify_signals."""

    def test_load_mock_signal_returns_expected_fields(self):
        from app.workers.classify_signals import _load_mock_signal
        signal = _load_mock_signal("test-signal-id")
        assert signal["id"] == "test-signal-id"
        assert "title" in signal
        assert "description" in signal
        assert "source" in signal
        assert "company_name" in signal
        assert "signal_date" in signal

    def test_load_mock_signal_has_target_arrays(self):
        from app.workers.classify_signals import _load_mock_signal
        signal = _load_mock_signal("sig-xyz")
        assert "user_target_industries" in signal
        assert "user_target_roles" in signal
        assert isinstance(signal["user_target_industries"], list)
        assert isinstance(signal["user_target_roles"], list)

    def test_mock_update_signal_does_not_raise(self):
        from app.workers.classify_signals import _mock_update_signal
        _mock_update_signal("test-signal-id", "FUNDING", 0.87)

    def test_mock_store_embedding_does_not_raise(self):
        from app.workers.classify_signals import _mock_store_embedding
        _mock_store_embedding("test-signal-id")


# ── classify_signals Celery tasks (eager mode) ───────────────────────────────

class TestClassifySignalsTasks:
    """Tests for Celery tasks in classify_signals using eager mode."""

    def test_classify_signal_returns_dict(self):
        from app.workers.classify_signals import classify_signal
        result = classify_signal("mock-user-id", "test-signal-id") if False else classify_signal.apply(args=["test-signal-id"]).get()
        assert isinstance(result, dict)

    def test_classify_signal_has_all_required_keys(self):
        from app.workers.classify_signals import classify_signal
        result = classify_signal.apply(args=["test-signal-id"]).get()
        assert "signal_id" in result
        assert "signal_type" in result
        assert "relevance_score" in result
        assert "gated_out" in result

    def test_classify_signal_returns_correct_signal_id(self):
        from app.workers.classify_signals import classify_signal
        result = classify_signal.apply(args=["my-test-signal"]).get()
        assert result["signal_id"] == "my-test-signal"

    def test_classify_signal_relevance_score_is_float(self):
        from app.workers.classify_signals import classify_signal
        result = classify_signal.apply(args=["test-signal-id"]).get()
        assert isinstance(result["relevance_score"], float)
        assert 0.0 <= result["relevance_score"] <= 1.0

    def test_classify_signal_gated_out_is_bool(self):
        from app.workers.classify_signals import classify_signal
        result = classify_signal.apply(args=["test-signal-id"]).get()
        assert isinstance(result["gated_out"], bool)

    def test_embed_signal_mock_returns_embedded_true(self):
        from app.workers.classify_signals import embed_signal
        result = embed_signal.apply(args=["test-signal-id"]).get()
        assert result.get("embedded") is True

    def test_embed_signal_returns_signal_id(self):
        from app.workers.classify_signals import embed_signal
        result = embed_signal.apply(args=["embed-me"]).get()
        assert result["signal_id"] == "embed-me"

    def test_batch_classify_empty_list_returns_zero(self):
        from app.workers.classify_signals import batch_classify_signals
        result = batch_classify_signals.apply(args=[[]]).get()
        assert result == {"queued": 0}

    def test_batch_classify_signals_multiple(self):
        from app.workers.classify_signals import batch_classify_signals
        result = batch_classify_signals.apply(args=[["sig-001", "sig-002", "sig-003"]]).get()
        assert result["queued"] == 3

    def test_classify_and_embed_runs_pipeline(self):
        from app.workers.classify_signals import classify_and_embed
        result = classify_and_embed.apply(args=["test-signal-id"]).get()
        assert isinstance(result, dict)
        # Either pipeline completed or signal was gated out
        assert "pipeline" in result or result.get("gated_out") is True


# ── predict_opportunities helpers ────────────────────────────────────────────

class TestPredictOpportunitiesHelpers:
    """Tests for helper functions in app.workers.predict_opportunities."""

    def test_load_mock_company_context_returns_dict(self):
        from app.workers.predict_opportunities import _load_mock_company_context
        ctx = _load_mock_company_context("user-001", "company-001")
        assert "company_name" in ctx
        assert "signals" in ctx
        assert "user_profile" in ctx

    def test_load_mock_company_context_has_signals_list(self):
        from app.workers.predict_opportunities import _load_mock_company_context
        ctx = _load_mock_company_context("user-001", "company-001")
        assert isinstance(ctx["signals"], list)
        assert len(ctx["signals"]) > 0

    def test_load_mock_company_context_signal_has_required_fields(self):
        from app.workers.predict_opportunities import _load_mock_company_context
        ctx = _load_mock_company_context("user-001", "company-001")
        signal = ctx["signals"][0]
        assert "signal_id" in signal
        assert "signal_type" in signal
        assert "title" in signal
        assert "description" in signal

    def test_load_mock_opportunity_returns_dict(self):
        from app.workers.predict_opportunities import _load_mock_opportunity
        opp = _load_mock_opportunity("opp-001", "user-001")
        assert "predicted_role" in opp
        assert "confidence" in opp
        assert "timeline_weeks" in opp

    def test_mock_store_opportunity_returns_string_id(self):
        from app.workers.predict_opportunities import _mock_store_opportunity
        result = _mock_store_opportunity("user-001", "company-001", {
            "predicted_role": "VP Strategy",
            "confidence": "HIGH",
        })
        assert isinstance(result, str)
        assert "company-0"[:8] in result

    def test_mock_update_opportunity_fit_does_not_raise(self):
        from app.workers.predict_opportunities import _mock_update_opportunity_fit
        _mock_update_opportunity_fit("opp-001", 82.5)

    def test_get_settings_returns_settings(self):
        from app.workers.predict_opportunities import _get_settings
        settings = _get_settings()
        assert settings is not None
        assert hasattr(settings, "USE_MOCK_DATA")


# ── predict_opportunities Celery tasks (eager mode) ──────────────────────────

class TestPredictOpportunitiesTasks:
    """Tests for Celery tasks in predict_opportunities using eager mode."""

    def test_predict_for_company_returns_dict(self):
        from app.workers.predict_opportunities import predict_for_company
        result = predict_for_company.apply(args=["mock-user-id", "mock-company-id"]).get()
        assert isinstance(result, dict)

    def test_predict_for_company_has_opportunity_id(self):
        from app.workers.predict_opportunities import predict_for_company
        result = predict_for_company.apply(args=["mock-user-id", "mock-company-id"]).get()
        assert "opportunity_id" in result

    def test_predict_for_company_has_predicted_role(self):
        from app.workers.predict_opportunities import predict_for_company
        result = predict_for_company.apply(args=["mock-user-id", "mock-company-id"]).get()
        assert "predicted_role" in result
        assert isinstance(result["predicted_role"], str)

    def test_predict_for_company_has_confidence(self):
        from app.workers.predict_opportunities import predict_for_company
        result = predict_for_company.apply(args=["mock-user-id", "mock-company-id"]).get()
        assert "confidence" in result
        assert result["confidence"] in ("HIGH", "MEDIUM", "SPECULATIVE")

    def test_score_opportunity_fit_returns_dict(self):
        from app.workers.predict_opportunities import score_opportunity_fit
        result = score_opportunity_fit.apply(args=["mock-user-id", "mock-opp-id"]).get()
        assert isinstance(result, dict)

    def test_score_opportunity_fit_has_fit_score(self):
        from app.workers.predict_opportunities import score_opportunity_fit
        result = score_opportunity_fit.apply(args=["mock-user-id", "mock-opp-id"]).get()
        assert "fit_score" in result
        score = result["fit_score"]
        assert isinstance(score, (int, float))
        assert 0 <= score <= 100


# ── generate_actions helpers ─────────────────────────────────────────────────

class TestGenerateActionsHelpers:
    """Tests for helper functions in app.workers.generate_actions."""

    def test_load_mock_opportunity_full_returns_context(self):
        from app.workers.generate_actions import _load_mock_opportunity_full
        ctx = _load_mock_opportunity_full("opp-001", "user-001")
        assert "opportunity" in ctx
        assert "fit_score" in ctx
        assert "user_profile" in ctx
        assert "contacts" in ctx

    def test_load_mock_opportunity_full_opportunity_has_role(self):
        from app.workers.generate_actions import _load_mock_opportunity_full
        ctx = _load_mock_opportunity_full("opp-001", "user-001")
        opp = ctx["opportunity"]
        assert "predicted_role" in opp
        assert "confidence" in opp
        assert "company_name" in opp

    def test_load_mock_opportunity_full_fit_score_is_float(self):
        from app.workers.generate_actions import _load_mock_opportunity_full
        ctx = _load_mock_opportunity_full("opp-001", "user-001")
        assert isinstance(ctx["fit_score"], float)
        assert 0 <= ctx["fit_score"] <= 100

    def test_load_mock_opportunity_full_contacts_is_list(self):
        from app.workers.generate_actions import _load_mock_opportunity_full
        ctx = _load_mock_opportunity_full("opp-001", "user-001")
        assert isinstance(ctx["contacts"], list)

    def test_load_mock_opportunity_full_user_profile_has_role(self):
        from app.workers.generate_actions import _load_mock_opportunity_full
        ctx = _load_mock_opportunity_full("opp-001", "user-001")
        assert "current_role" in ctx["user_profile"]
        assert "aspirations_text" in ctx["user_profile"]

    def test_mock_store_actions_does_not_raise(self):
        from app.workers.generate_actions import _mock_store_actions
        _mock_store_actions("user-001", "opp-001", [
            {"title": "Send email", "type": "OUTREACH", "priority": "HIGH", "due_date": "+5d"}
        ])

    def test_mock_store_positioning_does_not_raise(self):
        from app.workers.generate_actions import _mock_store_positioning
        _mock_store_positioning("opp-001", {"narrative": "Lead with HEC Paris background"})

    def test_get_settings_returns_settings(self):
        from app.workers.generate_actions import _get_settings
        settings = _get_settings()
        assert settings is not None


# ── generate_actions Celery tasks (eager mode) ───────────────────────────────

class TestGenerateActionsTasks:
    """Tests for Celery tasks in generate_actions using eager mode."""

    def test_generate_actions_for_opportunity_returns_dict(self):
        from app.workers.generate_actions import generate_actions_for_opportunity
        result = generate_actions_for_opportunity.apply(
            args=["mock-user-id", "mock-opp-id"]
        ).get()
        assert isinstance(result, dict)

    def test_generate_actions_has_opportunity_id(self):
        from app.workers.generate_actions import generate_actions_for_opportunity
        result = generate_actions_for_opportunity.apply(
            args=["mock-user-id", "specific-opp-123"]
        ).get()
        assert result["opportunity_id"] == "specific-opp-123"

    def test_generate_actions_has_actions_count(self):
        from app.workers.generate_actions import generate_actions_for_opportunity
        result = generate_actions_for_opportunity.apply(
            args=["mock-user-id", "mock-opp-id"]
        ).get()
        assert "actions_count" in result
        assert isinstance(result["actions_count"], int)
        assert result["actions_count"] >= 0

    def test_generate_actions_has_actions_list(self):
        from app.workers.generate_actions import generate_actions_for_opportunity
        result = generate_actions_for_opportunity.apply(
            args=["mock-user-id", "mock-opp-id"]
        ).get()
        assert "actions" in result
        assert isinstance(result["actions"], list)

    def test_generate_actions_count_matches_list_length(self):
        from app.workers.generate_actions import generate_actions_for_opportunity
        result = generate_actions_for_opportunity.apply(
            args=["mock-user-id", "mock-opp-id"]
        ).get()
        assert result["actions_count"] == len(result["actions"])

    def test_advise_positioning_returns_dict(self):
        from app.workers.generate_actions import advise_positioning
        result = advise_positioning.apply(
            args=["mock-user-id", "mock-opp-id"]
        ).get()
        assert isinstance(result, dict)

    def test_advise_positioning_has_opportunity_id(self):
        from app.workers.generate_actions import advise_positioning
        result = advise_positioning.apply(
            args=["mock-user-id", "specific-opp-999"]
        ).get()
        assert "opportunity_id" in result
        assert result["opportunity_id"] == "specific-opp-999"


# ── enrich_contacts helpers ──────────────────────────────────────────────────

class TestEnrichContactsHelpers:
    """Tests for helper functions in app.workers.enrich_contacts."""

    def test_load_mock_company_returns_dict(self):
        from app.workers.enrich_contacts import _load_mock_company
        company = _load_mock_company("company-001")
        assert "name" in company
        assert "domain" in company
        assert "industry" in company
        assert company["id"] == "company-001"

    def test_load_mock_contact_returns_dict(self):
        from app.workers.enrich_contacts import _load_mock_contact
        contact = _load_mock_contact("contact-001")
        assert "name" in contact
        assert "title" in contact
        assert "company_name" in contact
        assert contact["id"] == "contact-001"

    def test_mock_update_company_enrichment_does_not_raise(self):
        from app.workers.enrich_contacts import _mock_update_company_enrichment
        mock_profile = MagicMock(headcount=5000, industry="Consulting")
        _mock_update_company_enrichment("company-001", mock_profile)

    def test_mock_update_contact_enrichment_does_not_raise(self):
        from app.workers.enrich_contacts import _mock_update_contact_enrichment
        mock_profile = MagicMock(pdl_id="pdl-001")
        _mock_update_contact_enrichment("contact-001", mock_profile, "jane@mckinsey.com")

    def test_mock_create_contact_returns_id_string(self):
        from app.workers.enrich_contacts import _mock_create_contact
        mock_result = MagicMock(
            pdl_id="pdl-xyz-001",
            full_name="Jane Smith",
            job_title="Chief of Staff",
        )
        result = _mock_create_contact("company-abc-001", mock_result, "jane@mckinsey.com")
        assert isinstance(result, str)
        assert result.startswith("contact-mock-")

    def test_get_settings_returns_settings(self):
        from app.workers.enrich_contacts import _get_settings
        settings = _get_settings()
        assert settings is not None
        assert hasattr(settings, "USE_MOCK_DATA")


# ── enrich_contacts Celery tasks (eager mode) ────────────────────────────────

class TestEnrichContactsTasks:
    """Tests for Celery tasks in enrich_contacts using eager mode."""

    def test_enrich_company_mock_returns_dict(self):
        from app.workers.enrich_contacts import enrich_company
        result = enrich_company.apply(args=["mock-company-id"]).get()
        assert isinstance(result, dict)

    def test_enrich_company_has_company_id(self):
        from app.workers.enrich_contacts import enrich_company
        result = enrich_company.apply(args=["test-company-id"]).get()
        assert result.get("company_id") == "test-company-id"

    def test_enrich_company_has_enriched_flag(self):
        from app.workers.enrich_contacts import enrich_company
        result = enrich_company.apply(args=["mock-company-id"]).get()
        assert "enriched" in result
        assert isinstance(result["enriched"], bool)

    def test_enrich_contact_mock_returns_dict(self):
        from app.workers.enrich_contacts import enrich_contact
        result = enrich_contact.apply(args=["mock-contact-id"]).get()
        assert isinstance(result, dict)

    def test_enrich_contact_has_contact_id(self):
        from app.workers.enrich_contacts import enrich_contact
        result = enrich_contact.apply(args=["test-contact-id"]).get()
        assert "contact_id" in result
        assert result["contact_id"] == "test-contact-id"

    def test_enrich_contact_has_enriched_flag(self):
        from app.workers.enrich_contacts import enrich_contact
        result = enrich_contact.apply(args=["mock-contact-id"]).get()
        assert "enriched" in result

    def test_batch_enrich_empty_returns_zero(self):
        from app.workers.enrich_contacts import batch_enrich
        result = batch_enrich.apply(args=[[]]).get()
        assert result.get("queued", 0) == 0

    def test_find_key_contact_strategy_returns_dict(self):
        from app.workers.enrich_contacts import find_key_contact
        result = find_key_contact.apply(args=["mock-company-id", "strategy"]).get()
        assert isinstance(result, dict)
        assert "contact_id" in result
        assert "full_name" in result
        assert "job_title" in result

    def test_find_key_contact_operations_role(self):
        from app.workers.enrich_contacts import find_key_contact
        result = find_key_contact.apply(args=["mock-company-id", "operations"]).get()
        assert isinstance(result, dict)

    def test_find_key_contact_unknown_role_uses_default(self):
        from app.workers.enrich_contacts import find_key_contact
        result = find_key_contact.apply(args=["mock-company-id", "unknown-role"]).get()
        assert isinstance(result, dict)

    def test_find_key_contact_hr_role(self):
        from app.workers.enrich_contacts import find_key_contact
        result = find_key_contact.apply(args=["mock-company-id", "hr"]).get()
        assert isinstance(result, dict)
