# Phase 3, Step 3 — Containerize and Deploy the Frontend (manual walkthrough)

Goal: build the React app into a Docker image, load it into the `kind`
cluster, and deploy it as a Deployment + Service, same shape as the backend
in Phase 1. This is the "deploy to k8s at phase boundaries" step from
`CLAUDE.md` — you've been running the frontend as a local Vite dev process
this whole phase; now it runs the way it actually will in the cluster.

Same deal as the last two docs: you type it, I explain it.

---

## 0. Stop pointing the frontend at a hardcoded URL

Right now `frontend/src/api/client.ts` has:

```ts
const API_BASE = 'http://localhost:8000'
```

That's been fine because you've always run the backend port-forwarded to
`localhost:8000`. It'll still *work* the same way once containerized (you're
about to port-forward the backend to `localhost:8000` again below), but
hardcoding it is worth fixing now rather than carrying it forward, and it's
a good excuse to learn a real Vite concept: **build-time environment
variables.**

Create `frontend/.env.development`:

```
VITE_API_BASE=http://localhost:8000
```

Edit `src/api/client.ts`, change:

```ts
const API_BASE = 'http://localhost:8000'
```

to:

```ts
const API_BASE = import.meta.env.VITE_API_BASE
```

**Why the `VITE_` prefix is required, not a style choice.** Vite only
exposes env vars to client-side code if they're prefixed `VITE_`. Everything
else in your shell/`.env` stays server-side-only, by design — a `.env` file
often holds secrets, and a client-side JS bundle is public (anyone can view
it in the browser), so Vite refuses to leak anything into that bundle unless
you opt in per-variable with the prefix. This is a real security guardrail,
not boilerplate.

**Why this matters more for deploy than for dev.** In dev, `npm run dev`
reads `.env.development` automatically, so nothing changes yet — that's
intentional, this step should not break your current dev loop. The part
that matters is *later*, in Step 2 below: `vite build` bakes
`import.meta.env.VITE_API_BASE` into the compiled JS as a literal string at
build time. That's a fundamentally different model from the backend's
`ConfigMap`, which the Python process reads fresh at container *start*
time. A frontend env var is fixed the moment you run `docker build` — to
change it, you rebuild the image, not just edit a ConfigMap and restart the
pod. Keep that distinction in mind; it'll bite you later if you forget it
(e.g. "I changed the ConfigMap but the frontend still hits the old URL").

`.env.development` is local-only config (like `.env` files generally) —
check whether `frontend/.gitignore` already ignores `.env*` files before you
commit; Vite's default template usually does this for you.

---

## 1. Write the Dockerfile

Create `frontend/Dockerfile`:

```dockerfile
# Stage 1: build the static assets. This stage needs the full Node
# toolchain and all devDependencies (TypeScript, Vite, ESLint types, etc.),
# which together are large — but none of that ships in the final image.
FROM node:24-slim AS build

WORKDIR /app

# Copy dependency-relevant files first so Docker can cache this layer and
# skip `npm ci` on rebuilds that only change application code — same
# reasoning as the backend Dockerfile's pyproject.toml-first copy.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# Baked into the JS bundle at this point — see docs/manual/03 for why this
# is different from how the backend reads its config.
ARG VITE_API_BASE=http://localhost:8000
ENV VITE_API_BASE=$VITE_API_BASE

RUN npm run build

# Stage 2: serve the built static files with nginx. No Node, no
# node_modules, no source code — just HTML/CSS/JS and a tiny web server.
FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
```

**Why two `FROM` lines (a multi-stage build).** This is the concept worth
sitting with here. If you built the app straight from a single
`node:24-slim` image, your final container would carry the entire Node
toolchain, every `devDependency`, and your uncompiled source, none of which
is needed to actually *serve* a built React app — a static site is just
files. Stage 1 (`build`) does the compiling; Stage 2 starts over from a
clean, tiny `nginx:alpine` base and copies over only `/app/dist` (Vite's
build output directory) from Stage 1. The `node:24-slim` stage and
everything in it gets discarded — it never becomes part of the image you
actually deploy. This is the standard pattern for any compiled frontend, and
part of why frontend prod images end up so much smaller than dev
environments.

**Why nginx, and not `vite preview` or a Node server.** `vite preview` and
custom Node static-file servers exist, but once you have static
files, a purpose-built web server (nginx, tiny and battle-tested at serving
files fast) is the conventional choice — no reason to keep a JS runtime
running just to hand out unchanging HTML/CSS/JS.

**Why `ARG` and not just baking in the `.env.development` value.** `ARG`
lets you override the value at `docker build` time
(`--build-arg VITE_API_BASE=...`) without editing the Dockerfile — useful
later if you ever build this image for a different environment. For now
you'll just take the default, which matches your dev value.

---

## 2. Write the nginx config

Create `frontend/nginx.conf`:

```nginx
server {
    listen 80;

    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

**Why `try_files ... /index.html` instead of nginx's default behavior.**
Your app doesn't use client-side routing yet (Step 1 deliberately deferred
`react-router`), so right now every request is just `/` and this line isn't
doing much visible work. But it's the standard, load-bearing line for any
React app and worth having correct from the start: without it, if you add
`react-router` later and someone refreshes the browser on a route like
`/jobs/42`, nginx would try to find a literal file at that path, fail, and
return a 404 — because that route only exists inside your JS bundle's
client-side router, not as a real file on disk. This line tells nginx
"if the requested path isn't a real file, serve `index.html` instead and
let React's router figure out what to render." Free to add now, saves you a
confusing bug later.

---

## 3. Build the image and load it into kind

Mirror the exact flow you used for the backend in Phase 1:

```powershell
cd frontend
docker build -t job-hunter-frontend:dev .
kind load docker-image job-hunter-frontend:dev --name job-hunter
cd ..
```

**Why `kind load docker-image` and not a registry push.** Same reasoning as
the backend: `kind` runs Kubernetes nodes as Docker containers with their
own isolated image storage, separate from your host machine's Docker. A
locally-built image is invisible to the cluster until you explicitly load
it in — no Docker Hub / ECR / registry needed for local dev.

---

## 4. Write the k8s manifests

Create `k8s/frontend/deployment.yaml`:

```yaml
# Deployment, not StatefulSet: like the backend, this is stateless — nginx
# serving static files has no identity or storage to preserve.
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend
  namespace: job-hunter
spec:
  replicas: 1
  selector:
    matchLabels:
      app: frontend
  template:
    metadata:
      labels:
        app: frontend
    spec:
      containers:
        - name: frontend
          image: job-hunter-frontend:dev
          imagePullPolicy: IfNotPresent
          ports:
            - name: http
              containerPort: 80
          readinessProbe:
            httpGet:
              path: /
              port: http
            initialDelaySeconds: 3
            periodSeconds: 10
          livenessProbe:
            httpGet:
              path: /
              port: http
            initialDelaySeconds: 5
            periodSeconds: 20
```

Create `k8s/frontend/service.yaml`:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: frontend
  namespace: job-hunter
  labels:
    app: frontend
spec:
  selector:
    app: frontend
  ports:
    - name: http
      port: 80
      targetPort: 80
```

**What's deliberately missing compared to the backend's `k8s/backend/`.**
No `configmap.yaml`, no `secret.yaml`, no `initContainers`. The backend
needed those for DB credentials and an Alembic migration step before
serving traffic. The frontend has neither a database connection nor
runtime-configurable settings — its one piece of config
(`VITE_API_BASE`) was already baked into the JS bundle back in Step 1, so
there's nothing left for the pod to read at startup. This asymmetry is the
same build-time-vs-runtime-config distinction from Step 1, showing up again
here as a concrete "why does the backend have 4 files and the frontend only
has 2" difference.

---

## 5. Apply and verify

```powershell
kubectl apply -f k8s/frontend/
kubectl wait --for=condition=ready pod -l app=frontend -n job-hunter --timeout=90s
```

You need **two** port-forwards running simultaneously now — one for each
Service — since the containerized frontend calls the containerized backend
over the same `localhost:8000` URL it always has, just now both ends are
pods instead of one pod + your local `uvicorn`:

```powershell
# Terminal 1
kubectl port-forward -n job-hunter svc/backend 8000:8000

# Terminal 2
kubectl port-forward -n job-hunter svc/frontend 5173:80
```

Open `http://localhost:5173`. You should see the same job feed, filters,
and detail view you've been running locally all phase — now served
entirely from the cluster, no local `npm run dev` or `uvicorn --reload`
involved.

You can stop your Postgres port-forward from earlier for this check — the
backend pod already talks to Postgres over the in-cluster network directly,
it never needed the port-forward that was only there for your local
`uvicorn` process.

---

## Where this leaves you

```
frontend/
  Dockerfile        (new)
  nginx.conf         (new)
  .env.development   (new, gitignored)
  src/api/client.ts  (updated: reads VITE_API_BASE)
k8s/frontend/
  deployment.yaml    (new)
  service.yaml       (new)
```

This closes out Phase 3's plan checklist — `docs/PLAN.md`'s own Phase 3
verification criterion ("open the React app, see the live job feed, filters
work, detail view loads") now passes against the *deployed* app, not just
the dev server.

Not yet done (deliberately deferred, matching `docs/PLAN.md`):

- **Ingress** — right now reaching the app means two manual
  `kubectl port-forward` commands. Phase 5 adds `ingress-nginx` plus
  `kind-config.yaml` port mappings so frontend and backend share a real
  hostname and you drop the port-forwards.
- **Rebuild loop** — same as the backend: a frontend code change now needs
  `docker build` → `kind load docker-image` → `kubectl rollout restart
  deployment/frontend -n job-hunter` to reach the cluster. Keep using
  `npm run dev` for day-to-day work; only repeat this flow at phase
  boundaries or when you specifically want to verify the containerized
  path, same rule as the backend.
- `react-router`, description sanitizing, URL-synced filters — still open
  from the earlier docs, unrelated to containerizing.

When this is verified, update `CLAUDE.md`'s status checklist to mark Phase 3
done and let's talk through Phase 4.
