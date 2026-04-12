"""
Company and Contact ORM models + Pydantic v2 schemas.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import String, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from pydantic import BaseModel, ConfigDict, Field


# ── SQLAlchemy ORM ─────────────────────────────────────────────────────────────

class CompanyORM(Base):
    """ORM model for the `companies` table."""
    __tablename__ = "companies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    domain: Mapped[str | None] = mapped_column(Text, nullable=True)
    industry: Mapped[str | None] = mapped_column(Text, nullable=True)
    size_range: Mapped[str | None] = mapped_column(Text, nullable=True)
    location: Mapped[str | None] = mapped_column(Text, nullable=True)
    linkedin_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    enrichment_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    last_enriched_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class ContactORM(Base):
    """ORM model for the `contacts` table."""
    __tablename__ = "contacts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    linkedin_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    email: Mapped[str | None] = mapped_column(String, nullable=True)
    enrichment_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    last_enriched_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


# ── Pydantic v2 Schemas ────────────────────────────────────────────────────────

class CompanyCreate(BaseModel):
    """Request schema for creating a company."""
    model_config = ConfigDict(from_attributes=True)

    name: str
    domain: str | None = None
    industry: str | None = None
    size_range: str | None = None
    location: str | None = None
    linkedin_url: str | None = None
    enrichment_json: dict[str, Any] = Field(default_factory=dict)


class CompanyRead(BaseModel):
    """Response schema for reading a company."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    domain: str | None
    industry: str | None
    size_range: str | None
    location: str | None
    linkedin_url: str | None
    enrichment_json: dict[str, Any]
    last_enriched_at: datetime | None


class CompanyUpdate(BaseModel):
    """Request schema for partial company updates."""
    model_config = ConfigDict(from_attributes=True)

    name: str | None = None
    domain: str | None = None
    industry: str | None = None
    size_range: str | None = None
    location: str | None = None
    linkedin_url: str | None = None


class ContactCreate(BaseModel):
    """Request schema for creating a contact."""
    model_config = ConfigDict(from_attributes=True)

    company_id: uuid.UUID | None = None
    name: str
    title: str | None = None
    linkedin_url: str | None = None
    email: str | None = None
    enrichment_json: dict[str, Any] = Field(default_factory=dict)


class ContactRead(BaseModel):
    """Response schema for reading a contact."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID | None
    name: str
    title: str | None
    linkedin_url: str | None
    email: str | None
    enrichment_json: dict[str, Any]
    last_enriched_at: datetime | None


class ContactUpdate(BaseModel):
    """Request schema for partial contact updates."""
    model_config = ConfigDict(from_attributes=True)

    name: str | None = None
    title: str | None = None
    linkedin_url: str | None = None
    email: str | None = None
