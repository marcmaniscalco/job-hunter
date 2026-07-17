"""Poller entrypoint: fetch every configured company's postings and upsert them.

Run manually:  python pollers/poll_all.py   (from backend/, venv active)
In the cluster: runs as the poll-greenhouse CronJob (see k8s/cronjobs/).
"""

import logging

from app.db import SessionLocal
from app.models import Company
from app.sources.greenhouse import fetch_jobs, normalize_job, upsert_jobs

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def poll_company(db, company: Company) -> int:
    if company.ats_type != "greenhouse":
        logger.warning("skipping %s: unsupported ats_type %s", company.name, company.ats_type)
        return 0
    raw_jobs = fetch_jobs(company.ats_token)
    normalized = [normalize_job(raw, company.name) for raw in raw_jobs]
    count = upsert_jobs(db, normalized)
    logger.info("%s: upserted %d jobs", company.name, count)
    return count


def main() -> None:
    db = SessionLocal()
    try:
        companies = db.query(Company).all()
        total = sum(poll_company(db, c) for c in companies)
        logger.info("done: %d jobs upserted across %d companies", total, len(companies))
    finally:
        db.close()


if __name__ == "__main__":
    main()
