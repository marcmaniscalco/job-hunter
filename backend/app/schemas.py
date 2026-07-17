"""Pydantic response models — the API's public shape, kept separate from the ORM models."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source: str
    source_job_id: str
    title: str
    company: str
    location: str | None
    remote: bool
    url: str
    description: str | None
    salary_min: int | None
    salary_max: int | None
    posted_at: datetime | None
    first_seen_at: datetime
