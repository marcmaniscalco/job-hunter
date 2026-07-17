# Phase 3, Step 1 — Scaffold the React Frontend (manual walkthrough)

Goal: a Vite + React + TypeScript app, wired to TanStack Query, that renders
a live `JobList` from your `GET /jobs` API and a `JobDetail` view. You'll type
every command and file yourself; this doc explains *why* each step matters so
the React concepts actually stick.

Prerequisites (already confirmed on your machine): Node v24.14.0, npm 11.12.0.

Everything below assumes PowerShell, run from the repo root
(`C:\Users\manny\projects\job-hunter`).

---

## 0. Get the backend running first

The frontend is useless without something to call. In one terminal:

```powershell
kubectl port-forward -n job-hunter svc/postgres 5432:5432
```

In a second terminal:

```powershell
cd backend
./.venv/Scripts/python.exe -m uvicorn app.main:app --reload
```

Confirm `http://localhost:8000/docs` loads and `GET /jobs` returns data.
Leave both terminals running for the rest of this doc — you'll add a third
terminal for the frontend dev server.

---

## 1. Scaffold the Vite project

From the repo root:

```powershell
npm create vite@latest frontend -- --template react-ts
```

**What this does:** `create vite` is a scaffolding tool (like
`create-react-app` used to be, but fast — Vite uses native ES modules in dev
instead of bundling everything up front, which is why the dev server starts
almost instantly). `--template react-ts` gives you React + TypeScript
pre-wired, no Babel config or webpack config to hand-write.

It will create `frontend/` with something like:

```
frontend/
  src/
    App.tsx
    main.tsx
    index.css
    App.css
    assets/
  index.html
  package.json
  tsconfig.json
  tsconfig.app.json
  tsconfig.node.json
  vite.config.ts
  .gitignore
```

This matches the layout `docs/PLAN.md` sketched out.

Now install dependencies and confirm it runs:

```powershell
cd frontend
npm install
npm run dev
```

Open the URL it prints (default `http://localhost:5173`). You should see the
default Vite+React counter demo. Stop it (Ctrl+C) once confirmed — you'll
restart it later once there's something real to look at.

---

## 2. Clean out the demo scaffolding

Delete the parts you won't use:

```powershell
rm src/App.css
rm -r src/assets
```

Replace `src/index.css` with just a minimal reset (you can style properly
later — don't let CSS bikeshedding block wiring up data first):

```css
* {
  box-sizing: border-box;
}

body {
  margin: 0;
  font-family: system-ui, sans-serif;
  background: #0e0e10;
  color: #f2f2f2;
}
```

Leave `App.tsx` and `main.tsx` alone for now — you'll rewrite both shortly.

---

## 3. Install TanStack Query

```powershell
npm install @tanstack/react-query
```

**What this is and why the plan calls for it specifically:** TanStack Query
(formerly "React Query") is a *data-fetching and server-state library*. The
distinction it teaches — and the reason `docs/PLAN.md` calls it out as "the
modern, correct data-fetching pattern" — is that data from a server (like
your `/jobs` list) is not the same kind of thing as local UI state (like
"is this dropdown open"). Server data can be stale, can fail to load, can be
loading, and multiple components might want the same data without
re-fetching it. Doing this by hand with `useEffect` + `useState` is the
classic React footgun (race conditions, no caching, no retry, duplicated
fetches). TanStack Query gives you `useQuery`, which handles loading/error/
caching/refetch state for you, keyed by a query key.

You will *not* need Redux, Context-based data stores, or manual `useEffect`
fetches anywhere in this app. If you catch yourself reaching for
`useEffect(() => fetch(...))`, stop — that's the anti-pattern this library
exists to replace.

---

## 4. Wire up the QueryClientProvider

Every TanStack Query app needs exactly one `QueryClient` instance at the
root, provided via context so any component can call `useQuery`.

Open `src/main.tsx`. It currently looks like:

```tsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
```

Change it to:

```tsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import './index.css'
import App from './App.tsx'

const queryClient = new QueryClient()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </StrictMode>,
)
```

**Why this lives in `main.tsx` and not `App.tsx`:** `main.tsx` is the true
entry point (it mounts React into the DOM once). `App.tsx` is itself a
component and may get wrapped in tests or storybook-style tooling later
where you don't want a real network-backed QueryClient. Keeping the provider
at the mount point, outside `App`, is the conventional TanStack Query
pattern.

---

## 5. Allow the frontend to call the backend (CORS)

Your Vite dev server runs on `http://localhost:5173`; your API runs on
`http://localhost:8000`. Different ports means different *origins* to the
browser, so without explicit permission the browser will block the frontend's
fetch calls (CORS = Cross-Origin Resource Sharing). This has to be fixed on
the **backend**, not the frontend — only the server can grant the permission.

Open `backend/app/main.py`. Add the CORS middleware:

```python
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

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
```

Only `GET` is allowed for now since that's all the API currently exposes —
tighten/loosen this in Phase 4 when you add mutations (marking jobs
applied/rejected).

Uvicorn's `--reload` will pick this up automatically; no restart needed.

---

## 6. Build a typed API client

This is the "typed API client shared with the API shape" the plan calls out.
The idea: define one TypeScript type that mirrors your backend's `JobOut`
Pydantic schema, and one function that fetches and returns it. Every
component that needs job data goes through this, instead of components
calling `fetch` directly and guessing at the response shape.

Create `src/api/types.ts`:

```ts
export interface Job {
  id: number
  source: string
  source_job_id: string
  title: string
  company: string
  location: string | null
  remote: boolean
  url: string
  description: string | null
  salary_min: number | null
  salary_max: number | null
  posted_at: string | null
  first_seen_at: string
}
```

This mirrors `backend/app/schemas.py::JobOut` field-for-field. `datetime`
fields become `string` because that's what actually crosses the wire as
JSON — FastAPI serializes them as ISO 8601 strings. Keep this file in sync
by hand for now; the plan defers real codegen/shared-schema tooling.

Create `src/api/client.ts`:

```ts
import type { Job } from './types'

const API_BASE = 'http://localhost:8000'

export interface JobFilters {
  keyword?: string
  remote?: boolean
  company?: string
}

export async function getJobs(filters: JobFilters = {}): Promise<Job[]> {
  const params = new URLSearchParams()
  if (filters.keyword) params.set('keyword', filters.keyword)
  if (filters.remote !== undefined) params.set('remote', String(filters.remote))
  if (filters.company) params.set('company', filters.company)

  const res = await fetch(`${API_BASE}/jobs?${params}`)
  if (!res.ok) {
    throw new Error(`GET /jobs failed: ${res.status}`)
  }
  return res.json()
}

export async function getJob(id: number): Promise<Job> {
  const res = await fetch(`${API_BASE}/jobs/${id}`)
  if (!res.ok) {
    throw new Error(`GET /jobs/${id} failed: ${res.status}`)
  }
  return res.json()
}
```

**Why throw on `!res.ok`:** `fetch` only rejects on network failure, not on
HTTP error status codes (a 404 or 500 is a "successful" fetch as far as the
Promise is concerned). TanStack Query's error state only activates if the
query function actually throws, so this check is what makes your `isError` /
`error` states in `useQuery` work correctly.

`API_BASE` is hardcoded for now since you're always running the dev server
against `localhost:8000` per the plan's dev loop. Revisit with an env
variable (`import.meta.env.VITE_API_BASE`) when you containerize the
frontend for k8s at the end of this phase.

---

## 7. Build JobList

Create `src/components/JobCard.tsx`:

```tsx
import type { Job } from '../api/client'
```

Wait — fix that import, `Job` lives in `types.ts`:

```tsx
import type { Job } from '../api/types'

interface JobCardProps {
  job: Job
  onSelect: (id: number) => void
}

export function JobCard({ job, onSelect }: JobCardProps) {
  return (
    <li>
      <button onClick={() => onSelect(job.id)}>
        <strong>{job.title}</strong> — {job.company}
        {job.location ? ` (${job.location})` : ''}
        {job.remote ? ' 🌐 remote' : ''}
      </button>
    </li>
  )
}
```

**Why `onSelect` is a callback prop instead of the card navigating itself:**
this is the "components vs hooks, no prop-drilling anti-patterns" concern
from the plan. `JobCard` doesn't know or care *what* happens when it's
clicked — it just reports the selection upward. The parent (`JobList`, then
`App`) owns the "which job is currently selected" state. This keeps
`JobCard` reusable and easy to reason about in isolation.

Create `src/components/JobList.tsx`:

```tsx
import { useQuery } from '@tanstack/react-query'
import { getJobs } from '../api/client'
import { JobCard } from './JobCard'

interface JobListProps {
  onSelect: (id: number) => void
}

export function JobList({ onSelect }: JobListProps) {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['jobs'],
    queryFn: () => getJobs(),
  })

  if (isLoading) return <p>Loading jobs…</p>
  if (isError) return <p>Failed to load jobs: {error.message}</p>
  if (!data || data.length === 0) return <p>No jobs found.</p>

  return (
    <ul>
      {data.map((job) => (
        <JobCard key={job.id} job={job} onSelect={onSelect} />
      ))}
    </ul>
  )
}
```

**The `queryKey`:** `['jobs']` is how TanStack Query caches and
de-duplicates this request. If two components call `useQuery` with the same
key at the same time, only one network request fires and both get the
result. When you add filters in the next step, the key needs to include the
filter values (e.g. `['jobs', filters]`) so changing a filter is treated as
a *different* query, not a stale cache hit.

**Why check `isLoading` / `isError` before touching `data`:** TypeScript
knows `data` is `Job[] | undefined` from `useQuery`'s return type. These
checks aren't just UX politeness, they're what narrows the type so
`data.map(...)` below is safe without a non-null assertion.

---

## 8. Build JobDetail

Create `src/components/JobDetail.tsx`:

```tsx
import { useQuery } from '@tanstack/react-query'
import { getJob } from '../api/client'

interface JobDetailProps {
  jobId: number
  onBack: () => void
}

export function JobDetail({ jobId, onBack }: JobDetailProps) {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['jobs', jobId],
    queryFn: () => getJob(jobId),
  })

  if (isLoading) return <p>Loading…</p>
  if (isError) return <p>Failed to load job: {error.message}</p>
  if (!data) return null

  return (
    <div>
      <button onClick={onBack}>&larr; Back to list</button>
      <h2>{data.title}</h2>
      <p>
        {data.company}
        {data.location ? ` — ${data.location}` : ''}
        {data.remote ? ' — remote' : ''}
      </p>
      {data.salary_min && data.salary_max && (
        <p>
          ${data.salary_min.toLocaleString()} – ${data.salary_max.toLocaleString()}
        </p>
      )}
      <a href={data.url} target="_blank" rel="noreferrer">
        View original posting
      </a>
      {/* Known issue from Phase 2: Greenhouse description HTML comes back
          double-escaped. Rendering raw text for now; sanitize + render as
          HTML in a follow-up. Do NOT dangerouslySetInnerHTML this without
          sanitizing first (XSS risk) — that's the whole reason it's
          deferred rather than done here. */}
      {data.description && <p>{data.description}</p>}
    </div>
  )
}
```

**No router yet, on purpose.** The plan calls for a "JobDetail view," and
the simplest correct way to get one is lifting "which job is selected" into
state in `App` and conditionally rendering `JobList` or `JobDetail`. This
avoids pulling in `react-router` before you've felt the actual need for it
(URLs you can share/bookmark, browser back/forward). That's a good follow-up
exercise once this works, not a Step 1 requirement.

**The `queryKey: ['jobs', jobId]`:** note it's `['jobs', jobId]`, not
`['job', jobId]`. Prefixing detail queries with the same root key as the
list query (`['jobs']`) is a deliberate TanStack Query convention — it
groups related queries so you *could* later use `invalidateQueries(['jobs'])`
to invalidate both the list and every detail view at once (useful in Phase 4
once mutations exist).

---

## 9. Wire it together in App

Replace `src/App.tsx` entirely:

```tsx
import { useState } from 'react'
import { JobList } from './components/JobList'
import { JobDetail } from './components/JobDetail'

function App() {
  const [selectedJobId, setSelectedJobId] = useState<number | null>(null)

  return (
    <main>
      <h1>Job Hunter</h1>
      {selectedJobId === null ? (
        <JobList onSelect={setSelectedJobId} />
      ) : (
        <JobDetail jobId={selectedJobId} onBack={() => setSelectedJobId(null)} />
      )}
    </main>
  )
}

export default App
```

This is the "lift state up" pattern: `App` is the lowest common ancestor of
`JobList` and `JobDetail`, so it's the right place to own
`selectedJobId`. Neither child needs to know the other exists.

---

## 10. Run it end to end

Third terminal, with the backend + port-forward from Step 0 still running:

```powershell
cd frontend
npm run dev
```

Open `http://localhost:5173`. You should see your real job list (title,
company, location, remote badge) pulled live from Postgres through FastAPI.
Click a job, confirm the detail view loads and "Back to list" returns you.

Things worth deliberately testing, since the plan calls out "loading/error
states done right":

- **Loading state:** hard-refresh — you should briefly see "Loading jobs…"
  before data appears.
- **Error state:** stop the `uvicorn` process, refresh the page, confirm you
  see "Failed to load jobs: …" instead of a blank screen or a crash. Restart
  uvicorn afterward.

---

## Where this leaves you

At this point `frontend/` has:

```
frontend/
  src/
    api/
      client.ts
      types.ts
    components/
      JobCard.tsx
      JobDetail.tsx
      JobList.tsx
    App.tsx
    main.tsx
    index.css
  package.json
  vite.config.ts
```

Not yet done (deliberately deferred, matching `docs/PLAN.md`):

- Filter controls (keyword/remote/company) on `JobList` — natural next
  exercise once this is working; wire them into local `useState` +
  `queryKey: ['jobs', filters]`.
- Sanitizing/rendering the Greenhouse `description` HTML safely.
- `frontend/Dockerfile` + `k8s/frontend/` manifests — that's the
  "containerize + deploy" tail end of Phase 3, done once the app itself is
  solid, per the plan's "deploy to k8s at phase boundaries" rule.
- `react-router` for real URLs — a good Phase 3 stretch exercise, not
  required for the phase's own verification criterion ("open the React app,
  see the live job feed, filters work, detail view loads").

When this is working, update `CLAUDE.md`'s status checklist and let's talk
through filters + containerizing next.
