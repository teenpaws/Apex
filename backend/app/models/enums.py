"""
Apex platform enumerations.

All database text columns that use a constrained value set are represented here
as Python enums. These are used in both SQLAlchemy ORM models and Pydantic schemas.
"""

from __future__ import annotations

import enum


class SignalType(str, enum.Enum):
    """Market signal categories — matches the `signals.type` column."""
    FUNDING = "FUNDING"
    EXEC_HIRE = "EXEC_HIRE"
    EXPANSION = "EXPANSION"
    LAYOFF = "LAYOFF"
    JOB_POSTING_PATTERN = "JOB_POSTING_PATTERN"
    MA = "MA"
    CONTRACT = "CONTRACT"
    EARNINGS = "EARNINGS"


class Confidence(str, enum.Enum):
    """Opportunity confidence band — matches the `opportunities.confidence` column."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    SPECULATIVE = "SPECULATIVE"


class OpportunityStatus(str, enum.Enum):
    """Opportunity lifecycle status — matches the `opportunities.status` column."""
    PREDICTED = "PREDICTED"
    APPROACHED = "APPROACHED"
    INTERVIEWING = "INTERVIEWING"
    CLOSED = "CLOSED"


class ActionType(str, enum.Enum):
    """Action category — matches the `actions.type` column."""
    OUTREACH = "OUTREACH"
    FOLLOW_UP = "FOLLOW_UP"
    RESEARCH = "RESEARCH"
    CALL = "CALL"


class Priority(str, enum.Enum):
    """Action priority band — matches the `actions.priority` column."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ActionStatus(str, enum.Enum):
    """Action lifecycle status — matches the `actions.status` column."""
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"
    SNOOZED = "SNOOZED"


class AgentRunStatus(str, enum.Enum):
    """AI agent invocation status — matches the `agent_runs.status` column."""
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    RETRIED = "RETRIED"
