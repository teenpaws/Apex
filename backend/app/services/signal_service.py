"""
SignalService — business logic for market intelligence signals.

In mock mode (use_mock=True): serves data from mock_responses/signals.json.
In live mode (use_mock=False): queries Supabase via SQLAlchemy (stubbed for Phase 2).
"""

from __future__ import annotations

from uuid import uuid4

from app.core.errors import ApexHTTPException
from app.services._mock_loader import load_mock


class SignalService:
    """Service layer for signal read and ingest operations."""

    def __init__(self, user_id: str, use_mock: bool = False) -> None:
        self.user_id = user_id
        self.use_mock = use_mock

    async def list_signals(
        self,
        page: int = 1,
        page_size: int = 20,
        signal_type: str | None = None,
        company_id: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> dict:
        """
        Return a paginated list of signals for the current user.

        Filters (signal_type, company_id) are applied in Python on mock data.
        date_from / date_to are accepted but not yet applied in mock mode.
        """
        if self.use_mock:
            return self._list_signals_mock(
                page=page,
                page_size=page_size,
                signal_type=signal_type,
                company_id=company_id,
            )
        raise NotImplementedError("Live DB not yet wired")

    def _list_signals_mock(
        self,
        page: int,
        page_size: int,
        signal_type: str | None,
        company_id: str | None,
    ) -> dict:
        data = load_mock("signals.json")
        signals: list[dict] = data["signals"]

        # Filter: only return signals belonging to this user (mock user is always mock-user-id)
        signals = [s for s in signals if s.get("user_id") == self.user_id or self.user_id == "mock-user-id"]

        if signal_type is not None:
            signals = [s for s in signals if s.get("type") == signal_type.upper()]

        if company_id is not None:
            signals = [s for s in signals if s.get("company_id") == company_id]

        total = len(signals)
        start = (page - 1) * page_size
        end = start + page_size
        page_signals = signals[start:end]

        return {
            "signals": page_signals,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def get_signal(self, signal_id: str) -> dict:
        """Return a single signal by ID."""
        if self.use_mock:
            return self._get_signal_mock(signal_id)
        raise NotImplementedError("Live DB not yet wired")

    def _get_signal_mock(self, signal_id: str) -> dict:
        data = load_mock("signals.json")
        for signal in data["signals"]:
            if signal["id"] == signal_id:
                return signal
        raise ApexHTTPException(404, "Signal not found", code="NOT_FOUND")

    async def trigger_ingest(self, source: str | None = None) -> dict:
        """
        Enqueue a signal ingestion run.

        Returns a run_id immediately. Real Celery task wired in Phase 3.
        """
        return {
            "run_id": str(uuid4()),
            "status": "queued",
            "message": "Signal ingestion queued",
        }
