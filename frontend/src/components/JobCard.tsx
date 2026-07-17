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
