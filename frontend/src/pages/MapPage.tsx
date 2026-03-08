import { useEffect, useState } from 'react'
import { ApiError, listPeople } from '../api'
import type { Person } from '../types'

export function MapPage() {
  const [people, setPeople] = useState<Person[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function load() {
    setLoading(true)
    setError('')
    try {
      const rows = await listPeople({ includeArchived: false, limit: 300 })
      setPeople(rows)
    } catch (err) {
      const detail = err instanceof ApiError ? err.message : 'Failed loading map data'
      setError(detail)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [])

  return (
    <section>
      <h2>Map</h2>
      <p>
        Parity note: Streamlit map uses geo coordinates. The new backend slice does not yet expose
        location fields, so this view currently provides a map-ready roster.
      </p>
      <div className="toolbar">
        <button onClick={() => void load()} disabled={loading}>
          {loading ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>
      {error ? <p className="error">{error}</p> : null}
      <table>
        <thead>
          <tr>
            <th>Name</th>
            <th>Email</th>
            <th>Status</th>
            <th>Map status</th>
          </tr>
        </thead>
        <tbody>
          {people.map((item) => (
            <tr key={item.personId}>
              <td>{[item.firstName, item.lastName].filter(Boolean).join(' ') || '(Unnamed)'}</td>
              <td>{item.email}</td>
              <td>{item.status}</td>
              <td>Awaiting geo fields in API</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  )
}

