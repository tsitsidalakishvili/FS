import { useState } from 'react'
import { ApiError, listEvents, listPeople, listTasks } from '../api'

function downloadJson(filename: string, payload: unknown): void {
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
}

export function DataPage() {
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  async function exportDataset(kind: 'people' | 'tasks' | 'events') {
    setError('')
    setSuccess('')
    try {
      if (kind === 'people') {
        const rows = await listPeople({ includeArchived: true, limit: 1000 })
        downloadJson('people-export.json', rows)
      } else if (kind === 'tasks') {
        const rows = await listTasks({ limit: 1000 })
        downloadJson('tasks-export.json', rows)
      } else {
        const rows = await listEvents(1000)
        downloadJson('events-export.json', rows)
      }
      setSuccess(`Exported ${kind} dataset.`)
    } catch (err) {
      const detail = err instanceof ApiError ? err.message : 'Export failed'
      setError(detail)
    }
  }

  return (
    <section>
      <h2>Data</h2>
      <p>Streamlit parity: data utilities and export shortcuts.</p>
      <div className="toolbar">
        <button onClick={() => void exportDataset('people')}>Export people JSON</button>
        <button onClick={() => void exportDataset('tasks')}>Export tasks JSON</button>
        <button onClick={() => void exportDataset('events')}>Export events JSON</button>
      </div>
      {error ? <p className="error">{error}</p> : null}
      {success ? <p className="success">{success}</p> : null}
    </section>
  )
}

