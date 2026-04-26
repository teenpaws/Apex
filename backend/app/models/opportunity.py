"""
Opportunity ORM model + Pydantic v2 schemas.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Text, Float, Integer, DateTime, func
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import Confidence, OpportunityStatus

from pydantic import BaseModel, ConfigDict, Field


# ── SQLAlchemy ORM ─────────────────────────────────────────────────────────────

class OpportunityORM(Base):
    """ORM model for the `opportunities` table."""
    __tablename__ = "opportunities"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    predicted_role: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[str] = mapped_column(Text, nullable=False)
    timeline_weeks: Mapped[int | None] = mapped_column(Integer, nullable=True)
    why_fit: Mapped[str | None] = mapped_column(Text, nullable=True)
    approach_angle: Mapped[str | None] = mapped_column(Text, nullable=True)
    predicted_salary_range: Mapped[str | None] = mapped_column(Text, nullable=True)
    fit_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    key_contact_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    signal_ids: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=False, default=list
    )
    real_postings: Mapped[list[dict] | None] = mapped_column(JSONB, nullable=True, default=None)
    status: Mapped[str] = mapped_column(
        Text, nullable=False, default=OpportunityStatus.PREDICTED.value
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


# ── Pydantic v2 Schemas ────────────────────────────────────────────────────────

class OpportunityCreate(BaseModel):
    """Request schema for creating an opportunity."""
    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    company_id: uuid.UUID | None = None
    predicted_role: str | None = None
    confidence: Confidence
    timeline_weeks: int | None = None
    why_fit: str | None = None
    approach_angle: str | None = None
    predicted_salary_range: str | None = None
    fit_score: float | None = None
    key_contact_id: uuid.UUID | None = None
    signal_ids: list[uuid.UUID] = Field(default_factory=list)
    status: OpportunityStatus = OpportunityStatus.PREDICTED
    real_postings: list[dict] | None = None


class OpportunityRead(BaseModel):
    """Response schema for reading an opportunity."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    company_id: uuid.UUID | None
    predicted_role: str | None
    confidence: Confidence
    timeline_weeks: int | None
    why_fit: str | None
    approach_angle: str | None
    predicted_salary_range: str | None
    fit_score: float | None
    key_contact_id: uuid.UUID | None
    signal_ids: list[uuid.UUID]
    status: OpportunityStatus
    created_at: datetime
    updated_at: datetime
    real_postings: list[dict] | None = None


class OpportunityUpdate(BaseModel):
    """Request schema for partial opportunity updates."""
    model_config = ConfigDict(from_attributes=True)

    predicted_role: str | None = None
    confidence: Confidence | None = None
    timeline_weeks: int | None = None
    why_fit: str | None = None
    approach_angle: str | None = None
    predicted_salary_range: str | None = None
    fit_score: float | None = None
    key_contact_id: uuid.UUID | None = None
    signal_ids: list[uuid.UUID] | None = None
    status: OpportunityStatus | None = None
    real_postings: list[dict] | None = None
