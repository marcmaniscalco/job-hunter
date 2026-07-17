# Job Hunter

A personal job-aggregation platform: scheduled pollers pull postings from job
sources into Postgres, a FastAPI backend serves them, and a React frontend (Phase
3) presents a filtered, trackable feed. Runs on a local Kubernetes cluster (kind).

Built as a learning project — the emphasis is on **Kubernetes** and **React**,
with a Python backend. See `.claude/plans/` for the full phased plan.

## Prerequisites

Setting up on a new machine (e.g. a laptop)? Install these first. Commands below
are for Windows via [winget](https://learn.microsoft.com/en-us/windows/package-manager/winget/);
swap in Homebrew/apt as needed on other OSes.

```powershell
winget install Docker.DockerDesktop
winget install Kubernetes.kubectl
winget install Kubernetes.kind
winget install Python.Python.3.13
winget install OpenJS.NodeJS.LTS   # Node 24 — needed starting Phase 3 (React frontend)
```

Verify:

```bash
docker --version
kubectl version --client
kind version
python --version     # should be 3.13.x
node --version       # should be 24.x, needed from Phase 3 onward
```

**Docker Desktop must be running** before any cluster work (`kind create cluster`,
`kubectl` against this cluster, etc.) — start it from the Start menu and wait for
it to report "running" before continuing.

After Docker Desktop is running, jump to [Bring it up from scratch](#bring-it-up-from-scratch)
below — it covers creating the cluster, Postgres, the backend venv, and running
the first migration.

## Architecture (current)

```
  kind cluster "job-hunter"
    └─ namespace: job-hunter
         └─ StatefulSet postgres-0  ──> PVC data-postgres-0 (2Gi)
         └─ Service postgres (headless, :5432)
         └─ Secret postgres-secret (db creds)

         └─ Deployment backend (1 replica)
              └─ initContainer: alembic upgrade head
              └─ container: uvicorn (FastAPI app, :8000)
         └─ Service backend (:8000)
         └─ Secret backend-secret (DATABASE_URL)
         └─ ConfigMap backend-config (LOG_LEVEL)
```

## Bring it up from scratch

```bash
# 1. Start Docker Desktop (GUI), then create the cluster:
kind create cluster --config kind-config.yaml

# 2. Deploy Postgres:
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/postgres/
kubectl wait --for=condition=ready pod/postgres-0 -n job-hunter --timeout=180s

# 3. Port-forward Postgres (leave this running; open a new terminal for step 4):
kubectl port-forward -n job-hunter svc/postgres 5432:5432
```

```bash
# 4. In another terminal — first-time backend setup + run migrations:
cd backend
python -m venv .venv
./.venv/Scripts/python.exe -m pip install -e .
./.venv/Scripts/alembic.exe upgrade head
```

```bash
# 5. Build the backend image and load it into the cluster, then deploy it.
# kind's nodes are Docker containers with their own image store, so a locally
# built image is invisible to them until explicitly loaded — no registry needed.
cd backend
docker build -t job-hunter-backend:dev .
kind load docker-image job-hunter-backend:dev --name job-hunter
cd ..
kubectl apply -f k8s/backend/
kubectl wait --for=condition=ready pod -l app=backend -n job-hunter --timeout=90s
```

Verify: `kubectl port-forward -n job-hunter svc/backend 8000:8000`, then open
http://localhost:8000/health and http://localhost:8000/docs.

Made a change to `app/`, `models.py`, or a migration and want it live in the
cluster? Repeat step 5 (`docker build` → `kind load` → `kubectl rollout restart
deployment/backend -n job-hunter`) — see the note on the dev loop below for why
this isn't part of the everyday workflow.

## Daily dev loop (fast inner loop)

Once the backend venv is set up (see "Bring it up from scratch" above), run the
DB in the cluster but the app locally with hot-reload:

```bash
# Terminal 1 — expose cluster Postgres on localhost:5432
kubectl port-forward -n job-hunter svc/postgres 5432:5432

# Terminal 2 — run the API with auto-reload
cd backend
./.venv/Scripts/python.exe -m uvicorn app.main:app --reload
# open http://localhost:8000/docs
```

## Useful cluster commands

```bash
kubectl get all -n job-hunter                 # everything in our namespace
kubectl logs -n job-hunter postgres-0         # database logs
kubectl exec -it -n job-hunter postgres-0 -- psql -U jobhunter -d jobhunter
kubectl logs -n job-hunter -l app=backend                # backend API logs
kubectl logs -n job-hunter -l app=backend -c migrate      # last migration run
kind delete cluster --name job-hunter         # tear it all down
```

## FAQ / troubleshooting

**`kubectl get all -n job-hunter` (or similar) says "No resources found", but you know you deployed things.**

Docker Desktop ships its own single-node Kubernetes cluster, separate from the
`kind` cluster this project uses. Both show up as `kubectl` contexts, and it's
easy to end up on the wrong one after a reboot — especially if Docker Desktop's
built-in Kubernetes is also enabled. Check which context you're on and switch if
needed:

```bash
kubectl config current-context      # expect: kind-job-hunter
kubectl config get-contexts         # lists all contexts; * marks the current one
kubectl config use-context kind-job-hunter
```

**After restarting my PC, the pods show `RESTARTS` > 0 — did I lose my data?**

No. When Docker Desktop restarts, the kind cluster's node containers restart
with it, which restarts the pods running on them. `postgres-0`'s data lives on
its PVC (backed by a volume on disk), not in the container, so it survives.
Verify any time with:

```bash
kubectl exec -n job-hunter postgres-0 -- psql -U jobhunter -d jobhunter -c "\dt"
```

You should see all four tables (`companies`, `jobs`, `saved_searches`,
`job_status`) plus `alembic_version`.

**I changed a pod spec (e.g. a probe) in `k8s/postgres/statefulset.yaml`, ran
`kubectl apply`, but the running pod still has the old spec.**

`kubectl apply` updates the StatefulSet object right away, and for most changes
the StatefulSet controller then rolls existing pods to match automatically. But
if it doesn't seem to have happened, confirm where the mismatch actually is
before assuming `apply` is broken — check the StatefulSet's *desired* spec vs
the *running pod's* spec:

```bash
kubectl get statefulset postgres -n job-hunter -o jsonpath='{.spec.template.spec.containers[0].readinessProbe.exec.command}'
kubectl get pod postgres-0 -n job-hunter -o jsonpath='{.spec.containers[0].readinessProbe.exec.command}'
```

If the StatefulSet already shows your new spec but the pod still shows the old
one, the rollout just hasn't reached it yet — nudge it along by deleting the
pod so it's recreated from the current template:

```bash
kubectl delete pod postgres-0 -n job-hunter
```

This is safe: `postgres-0`'s data lives on its PVC, not in the pod, so deleting
the pod (as opposed to the PVC) never touches the data — same guarantee as the
restart-survival question above.

**`kubectl port-forward` isn't working / "connection refused" hitting `/health`.**

Check whether a `port-forward` is actually running in another terminal — it's
easy to forget it's not still up. `port-forward` is a **client-side** process,
not a cluster resource: it's `kubectl` opening a tunnel through the API server
to one specific pod, for as long as that command keeps running in your
terminal. Kubernetes itself has no idea it exists. It is *not* something that
"starts with the cluster" — closing the terminal, Ctrl+C, or the target pod
restarting all silently kill it, and you just rerun the command to bring it
back:

```bash
kubectl port-forward -n job-hunter svc/backend 8000:8000
```

Also note: you don't need this running for normal day-to-day development —
that's what the "Daily dev loop" section above is for (local `uvicorn
--reload` against a port-forwarded Postgres, hitting `localhost:8000`
directly). `port-forward`ing `svc/backend` itself is only needed when you
specifically want to check the *in-cluster deployed* version.

If re-running port-forward each time you want to poke the in-cluster backend
gets annoying, there are real fixes for that (a NodePort + kind port mapping
for a stable no-command-needed local port, or Ingress for a proper hostname) —
deliberately deferred to Phase 5 per the plan rather than solved ad hoc now.

## Status

- [x] Phase 0 — kind cluster + Postgres (StatefulSet/PVC/Service/Secret)
- [x] Phase 1 — backend: FastAPI `/health` + data model + Alembic migration +
      Dockerfile, deployed to the cluster as a Deployment + Service (DB creds
      via Secret, config via ConfigMap, migrations run by an initContainer)
- [x] Phase 2 — Greenhouse poller (fetch/normalize/upsert with dedupe) as a
      `poll-greenhouse` CronJob; `GET /jobs` + `GET /jobs/{id}` with
      keyword/remote/company filtering. Seeded: Stripe, Robinhood, Affirm,
      Brex, Chime.
- [ ] Phase 3 — React frontend
- [ ] Phase 4 — saved searches + application tracking + more sources
