# CLAUDE.md — Job Hunter

Context and working rules for Claude Code sessions in this repo. Read this first.

## What this project is

A personal job-aggregation platform, built as a **learning project** alongside
Marc's 2026 job search (targeting fintech). Scheduled pollers pull postings from
job-board APIs into PostgreSQL; a FastAPI backend serves them; a React frontend
(later phase) shows a filtered, trackable feed.

**Explicit learning goals: Kubernetes and good React/frontend.** The backend is
Python (familiar) on purpose, so learning energy goes to k8s + React. When
building k8s or React pieces, explain the concepts as you go.

Full plan: `docs/PLAN.md`.

## Working rules (important)

- **Never commit or push unless Marc explicitly asks, every time.** Do not
  auto-commit even when a task seems to imply it. Writing/editing files is fine;
  creating commits is not, without an explicit request.
- **No em dashes** in prose written for Marc.
- Marc's git identity in this repo: `Marc Maniscalco <mmaniscalco18@gmail.com>`.
  GitHub username: `marcmaniscalco`. Remote: `github.com/marcmaniscalco/job-hunter`.

## Tech stack

- **Cluster:** `kind` (cluster name `job-hunter`) on Docker Desktop. Docker
  Desktop must be running before any cluster work.
- **DB:** Postgres 16 as a StatefulSet **in-cluster** (not AWS RDS; RDS deferred).
  Namespace `job-hunter`.
- **Backend:** Python 3.13 + FastAPI + SQLAlchemy 2.0 + Alembic + psycopg + httpx.
  Code under `backend/app/`. Virtualenv at `backend/.venv`
  (invoke `./.venv/Scripts/python.exe` on Windows).
- **Frontend (Phase 3):** React + Vite + TypeScript + TanStack Query.
- **Pollers:** Python, run as k8s CronJobs. First source: Greenhouse public board
  API. Later: Lever, Ashby, Adzuna, USAJOBS. Avoid LinkedIn/Indeed (no usable API).
- **No AI in v1** (deferred to a later phase).

## Current status

- [x] **Phase 0** — kind cluster + Postgres (StatefulSet, PVC, Service, Secret). Verified.
- [x] **Phase 1** — backend: FastAPI `/health` + SQLAlchemy models (companies,
      jobs, saved_searches, job_status); Alembic migration creating all four
      tables; Dockerfile; deployed to the cluster as a Deployment + Service
      (DB creds via `backend-secret`, config via `backend-config` ConfigMap,
      migrations applied by an initContainer on each rollout). Verified via
      `kubectl port-forward svc/backend` against `/health` and `/docs`.
- [x] **Phase 2** — Greenhouse poller (`sources/greenhouse.py`, fetch + normalize
      + upsert with dedupe on `(source, source_job_id)`); `pollers/poll_all.py`
      entrypoint; `poll-greenhouse` CronJob (every 30 min); `GET /jobs` and
      `GET /jobs/{id}` with keyword/remote/company filtering. Seeded companies:
      Stripe, Robinhood, Affirm, Brex, Chime. Verified via manual CronJob
      trigger, DB row counts (1,132 jobs, no dupes on re-run), and live API
      queries.
- [x] **Phase 3** — React frontend: Vite + TS + TanStack Query app with
      `JobList` (live data, loading/error states, keyword/remote/company
      `FilterBar`) and `JobDetail`; typed API client (`api/types.ts`,
      `api/client.ts`) mirroring the backend's `JobOut` schema; state lifted
      rather than prop-drilled, no router yet. Backend gained CORS
      middleware for the dev server origin. Containerized (multi-stage
      Dockerfile, nginx serving the build; `VITE_API_BASE` baked in at
      build time) and deployed as a Deployment + Service in
      `k8s/frontend/`. Verified via two simultaneous port-forwards
      (`svc/backend` 8000, `svc/frontend` 5173) showing the live feed,
      filters, and detail view served entirely from the cluster. Manual
      walkthrough docs: `docs/manual/01-frontend-scaffold.md`,
      `02-filter-controls.md`, `03-containerize-deploy.md`.
- [ ] **Phase 4** — saved searches + application tracking + more sources.

## Dev loop (fast inner loop)

DB stays in the cluster; app runs locally with hot-reload.

```bash
# Terminal 1 — expose cluster Postgres on localhost:5432
kubectl port-forward -n job-hunter svc/postgres 5432:5432

# Terminal 2 — run the API with auto-reload
cd backend
./.venv/Scripts/python.exe -m uvicorn app.main:app --reload
# http://localhost:8000/docs
```

First-time backend setup: `python -m venv .venv` then
`./.venv/Scripts/python.exe -m pip install -e .`

Only rebuild/redeploy container images to k8s at phase boundaries, to practice
the k8s side deliberately rather than on every edit.

## Bring the cluster up from scratch

```bash
kind create cluster --config kind-config.yaml
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/postgres/
kubectl wait --for=condition=ready pod/postgres-0 -n job-hunter --timeout=180s
```

See `README.md` for the full runbook.

## Data model (v1)

- **companies** — `id, name, ats_type, ats_token`
- **jobs** — normalized posting; unique `(source, source_job_id)` for dedupe
- **saved_searches** — Marc's filter criteria (DB-driven, Phase 4)
- **job_status** — application tracking (interested/applied/rejected/hidden)

Defined in `backend/app/models.py` (SQLAlchemy 2.0 typed style).
