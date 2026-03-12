import { useState } from 'react'
import type { FormEvent } from 'react'

import { searchPeople } from '../api/coreApi'
import type { PersonSummary } from '../types/api'

export function CrmPage() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<PersonSummary[]>([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setError('')
    setLoading(true)
    try {
      const response = await searchPeople(query)
      setResults(response.items)
    } catch (caughtError) {
      setResults([])
      setError(caughtError instanceof Error ? caughtError.message : 'Request failed.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="page-stack">
      <section className="section-header">
        <div>
          <p className="eyebrow">CRM</p>
          <h2>People search</h2>
        </div>
        <p className="muted">
          First React CRM slice backed by the new Core API service.
        </p>
      </section>

      <section className="panel-card">
        <form className="form-grid" onSubmit={handleSubmit}>
          <label className="field">
            <span>Search by name or email</span>
            <input
              minLength={2}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search CRM people..."
              value={query}
            />
          </label>
          <div className="form-actions">
            <button disabled={loading || query.trim().length < 2} type="submit">
              {loading ? 'Searching…' : 'Search people'}
            </button>
          </div>
        </form>
        {error ? <p className="error-text">{error}</p> : null}
      </section>

      <section className="panel-card">
        <div className="table-header">
          <h3>Results</h3>
          <span className="muted">{results.length} matches</span>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Email</th>
                <th>Group</th>
                <th>Availability</th>
              </tr>
            </thead>
            <tbody>
              {results.length === 0 ? (
                <tr>
                  <td className="empty-state" colSpan={4}>
                    Search to load CRM people from the Core API.
                  </td>
                </tr>
              ) : (
                results.map((person) => (
                  <tr key={person.person_id}>
                    <td>{person.full_name}</td>
                    <td>{person.email ?? '—'}</td>
                    <td>{person.group ?? '—'}</td>
                    <td>{person.time_availability ?? '—'}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}
