"""
OutreachEmail ORM model + Pydantic v2 schemas.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Text, DateTime, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

from pydantic import BaseModel, ConfigDict, Field


# ── SQLAlchemy ORM ─────────────────────────────────────────────────────────────

class OutreachEmailORM(Base):
    """ORM model for the `outreach_emails` table."""
    __tablename__ = "outreach_emails"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    action_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    contact_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    subject: Mapped[str | None] = mapped_column(Text, nullable=True)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    tone: Mapped[str | None] = mapped_column(Text, nullable=True)
    draft_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    gmail_message_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    opened_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    replied_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    reply_detected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


# ── Pydantic v2 Schemas ────────────────────────────────────────────────────────

class OutreachEmailCreate(BaseModel):
    """Request schema for creating an outreach email draft."""
    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    action_id: uuid.UUID | None = None
    contact_id: uuid.UUID | None = None
    subject: str | None = None
    body: str | None = None
    tone: str | None = None
    draft_json: dict[str, Any] = Field(default_factory=dict)


class OutreachEmailRead(BaseModel):
    """Response schema for reading an outreach email."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    action_id: uuid.UUID | None
    contact_id: uuid.UUID | None
    subject: str | None
    body: str | None
    tone: str | None
    draft_json: dict[str, Any]
    sent_at: datetime | None
    gmail_message_id: str | None
    opened_at: datetime | None
    replied_at: datetime | None
    reply_detected_at: datetime | None
    created_at: datetime


class OutreachEmailUpdate(BaseModel):
    """Request schema for partial outreach email updates."""
    model_config = ConfigDict(from_attributes=True)

    subject: str | None = None
    body: str | None = None
    tone: str | None = None
    draft_json: dict[str, Any] | None = None
    sent_at: datetime | None = None
    gmail_message_id: str | None = None
    opened_at: datetime | None = None
    replied_at: datetime | None = None
    reply_detected_at: datetime | None = None
