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