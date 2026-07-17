"""Greenhouse public job-board API: fetch + normalize postings for one company.

  Docs: https://developers.greenhouse.io/job-board.html (public, no auth needed).
  """

from datetime import datetime

import httpx
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.models import Job

GREENHOUSE_BASE_URL = "https://boards-api.greenhouse.io/v1/boards"


def fetch_jobs(token: str) -> list[dict]:
    """Fetch all open postings for one company's Greenhouse board."""
    url = f"{GREENHOUSE_BASE_URL}/{token}/jobs"
    response = httpx.get(url, params={"content": "true"}, timeout=30.0)
    response.raise_for_status()
    return response.json()["jobs"]


def normalize_job(raw: dict, company_name: str) -> dict:
    """Map one raw Greenhouse job into our Job model's column shape."""
    location = (raw.get("location") or {}).get("name") or ""
    posted_at_raw = raw.get("first_published") or raw.get("updated_at")
    return {
        "source": "greenhouse",
        "source_job_id": str(raw["id"]),
        "title": raw["title"],
        "company": company_name,
        "location": location or None,
        "remote": "remote" in location.lower(),
        "url": raw["absolute_url"],
        "description": raw.get("content"),
        "salary_min": None,
        "salary_max": None,
        "posted_at": datetime.fromisoformat(posted_at_raw) if posted_at_raw else None,
        "raw_json": raw,
    }


def upsert_jobs(db: Session, jobs: list[dict]) -> int:
    """Insert new postings, refresh existing ones. Matched on (source, source_job_id).

    `first_seen_at` is deliberately left out of the update set — it should only
    ever be stamped once, on first insert (via the column's server_default).
    """
    if not jobs:
        return 0
    stmt = pg_insert(Job).values(jobs)
    refreshable = ("title", "location", "remote", "url", "description", "posted_at", "raw_json")
    stmt = stmt.on_conflict_do_update(
        constraint="uq_job_source_id",
        set_={col: stmt.excluded[col] for col in refreshable},
    )
    db.execute(stmt)
    db.commit()
    return len(jobs)
