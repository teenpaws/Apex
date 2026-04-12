"""
User and CareerProfile ORM models + Pydantic v2 schemas.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import String, Text, DateTime, func
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

# pgvector import — optional until the package is installed
try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    Vector = None  # type: ignore[assignment]

from pydantic import BaseModel, ConfigDict, EmailStr
from pydantic import Field


# ── SQLAlchemy ORM ─────────────────────────────────────────────────────────────

class UserORM(Base):
    """ORM model for the `users` table."""
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    full_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    profile_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    preferences_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class CareerProfileORM(Base):
    """ORM model for the `career_profiles` table."""
    __tablename__ = "career_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    current_role: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_roles: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, default=list
    )
    industries: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, default=list
    )
    aspirations_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    embedding: Mapped[Any | None] = mapped_column(
        Vector(1536) if Vector is not None else Text, nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


# ── Pydantic v2 Schemas ────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    """Request schema for creating a user."""
    model_config = ConfigDict(from_attributes=True)

    email: EmailStr
    full_name: str | None = None
    profile_json: dict[str, Any] = Field(default_factory=dict)
    preferences_json: dict[str, Any] = Field(default_factory=dict)


class UserRead(BaseModel):
    """Response schema for reading a user."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str | None
    profile_json: dict[str, Any]
    preferences_json: dict[str, Any]
    created_at: datetime


class UserUpdate(BaseModel):
    """Request schema for partial user updates."""
    model_config = ConfigDict(from_attributes=True)

    full_name: str | None = None
    profile_json: dict[str, Any] | None = None
    preferences_json: dict[str, Any] | None = None


class CareerProfileCreate(BaseModel):
    """Request schema for creating a career profile."""
    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    current_role: str | None = None
    target_roles: list[str] = Field(default_factory=list)
    industries: list[str] = Field(default_factory=list)
    aspirations_text: str | None = None


class CareerProfileRead(BaseModel):
    """Response schema for reading a career profile."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    current_role: str | None
    target_roles: list[str]
    industries: list[str]
    aspirations_text: str | None
    updated_at: datetime


class CareerProfileUpdate(BaseModel):
    """Request schema for partial career profile updates."""
    model_config = ConfigDict(from_attributes=True)

    current_role: str | None = None
    target_roles: list[str] | None = None
    industries: list[str] | None = None
    aspirations_text: str | None = None
