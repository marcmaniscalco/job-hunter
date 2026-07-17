# Phase 3, Step 2 — Filter Controls on JobList (manual walkthrough)

Goal: a `FilterBar` above the job list with keyword, remote, and company
filters, wired so changing them re-queries `/jobs` with the right params.
Same deal as before — you type it, I explain it, you run it.

Starting point (already in place from Step 1):

- `src/api/client.ts` already exports `JobFilters` (`keyword?`, `remote?`,
  `company?`) and `getJobs(filters)` already builds the query string from it.
  **You don't need to touch `client.ts` at all this round** — it was built
  ahead of time for exactly this.
- `src/components/JobList.tsx` currently calls `getJobs()` with no filters
  and has a hardcoded `queryKey: ['jobs']`.

---

## 1. Decide where filter state lives

`FilterBar` is going to be a **controlled, presentational component** — same
split you already used for `JobCard`: it renders inputs and reports changes
upward via a callback prop, it does not own the "current filters" state
itself. `JobList` owns that state, because `JobList` is the thing that
actually needs it to build the query.

This matters for a concrete reason: if `FilterBar` owned the state
internally, `JobList` would have no way to read it to pass into `useQuery`.
Lifting state up to the nearest common owner is the same pattern from
Step 1's `App` / `selectedJobId`.

---

## 2. Build FilterBar

Create `src/components/FilterBar.tsx`:

```tsx
import { useEffect, useState } from 'react'
import type { JobFilters } from '../api/client'

const COMPANIES = ['Stripe', 'Robinhood', 'Affirm', 'Brex', 'Chime']

interface FilterBarProps {
  onChange: (filters: JobFilters) => void
}

export function FilterBar({ onChange }: FilterBarProps) {
  const [keywordDraft, setKeywordDraft] = useState('')
  const [remote, setRemote] = useState<boolean | undefined>(undefined)
  const [company, setCompany] = useState<string | undefined>(undefined)

  // Debounce the keyword: only push it into the actual query 300ms after
  // the user stops typing, instead of firing a request per keystroke.
  useEffect(() => {
    const timeout = setTimeout(() => {
      onChange({ keyword: keywordDraft || undefined, remote, company })
    }, 300)
    return () => clearTimeout(timeout)
  }, [keywordDraft, remote, company])

  return (
    <div>
      <input
        type="text"
        placeholder="Search title…"
        value={keywordDraft}
        onChange={(e) => setKeywordDraft(e.target.value)}
      />

      <select
        value={remote === undefined ? 'any' : String(remote)}
        onChange={(e) => {
          const v = e.target.value
          setRemote(v === 'any' ? undefined : v === 'true')
        }}
      >
        <option value="any">Any (remote or on-site)</option>
        <option value="true">Remote only</option>
        <option value="false">On-site only</option>
      </select>

      <select
        value={company ?? 'any'}
        onChange={(e) => {
          const v = e.target.value
          setCompany(v === 'any' ? undefined : v)
        }}
      >
        <option value="any">All companies</option>
        {COMPANIES.map((c) => (
          <option key={c} value={c}>
            {c}
          </option>
        ))}
      </select>
    </div>
  )
}
```

A few things worth understanding line by line, since there's more going on
here than in Step 1's components:

**Why `keywordDraft` is separate state from what gets sent to the API.**
The `<input>` needs to update on every keystroke so the user sees what
they're typing (that's `keywordDraft`, updated synchronously in `onChange`).
But firing a network request on *every keystroke* is wasteful and creates a
race between fast-typing and slow responses. So there are two layers: fast
local state for what's displayed, and a slower, debounced value that
actually drives the query.

**Why this is the correct use of `useEffect`, unlike Step 1's warning
against it.** Step 1 told you not to reach for `useEffect` to fetch data —
that's TanStack Query's job. But `useEffect` still has a real purpose: it's
for synchronizing a component with something *outside* React's normal
render flow — here, a `setTimeout` timer. Every keystroke re-runs the
effect, which clears the previous pending timeout (the cleanup function
returned from `useEffect`) and starts a new one. Only if 300ms pass with no
further keystrokes does the timeout actually fire and call `onChange`. This
is the standard manual-debounce pattern in React.

**Why `remote` is `boolean | undefined`, not just `boolean`.** The API's
`remote` filter is optional (`Query(None)` in FastAPI) — three states:
"don't filter on this at all," "remote only," "on-site only." A plain
checkbox only gives you two states and can't express "don't care," so a
`<select>` with an explicit "Any" option is the right control here, not a
checkbox. Watch the `e.target.value === 'true'` conversion: `<select>`
values are always strings in the DOM, so this line is doing the
string-to-boolean conversion by hand.

**Why `company` is a hardcoded `<select>` instead of a text input.** Look
at `backend/app/api/jobs.py`: the `company` filter is an *exact* string
match (`Job.company == company`), not `ilike`. A free-text input would let
someone type `stripe` (lowercase) and silently get zero results with no
explanation. A dropdown constrained to the actual seeded companies avoids
that whole class of bug. This list is hardcoded to match `docs/PLAN.md`'s
seeded companies for now — a real "list of companies we track" endpoint is
a natural Phase 4 addition once `companies` table CRUD exists.

---

## 3. Wire FilterBar into JobList

Edit `src/components/JobList.tsx`:

```tsx
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getJobs, type JobFilters } from '../api/client'
import { JobCard } from './JobCard'
import { FilterBar } from './FilterBar'

interface JobListProps {
  onSelect: (id: number) => void
}

export function JobList({ onSelect }: JobListProps) {
  const [filters, setFilters] = useState<JobFilters>({})

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['jobs', filters],
    queryFn: () => getJobs(filters),
  })

  return (
    <div>
      <FilterBar onChange={setFilters} />

      {isLoading && <p>Loading jobs…</p>}
      {isError && <p>Failed to load jobs: {error.message}</p>}
      {data && data.length === 0 && <p>No jobs found.</p>}

      {data && (
        <ul>
          {data.map((job) => (
            <JobCard key={job.id} job={job} onSelect={onSelect} />
          ))}
        </ul>
      )}
    </div>
  )
}
```

Two changes from Step 1's version worth calling out:

**`queryKey: ['jobs', filters]` instead of `['jobs']`.** This is the piece
Step 1 flagged as a follow-up. TanStack Query treats the query key as a
cache identity — different key means a different cached entry, and (this is
the important part) changing the key is what *triggers* a refetch. If you
left the key as `['jobs']` and only changed the `queryFn`, changing filters
would silently keep serving the old cached result. `filters` is an object,
but TanStack Query does a structural (deep) comparison on query keys, not
a reference comparison, so a new `filters` object with the same values
won't cause an unnecessary refetch — only an actual value change will.

**The early-return `if (isLoading) return <p>...` pattern got replaced with
inline conditionals.** With Step 1's early returns, changing a filter would
unmount `FilterBar` entirely while the new data loaded (because the whole
component returned just `<p>Loading…</p>`), which means the input would
lose focus every time you typed. Rendering `FilterBar` unconditionally,
outside the loading/error branches, keeps it mounted across refetches so
you can keep typing/selecting without interruption. This is a real, common
TanStack Query gotcha, not a style preference.

---

## 4. Verify

With uvicorn + port-forward + `npm run dev` all running:

- Type a keyword (e.g. `engineer`). Confirm the list updates roughly 300ms
  after you stop typing, not on every keystroke — you can watch this in
  your browser's Network tab (F12 → Network), filtering for `jobs?`.
- Select "Remote only" — confirm every result shown has the 🌐 badge from
  `JobCard`. Switch to "On-site only" — confirm none do.
- Pick a company from the dropdown — confirm results narrow to just that
  company. Set it back to "All companies."
- Combine filters (e.g. keyword + a specific company) and confirm the
  result set is the intersection, not either one alone.
- Confirm `FilterBar`'s inputs never lose focus or reset while you're
  actively typing, even as the list above it flickers through loading
  states.

---

## Where this leaves you

```
frontend/src/components/
  FilterBar.tsx   (new)
  JobCard.tsx
  JobDetail.tsx
  JobList.tsx     (updated: owns filters state, renders FilterBar)
```

Not yet done (deliberately deferred):

- Filters aren't reflected in the URL, so refreshing or sharing a link
  loses them. That's what `react-router` + `useSearchParams` would solve —
  a good combined exercise once you add routing for `JobDetail`.
- The company list is hardcoded rather than pulled from the API. Revisit
  once there's a `GET /companies` endpoint.
- No "clear filters" button yet — small, optional addition if it bothers
  you in practice.

When this is working, we can talk through the description-sanitizing
follow-up or start on `react-router`.
