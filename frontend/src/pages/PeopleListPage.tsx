import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ApiError, listPeople } from '../api'
import type { Person } from '../types'

export function PeopleListPage() {
  const [q, setQ] = useState('')
  const [includeArchived, setIncludeArchived] = useState(false)
  const [people, setPeople] = useState<Person[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function load() {
    setLoading(true)
    setError('')
    try {
      const rows = await listPeople({ q, includeArchived, limit: 200 })
      setPeople(rows)
    } catch (err) {
      const detail = err instanceof ApiError ? err.message : 'Failed loading people'
      setError(detail)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
    // initial load only
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <section>
      <h2>People</h2>
      <div className="toolbar">
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search name or email" />
        <label>
          <input
            type="checkbox"
            checked={includeArchived}
            onChange={(e) => setIncludeArchived(e.target.checked)}
          />
          Include archived
        </label>
        <button onClick={() => void load()} disabled={loading}>
          {loading ? 'Loading...' : 'Search'}
        </button>
        <Link to="/app/people/new">Create person</Link>
      </div>
      {error ? <p className="error">{error}</p> : null}
      <table>
        <thead>
          <tr>
            <th>Name</th>
            <th>Email</th>
            <th>Status</th>
            <th>Updated</th>
          </tr>
        </thead>
        <tbody>
          {people.map((person) => (
            <tr key={person.personId}>
              <td>
                <Link to={`/app/people/${person.personId}`}>
                  {[person.firstName, person.lastName].filter(Boolean).join(' ') || '(Unnamed)'}
                </Link>
              </td>
              <td>{person.email}</td>
              <td>{person.status}</td>
              <td>{new Date(person.updatedAt).toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {people.length === 0 && !loading ? <p>No people found.</p> : null}
    </section>
  )
}

