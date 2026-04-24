"""
Apex Agent Registry — single source of truth for all agent configurations.

Every Claude-powered agent in the platform is declared here.
Never hardcode model names in agent implementations — always read from this registry.

Usage:
    from app.agents.registry import AGENT_REGISTRY
    config = AGENT_REGISTRY["signal_classifier"]
    model  = config["model"]
"""

from typing import TypedDict


class AgentConfig(TypedDict):
    model: str
    version: str
    prompt_file: str


AGENT_REGISTRY: dict[str, AgentConfig] = {
    "signal_classifier": {
        "model": "claude-haiku-4-5-20251001",
        "version": "1.0",
        "prompt_file": "prompts/signal_classifier_v1.txt",
    },
    "opportunity_predictor": {
        "model": "claude-sonnet-4-6",
        "version": "1.0",
        "prompt_file": "prompts/opportunity_predictor_v1.txt",
    },
    "career_fit_scorer": {
        "model": "claude-sonnet-4-6",
        "version": "1.0",
        "prompt_file": "prompts/career_fit_scorer_v1.txt",
    },
    "positioning_advisor": {
        "model": "claude-sonnet-4-6",
        "version": "1.0",
        "prompt_file": "prompts/positioning_advisor_v1.txt",
    },
    "email_drafter": {
        "model": "claude-sonnet-4-6",
        "version": "1.0",
        "prompt_file": "prompts/email_drafter_v1.txt",
    },
    "action_generator": {
        "model": "claude-haiku-4-5-20251001",
        "version": "1.0",
        "prompt_file": "prompts/action_generator_v1.txt",
    },
    "batch_signal_classifier": {
        "model": "claude-sonnet-4-6",
        "version": "1.0",
        "prompt_file": "prompts/batch_signal_classifier_v1.txt",
    },
}
