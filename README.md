# Job Hunter

A personal job-aggregation platform: scheduled pollers pull postings from job
sources into Postgres, a FastAPI backend serves them, and a React frontend (Phase
3) presents a filtered, trackable feed. Runs on a local Kubernetes cluster (kind).

Built as a learning project — the emphasis is on **Kubernetes** and **React**,
with a Python backend. See `.claude/plans/` for the full phased plan.

## Prerequisites

Already installed on this machine: Docker Desktop, `kubectl`, `kind`, Python 3.13,
Node 24. **Docker Desktop must be running** before any cluster work.

## Architecture (current)

```
  kind cluster "job-hunter"
    └─ namespace: job-hunter
         └─ StatefulSet postgres-0  ──> PVC data-postgres-0 (2Gi)
         └─ Service postgres (headless, :5432)
         └─ Secret postgres-secret (db creds)

  Backend (Python/FastAPI) — runs locally for now, deployed to cluster next.
```

## Bring it up from scratch

```bash
# 1. Start Docker Desktop (GUI), then create the cluster:
kind create cluster --config kind-config.yaml

# 2. Deploy Postgres:
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/postgres/
kubectl wait --for=condition=ready pod/postgres-0 -n job-hunter --timeout=180s
```

## Daily dev loop (fast inner loop)

Run the DB in the cluster but the app locally with hot-reload:

```bash
# Terminal 1 — expose cluster Postgres on localhost:5432
kubectl port-forward -n job-hunter svc/postgres 5432:5432

# Terminal 2 — run the API with auto-reload
cd backend
./.venv/Scripts/python.exe -m uvicorn app.main:app --reload
# open http://localhost:8000/docs
```

First-time backend setup:

```bash
cd backend
python -m venv .venv
./.venv/Scripts/python.exe -m pip install -e .
```

## Useful cluster commands

```bash
kubectl get all -n job-hunter                 # everything in our namespace
kubectl logs -n job-hunter postgres-0         # database logs
kubectl exec -it -n job-hunter postgres-0 -- psql -U jobhunter -d jobhunter
kind delete cluster --name job-hunter         # tear it all down
```

## Status

- [x] Phase 0 — kind cluster + Postgres (StatefulSet/PVC/Service/Secret)
- [~] Phase 1 — backend skeleton: FastAPI `/health` + data model (running locally)
      next: Alembic migration to create tables, then containerize + deploy to k8s
- [ ] Phase 2 — Greenhouse poller as a CronJob + `GET /jobs`
- [ ] Phase 3 — React frontend
- [ ] Phase 4 — saved searches + application tracking + more sources
