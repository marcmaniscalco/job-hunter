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