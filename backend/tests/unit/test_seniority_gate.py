"""
Unit tests for SeniorityGate utility.
"""
from __future__ import annotations
import pytest

_MODULE = "app.services.seniority_gate"


class TestSeniorityBandDetection:

    @pytest.fixture(autouse=True)
    def _import(self):
        pytest.importorskip(_MODULE)

    def test_analyst_title(self):
        from app.services.seniority_gate import SeniorityGate
        assert SeniorityGate.detect_band("Junior Analyst") == "ANALYST"

    def test_associate_title(self):
        from app.services.seniority_gate import SeniorityGate
        assert SeniorityGate.detect_band("Strategy Consultant") == "ASSOCIATE"

    def test_manager_title(self):
        from app.services.seniority_gate import SeniorityGate
        assert SeniorityGate.detect_band("Senior Manager, Operations") == "MANAGER"

    def test_director_title(self):
        from app.services.seniority_gate import SeniorityGate
        assert SeniorityGate.detect_band("Director of Strategy") == "DIRECTOR"

    def test_vp_title(self):
        from app.services.seniority_gate import SeniorityGate
        assert SeniorityGate.detect_band("Vice President, Corporate Development") == "VP_PLUS"

    def test_ceo_title(self):
        from app.services.seniority_gate import SeniorityGate
        assert SeniorityGate.detect_band("Chief Executive Officer") == "VP_PLUS"

    def test_unknown_title_defaults_to_associate(self):
        from app.services.seniority_gate import SeniorityGate
        assert SeniorityGate.detect_band("Unicorn Wrangler") == "ASSOCIATE"


class TestSeniorityGateApply:

    @pytest.fixture(autouse=True)
    def _import(self):
        pytest.importorskip(_MODULE)

    def test_two_bands_above_downgraded_to_speculative(self):
        from app.services.seniority_gate import SeniorityGate
        result = SeniorityGate.apply(
            user_band="ANALYST",
            predicted_role="Chief Strategy Officer",
            original_confidence="HIGH",
        )
        assert result["gated_confidence"] == "SPECULATIVE"
        assert result["was_downgraded"] is True

    def test_one_band_above_unchanged(self):
        from app.services.seniority_gate import SeniorityGate
        result = SeniorityGate.apply(
            user_band="ASSOCIATE",
            predicted_role="Senior Manager",
            original_confidence="HIGH",
        )
        assert result["gated_confidence"] == "HIGH"
        assert result["was_downgraded"] is False

    def test_same_band_unchanged(self):
        from app.services.seniority_gate import SeniorityGate
        result = SeniorityGate.apply(
            user_band="MANAGER",
            predicted_role="Manager, Digital Strategy",
            original_confidence="MEDIUM",
        )
        assert result["gated_confidence"] == "MEDIUM"
        assert result["was_downgraded"] is False

    def test_no_user_band_unchanged(self):
        from app.services.seniority_gate import SeniorityGate
        result = SeniorityGate.apply(
            user_band=None,
            predicted_role="VP Strategy",
            original_confidence="HIGH",
        )
        assert result["gated_confidence"] == "HIGH"
        assert result["was_downgraded"] is False
