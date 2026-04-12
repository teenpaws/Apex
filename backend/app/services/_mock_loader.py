"""
Utility for loading mock JSON response fixtures from the mock_responses directory.

Usage:
    from app.services._mock_loader import load_mock
    data = load_mock("signals.json")
"""

import json
from pathlib import Path

_BASE = Path(__file__).parent.parent / "api" / "mock_responses"


def load_mock(filename: str) -> dict:
    """Load and return a mock JSON fixture by filename."""
    with open(_BASE / filename) as f:
        return json.load(f)
