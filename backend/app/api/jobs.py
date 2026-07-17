"""GET /jobs — list postings with basic filtering; GET /jobs/{id} — one posting."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Job
from app.schemas import JobOut

router = APIRouter()


@router.get("/jobs", response_model=list[JobOut])
def list_jobs(
  keyword: str | None = Query(None, description="Case-insensitive match against title"),
  remote: bool | None = Query(None),
  company: str | None = Query(None, description="Exact company name match"),
  db: Session = Depends(get_db),
) -> list[Job]:
    stmt = select(Job).order_by(Job.posted_at.desc().nullslast())
    if keyword:
        stmt = stmt.where(Job.title.ilike(f"%{keyword}%"))
    if remote is not None:
        stmt = stmt.where(Job.remote == remote)
    if company:
        stmt = stmt.where(Job.company == company)
    return list(db.execute(stmt).scalars())


@router.get("/jobs/{job_id}", response_model=JobOut)
def get_job(job_id: int, db: Session = Depends(get_db)) -> Job:
  job = db.get(Job, job_id)
  if job is None:
      raise HTTPException(status_code=404, detail="job not found")
  return job
