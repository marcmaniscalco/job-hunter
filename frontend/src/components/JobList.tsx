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
