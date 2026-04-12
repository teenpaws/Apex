"""
Signal ORM model + Pydantic v2 schemas.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Text, Float, Boolean, DateTime, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import SignalType

# pgvector import — optional until the package is installed
try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    Vector = None  # type: ignore[assignment]

from pydantic import BaseModel, ConfigDict, Field


# ── SQLAlchemy ORM ─────────────────────────────────────────────────────────────

class SignalORM(Base):
    """ORM model for the `signals` table."""
    __tablename__ = "signals"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    type: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str | None] = mapped_column(Text, nullable=True)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_data_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    signal_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    relevance_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    embedding: Mapped[Any | None] = mapped_column(
        Vector(1536) if Vector is not None else Text, nullable=True
    )
    is_duplicate: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    dedup_hash: Mapped[str | None] = mapped_column(Text, unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


# ── Pydantic v2 Schemas ────────────────────────────────────────────────────────

class SignalCreate(BaseModel):
    """Request schema for creating a signal."""
    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    company_id: uuid.UUID | None = None
    type: SignalType
    source: str | None = None
    title: str | None = None
    description: str | None = None
    raw_data_json: dict[str, Any] = Field(default_factory=dict)
    signal_date: datetime | None = None
    relevance_score: float | None = None
    dedup_hash: str | None = None


class SignalRead(BaseModel):
    """Response schema for reading a signal."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    company_id: uuid.UUID | None
    type: SignalType
    source: str | None
    title: str | None
    description: str | None
    raw_data_json: dict[str, Any]
    signal_date: datetime | None
    relevance_score: float | None
    processed_at: datetime | None
    is_duplicate: bool
    dedup_hash: str | None
    created_at: datetime


class SignalUpdate(BaseModel):
    """Request schema for partial signal updates."""
    model_config = ConfigDict(from_attributes=True)

    relevance_score: float | None = None
    processed_at: datetime | None = None
    is_duplicate: bool | None = None
