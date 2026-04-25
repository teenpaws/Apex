"""Unit tests for pipeline_progress.report_stage."""
import json
import pytest
from unittest.mock import patch, MagicMock

from app.workers.pipeline_progress import report_stage, STAGE_ORDER, STAGE_WEIGHTS


def test_report_stage_calculates_overall_progress():
    """CLASSIFY at 50% completion should yield ~22% overall (5% INGEST done + 20% of 40%)."""
    with patch("app.workers.pipeline_progress.redis") as mock_redis_mod:
        mock_r = MagicMock()
        mock_redis_mod.from_url.return_value = mock_r
        report_stage(run_id="test-run", stage="CLASSIFY", status="RUNNING", completed=5, total=10, redis_url="redis://localhost")
        mock_r.set.assert_called_once()
        call_args = mock_r.set.call_args
        data = json.loads(call_args[0][1])
        assert data["stage"] == "CLASSIFY"
        assert data["status"] == "RUNNING"
        assert data["progress"] == 25  # 5 (INGEST weight) + 50% of 40 = 25


def test_report_stage_done_sets_100():
    with patch("app.workers.pipeline_progress.redis") as mock_redis_mod:
        mock_r = MagicMock()
        mock_redis_mod.from_url.return_value = mock_r
        report_stage(run_id="test-run", stage="DONE", status="SUCCESS", completed=100, total=100, redis_url="redis://localhost")
        data = json.loads(mock_r.set.call_args[0][1])
        assert data["progress"] == 100
        assert data["status"] == "SUCCESS"


def test_report_stage_silent_on_redis_failure():
    """Redis failures must never raise — workers must continue."""
    with patch("app.workers.pipeline_progress.redis") as mock_redis_mod:
        mock_redis_mod.from_url.side_effect = Exception("Redis unavailable")
        # Should not raise
        report_stage(run_id="test-run", stage="INGEST", status="RUNNING", completed=1, total=10, redis_url="redis://localhost")
