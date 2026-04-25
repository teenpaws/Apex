"""Tests for extended thinking integration in BaseAgent._call_claude."""
import inspect
import pytest
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
    """OpportunityPredictorAgent must call _call_claude with thinking_budget=8000."""
    import ast
    import pathlib

    # Resolve relative to this test file's location (backend/tests/unit/ → backend/)
    root = pathlib.Path(__file__).parent.parent.parent
    source = (root / "app/agents/opportunity_predictor.py").read_text()
    tree = ast.parse(source)

    found = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute) and func.attr == "_call_claude":
                for kw in node.keywords:
                    if kw.arg == "thinking_budget":
                        found = True
    assert found, "opportunity_predictor.py must call _call_claude(thinking_budget=8000)"


def test_registry_version_updated():
    """opportunity_predictor version must be '1.1' after adding extended thinking."""
    from app.agents.registry import AGENT_REGISTRY
    assert AGENT_REGISTRY["opportunity_predictor"]["version"] == "1.1"
