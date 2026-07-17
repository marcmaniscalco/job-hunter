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