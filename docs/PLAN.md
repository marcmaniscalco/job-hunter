# Job Hunter — Local Kubernetes Job-Aggregation Platform

## Context

Marc is job searching in 2026 (targeting fintech) and wants a project that both
produces daily value (a personal feed of jobs matching his criteria) and closes
skill gaps he's identified: **good frontend/React programming** and
**Kubernetes**. He has strong backend/data-engineering fundamentals, so the plan
leans into frontend + k8s as the *learning* surface while keeping the backend in
familiar Python.

The core insight from research: job sites offer **almost no events/webhooks for
job seekers**, but several offer **pollable APIs**. So the system is a scheduled
poll → dedupe → store → filter → view pipeline. That polling model maps perfectly
onto Kubernetes CronJobs, which makes this an ideal k8s teaching project.

### Decisions already made
- **Database:** local Postgres in-cluster (StatefulSet + PVC). $0, self-contained. RDS migration deferred to a later phase.
- **Backend:** Python. Focus learning energy on k8s + React, not a new language.
- **AI:** skipped for v1. Plain keyword/criteria filtering first; AI is a later phase.

### Chosen tech stack (all prerequisites already installed except helm)
- **Cluster:** `kind` 0.32 on Docker Desktop (already installed).
- **DB:** Postgres 16 StatefulSet in the cluster.
- **Backend:** Python 3.13 + **FastAPI** (async API + auto OpenAPI docs at `/docs`), **SQLAlchemy** ORM, **Alembic** migrations, **httpx** for polling, **Pydantic** for schemas.
- **Frontend:** **React + Vite + TypeScript** with **TanStack Query** (React Query) for data fetching, teaches the modern, correct data-fetching pattern from day one.
- **Pollers:** Python scripts packaged in the backend image, run as k8s **CronJobs**.
- **Images:** built locally, loaded into kind with `kind load docker-image` (no registry needed).

### Job sources (start small, expand in Phase 4)
- **v1 source:** Greenhouse public board API (`boards-api.greenhouse.io/v1/boards/{company}/jobs`), no auth, many fintech companies.
- **Later:** Lever (`api.lever.co/v0/postings/{company}`), Ashby, Adzuna (keyed aggregator, free tier), USAJOBS (official, keyed).
- **Avoid:** LinkedIn (no realistic API, blocks scraping), Indeed (partner-only now).

---

## Repo layout (monorepo)

```
job-hunter/
  backend/
    app/
      main.py          # FastAPI app + router registration
      db.py            # engine/session
      models.py        # SQLAlchemy: Company, Job, SavedSearch, JobStatus
      schemas.py       # Pydantic request/response models
      config.py        # env-driven settings (DB URL from Secret)
      api/jobs.py      # GET /jobs (+ filters), GET /jobs/{id}, status mutations
      sources/greenhouse.py   # fetch+normalize one source
    pollers/poll_all.py       # entrypoint the CronJob runs
    alembic/                  # migrations
    pyproject.toml
    Dockerfile
  frontend/
    src/  (App, JobList, JobDetail, api client, types)
    package.json
    Dockerfile
  k8s/
    postgres/   (statefulset, service, secret)
    backend/    (deployment, service, configmap, secret)
    frontend/   (deployment, service)
    cronjobs/   (poll-greenhouse cronjob)
  README.md    # runbook: how to bring the whole thing up
```

---

## Data model (v1)

- **companies** — `id, name, ats_type, ats_token` (e.g. ats_type='greenhouse', token='stripe').
- **jobs** — `id, source, source_job_id, title, company, location, remote, url, description, salary_min, salary_max, posted_at, first_seen_at, raw_json`. **Unique (source, source_job_id)** for idempotent upserts (dedupe).
- **saved_searches** — `id, name, keywords[], locations[], remote_only, min_salary`, Marc's filter criteria, stored not hardcoded.
- **job_status** — `job_id, state (interested|applied|rejected|hidden), notes, updated_at`, turns the feed into an application tracker (daily-use value).

---

## Phased plan (each phase ends with something that works)

### Phase 0 — Cluster + Postgres ("hello, Kubernetes")  ✅ done
- `git init` the repo; create the kind cluster from a small `kind-config.yaml`.
- Write and apply Postgres **StatefulSet + PVC + Service + Secret**.
- Verify by `kubectl exec` into the pod and running `psql`.
- **Teaches:** kind, kubectl basics, StatefulSet, PersistentVolumeClaim, Service, Secret.

### Phase 1 — Backend API skeleton on the cluster  (in progress)
- FastAPI app with `/health`; SQLAlchemy models; Alembic migration that creates the tables.
- Dockerfile; `kind load docker-image`; deploy as **Deployment + Service**; DB creds via **Secret**, config via **ConfigMap**.
- Verify: `kubectl port-forward` then hit `/health` and the auto-generated `/docs`.
- **Teaches:** Dockerfile authoring, Deployment vs Service, Config/Secret injection, DB migrations.

### Phase 2 — First poller, end-to-end data
- `sources/greenhouse.py` fetches + normalizes jobs for 3–5 fintech companies; upsert with dedupe on `(source, source_job_id)`.
- Package as a **CronJob** (every ~30 min).
- `GET /jobs` endpoint with basic filtering (keyword, remote, company).
- Verify: let the CronJob run (or trigger manually), confirm rows in Postgres and JSON from `/jobs`.
- **Teaches:** CronJob, idempotent pipelines, separating fetch/normalize/store.

### Phase 3 — React frontend (the main learning focus)
- Vite + TS app: a **JobList** page (fetch `/jobs` via TanStack Query, render cards, filter controls) and a **JobDetail** view.
- Emphasis on *good* React: typed API client, components vs hooks, loading/error states done right, no prop-drilling anti-patterns.
- Containerize + deploy; expose via `port-forward` first (Ingress deferred, on Windows/kind it needs extra port-mapping config we'll add in Phase 5).
- **Teaches:** React fundamentals, TypeScript types shared with the API shape, declarative data fetching, component design.

### Phase 4 — Make it genuinely useful
- Move criteria into **saved_searches** (DB-driven); API/pollers filter against them.
- **Application tracking**: mark interested/applied/rejected + notes (React forms + mutations).
- Add sources: **Lever**, **Ashby**, **Adzuna**, **USAJOBS** (one module each, same normalize interface).
- **Teaches:** richer data model, React forms & mutations, optimistic updates, pluggable-source design.

### Phase 5 — Polish & stretch (deferred / optional)
- Ingress (ingress-nginx + kind port mappings) so frontend+API share a hostname.
- Notifications (email/desktop) when new jobs match a saved search.
- **AI layer** (the skipped v1 feature): match/rank against resume, or tailor cover letters.
- **RDS migration** as a deliberate AWS-experience exercise (DB layer is kept swappable to make this easy).
- Helm chart to package the whole app; basic observability.

---

## Dev-loop note (important for learning speed)

Rebuilding an image and reloading into kind on every code change is painfully
slow, bad for learning React. Recommended workflow:
- Keep **Postgres running in kind** (so you learn StatefulSets), and `port-forward`
  it to localhost.
- During active coding, run the backend with `uvicorn --reload` and the frontend
  with the **Vite dev server** as plain local processes against that DB, fast
  inner loop.
- **Deploy to k8s at phase boundaries** to learn the containerization/Deployment/
  CronJob/Ingress pieces deliberately, not on every edit.

## Verification per phase
- **P0:** `kubectl get pods`, `kubectl exec … psql -c '\dt'`.
- **P1:** `curl localhost:8000/health` and open `/docs`; `alembic` shows tables.
- **P2:** trigger the CronJob, confirm rows in Postgres and that `/jobs` returns them, deduped.
- **P3:** open the React app, see the live job feed, filters work, detail view loads.
- **P4:** create a saved search, mark a job "applied", reload and confirm persistence; new sources appear in the feed.
