"""ORM models — the v1 data model from the plan.

Uses SQLAlchemy 2.0 typed style (`Mapped` / `mapped_column`). Each class maps to
one table. These definitions are the single source of truth for the schema;
Alembic (next increment) will read them to generate migrations.
"""

from datetime import datetime

from sqlalchemy import (
    ARRAY,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Company(Base):
    """A company whose jobs we poll, plus which ATS it uses."""

    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    # e.g. "greenhouse", "lever", "ashby"
    ats_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # the company's slug on that ATS, e.g. "stripe"
    ats_token: Mapped[str] = mapped_column(String(200), nullable=False)

    __table_args__ = (UniqueConstraint("ats_type", "ats_token", name="uq_company_ats"),)


class Job(Base):
    """A single job posting, normalized from whatever source produced it."""

    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # which source/ATS this came from, e.g. "greenhouse"
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    # the posting's stable id *within that source* — used for dedupe
    source_job_id: Mapped[str] = mapped_column(String(200), nullable=False)

    title: Mapped[str] = mapped_column(String(400), nullable=False)
    company: Mapped[str] = mapped_column(String(200), nullable=False)
    location: Mapped[str | None] = mapped_column(String(300))
    remote: Mapped[bool] = mapped_column(Boolean, default=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    salary_min: Mapped[int | None] = mapped_column(Integer)
    salary_max: Mapped[int | None] = mapped_column(Integer)

    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # server_default=now() lets the DB stamp this on insert
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    # keep the untouched source payload for debugging / re-parsing later
    raw_json: Mapped[dict | None] = mapped_column(JSONB)

    # The dedupe key: the same posting from the same source is one row. Pollers
    # upsert against this, so re-running a poll never creates duplicates.
    __table_args__ = (
        UniqueConstraint("source", "source_job_id", name="uq_job_source_id"),
    )


class SavedSearch(Base):
    """Marc's filter criteria, stored in the DB rather than hardcoded (Phase 4)."""

    __tablename__ = "saved_searches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    keywords: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    locations: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    remote_only: Mapped[bool] = mapped_column(Boolean, default=False)
    salary_min: Mapped[int | None] = mapped_column(Integer)


class JobStatus(Base):
    """Application-tracking state for a job (interested/applied/rejected/hidden)."""

    __tablename__ = "job_status"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    state: Mapped[str] = mapped_column(String(30), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    job: Mapped["Job"] = relationship()
