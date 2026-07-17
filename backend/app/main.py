"""FastAPI application entrypoint.

Run locally with:  uvicorn app.main:app --reload
Interactive docs:  http://localhost:8000/docs  (FastAPI generates these for free)

For now this exposes only a health check. Real endpoints (GET /jobs, etc.) arrive
in Phase 2 once there's data to serve.
"""

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

# Importing models here ensures every table is registered on Base.metadata,
# which Alembic needs to see the full schema.
from app import models  # noqa: F401
from app.db import get_db

from app.api.jobs import router as jobs_router

app = FastAPI(title="Job Hunter API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(jobs_router)

@app.get("/health")
def health(db: Session = Depends(get_db)) -> dict:
    """Liveness + DB connectivity check.

    Kubernetes will probe this. It returns ok only if we can actually round-trip
    a query to Postgres, so a healthy response means the whole path works.
    """
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "reachable"}
