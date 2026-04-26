"""
Unit tests for extract_profile Celery worker.

Tests cover (mock mode only):
  - Task is importable and callable
  - Task runs without raising in mock mode
  - Task returns a result dict with 'status' == 'SUCCESS'
"""
from __future__ import annotations
import pytest

_MODULE = "app.workers.extract_profile"


class TestExtractProfileWorker:

    @pytest.fixture(autouse=True)
    def _import(self):
        pytest.importorskip(_MODULE)

    def test_task_is_importable(self):
        from app.workers.extract_profile import extract_profile_from_documents
        assert callable(extract_profile_from_documents)

    def test_task_runs_in_mock_mode(self):
        from app.workers.extract_profile import extract_profile_from_documents
        result = extract_profile_from_documents("user-001")
        assert isinstance(result, dict)
        assert "status" in result

    def test_task_returns_success_in_mock_mode(self):
        from app.workers.extract_profile import extract_profile_from_documents
        result = extract_profile_from_documents("user-001")
        assert result["status"] == "SUCCESS"
