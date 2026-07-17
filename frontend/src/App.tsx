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
