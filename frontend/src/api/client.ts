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