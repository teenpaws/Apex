"""
Action ORM model + Pydantic v2 schemas.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Text, DateTime, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import ActionType, Priority, ActionStatus

from pydantic import BaseModel, ConfigDict, Field


# ── SQLAlchemy ORM ─────────────────────────────────────────────────────────────

class ActionORM(Base):
    """ORM model for the `actions` table."""
    __tablename__ = "actions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    opportunity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    contact_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    type: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(
        Text, nullable=False, default=Priority.MEDIUM.value
    )
    status: Mapped[str] = mapped_column(
        Text, nullable=False, default=ActionStatus.TODO.value
    )
    due_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    source_signal_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    ai_draft_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


# ── Pydantic v2 Schemas ────────────────────────────────────────────────────────

class ActionCreate(BaseModel):
    """Request schema for creating an action."""
    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    opportunity_id: uuid.UUID | None = None
    company_id: uuid.UUID | None = None
    contact_id: uuid.UUID | None = None
    title: str
    description: str | None = None
    type: ActionType
    priority: Priority = Priority.MEDIUM
    status: ActionStatus = ActionStatus.TODO
    due_date: datetime | None = None
    source_signal_id: uuid.UUID | None = None
    ai_draft_json: dict[str, Any] = Field(default_factory=dict)


class ActionRead(BaseModel):
    """Response schema for reading an action."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    opportunity_id: uuid.UUID | None
    company_id: uuid.UUID | None
    contact_id: uuid.UUID | None
    title: str
    description: str | None
    type: ActionType
    priority: Priority
    status: ActionStatus
    due_date: datetime | None
    source_signal_id: uuid.UUID | None
    ai_draft_json: dict[str, Any]
    created_at: datetime


class ActionUpdate(BaseModel):
    """Request schema for partial action updates."""
    model_config = ConfigDict(from_attributes=True)

    title: str | None = None
    description: str | None = None
    priority: Priority | None = None
    status: ActionStatus | None = None
    due_date: datetime | None = None
    ai_draft_json: dict[str, Any] | None = None
