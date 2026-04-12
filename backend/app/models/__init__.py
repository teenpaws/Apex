"""
Apex models package — exports all ORM classes and Pydantic schemas.

Import from here for consistency:
    from app.models import UserORM, UserCreate, UserRead, SignalType
"""
from __future__ import annotations

# ── Shared base ───────────────────────────────────────────────────────────────
from app.models.base import Base

# ── Enums ─────────────────────────────────────────────────────────────────────
from app.models.enums import (
    SignalType,
    Confidence,
    OpportunityStatus,
    ActionType,
    Priority,
    ActionStatus,
    AgentRunStatus,
)

# ── User + CareerProfile ──────────────────────────────────────────────────────
from app.models.user import (
    UserORM,
    UserCreate,
    UserRead,
    UserUpdate,
    CareerProfileORM,
    CareerProfileCreate,
    CareerProfileRead,
    CareerProfileUpdate,
)

# ── Company + Contact ─────────────────────────────────────────────────────────
from app.models.company import (
    CompanyORM,
    CompanyCreate,
    CompanyRead,
    CompanyUpdate,
    ContactORM,
    ContactCreate,
    ContactRead,
    ContactUpdate,
)

# ── Signal ────────────────────────────────────────────────────────────────────
from app.models.signal import (
    SignalORM,
    SignalCreate,
    SignalRead,
    SignalUpdate,
)

# ── Opportunity ───────────────────────────────────────────────────────────────
from app.models.opportunity import (
    OpportunityORM,
    OpportunityCreate,
    OpportunityRead,
    OpportunityUpdate,
)

# ── Action ────────────────────────────────────────────────────────────────────
from app.models.action import (
    ActionORM,
    ActionCreate,
    ActionRead,
    ActionUpdate,
)

# ── OutreachEmail ─────────────────────────────────────────────────────────────
from app.models.outreach import (
    OutreachEmailORM,
    OutreachEmailCreate,
    OutreachEmailRead,
    OutreachEmailUpdate,
)

# ── AgentRun ──────────────────────────────────────────────────────────────────
from app.models.agent_run import (
    AgentRunORM,
    AgentRunCreate,
    AgentRunRead,
)

__all__ = [
    # Base
    "Base",
    # Enums
    "SignalType",
    "Confidence",
    "OpportunityStatus",
    "ActionType",
    "Priority",
    "ActionStatus",
    "AgentRunStatus",
    # User
    "UserORM", "UserCreate", "UserRead", "UserUpdate",
    # CareerProfile
    "CareerProfileORM", "CareerProfileCreate", "CareerProfileRead", "CareerProfileUpdate",
    # Company
    "CompanyORM", "CompanyCreate", "CompanyRead", "CompanyUpdate",
    # Contact
    "ContactORM", "ContactCreate", "ContactRead", "ContactUpdate",
    # Signal
    "SignalORM", "SignalCreate", "SignalRead", "SignalUpdate",
    # Opportunity
    "OpportunityORM", "OpportunityCreate", "OpportunityRead", "OpportunityUpdate",
    # Action
    "ActionORM", "ActionCreate", "ActionRead", "ActionUpdate",
    # OutreachEmail
    "OutreachEmailORM", "OutreachEmailCreate", "OutreachEmailRead", "OutreachEmailUpdate",
    # AgentRun
    "AgentRunORM", "AgentRunCreate", "AgentRunRead",
]
