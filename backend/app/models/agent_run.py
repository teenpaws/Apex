"""
AgentRun ORM model + Pydantic v2 schemas.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Text, Float, Integer, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base
from app.models.enums import AgentRunStatus

from pydantic import BaseModel, ConfigDict


# ── SQLAlchemy ORM ─────────────────────────────────────────────────────────────

class AgentRunORM(Base):
    """ORM model for the `agent_runs` table."""
    __tablename__ = "agent_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    agent_name: Mapped[str] = mapped_column(Text, nullable=False)
    model_used: Mapped[str] = mapped_column(Text, nullable=False)
    input_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    tokens_in: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_out: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(
        Text, nullable=False, default=AgentRunStatus.SUCCESS.value
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


# ── Pydantic v2 Schemas ────────────────────────────────────────────────────────

class AgentRunCreate(BaseModel):
    """Request schema for creating an agent run record."""
    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    agent_name: str
    model_used: str
    input_hash: str | None = None
    output_hash: str | None = None
    tokens_in: int | None = None
    tokens_out: int | None = None
    cost_usd: float | None = None
    duration_ms: int | None = None
    status: AgentRunStatus = AgentRunStatus.SUCCESS
    error_message: str | None = None


class AgentRunRead(BaseModel):
    """Response schema for reading an agent run."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    agent_name: str
    model_used: str
    input_hash: str | None
    output_hash: str | None
    tokens_in: int | None
    tokens_out: int | None
    cost_usd: float | None
    duration_ms: int | None
    status: AgentRunStatus
    error_message: str | None
    created_at: datetime
