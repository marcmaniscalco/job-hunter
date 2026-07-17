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