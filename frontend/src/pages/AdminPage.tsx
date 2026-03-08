import { useState } from 'react'
import { getDeliberationHealth } from '../api'

const BACKEND_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8020/api/v1'

export function AdminPage() {
  const [backendStatus, setBackendStatus] = useState('unknown')
  const [deliberationStatus, setDeliberationStatus] = useState('unknown')
  const [error, setError] = useState('')

  async function runChecks() {
    setError('')
    try {
      const backend = await fetch(`${BACKEND_BASE}/healthz`)
      setBackendStatus(backend.ok ? 'ok' : `http_${backend.status}`)
      try {
        const deliberation = await getDeliberationHealth()
        setDeliberationStatus(deliberation.status)
      } catch {
        setDeliberationStatus('unreachable')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Health checks failed')
    }
  }

  return (
    <section>
      <h2>Admin</h2>
      <p>Operational checks for new UI stack services.</p>
      <div className="toolbar">
        <button onClick={() => void runChecks()}>Run health checks</button>
      </div>
      {error ? <p className="error">{error}</p> : null}
      <div className="card-grid">
        <article className="metric-card">
          <h4>Backend health</h4>
          <p>{backendStatus}</p>
        </article>
        <article className="metric-card">
          <h4>Deliberation health</h4>
          <p>{deliberationStatus}</p>
        </article>
      </div>
    </section>
  )
}

