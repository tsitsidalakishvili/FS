import { useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import { ApiError, listPeople } from '../api'
import type { Person } from '../types'

export function OutreachPage() {
  const [people, setPeople] = useState<Person[]>([])
  const [message, setMessage] = useState('Hello team, this is the weekly campaign update.')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [segment, setSegment] = useState<'all' | 'active' | 'archived'>('active')

  async function load() {
    setLoading(true)
    setError('')
    try {
      const rows = await listPeople({ includeArchived: true, limit: 500 })
      setPeople(rows)
    } catch (err) {
      const detail = err instanceof ApiError ? err.message : 'Failed loading audience'
      setError(detail)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [])

  const audience = useMemo(() => {
    if (segment === 'all') return people
    if (segment === 'archived') return people.filter((item) => item.status === 'ARCHIVED')
    return people.filter((item) => item.status !== 'ARCHIVED')
  }, [people, segment])

  function sendPreview(e: FormEvent) {
    e.preventDefault()
    setSuccess(`Prepared campaign for ${audience.length} recipients (preview mode).`)
  }

  return (
    <section>
      <h2>Outreach</h2>
      <p>Streamlit parity: campaign composition + audience preview.</p>
      <div className="toolbar">
        <button onClick={() => void load()} disabled={loading}>
          {loading ? 'Refreshing...' : 'Refresh audience'}
        </button>
      </div>
      <form className="stack" onSubmit={sendPreview}>
        <label>
          Segment
          <select value={segment} onChange={(e) => setSegment(e.target.value as 'all' | 'active' | 'archived')}>
            <option value="active">Active people</option>
            <option value="all">All people</option>
            <option value="archived">Archived only</option>
          </select>
        </label>
        <label>
          Campaign message
          <textarea rows={4} value={message} onChange={(e) => setMessage(e.target.value)} />
        </label>
        <button type="submit">Preview send</button>
      </form>
      {error ? <p className="error">{error}</p> : null}
      {success ? <p className="success">{success}</p> : null}

      <h3>Audience preview</h3>
      <table>
        <thead>
          <tr>
            <th>Name</th>
            <th>Email</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {audience.slice(0, 20).map((item) => (
            <tr key={item.personId}>
              <td>{[item.firstName, item.lastName].filter(Boolean).join(' ') || '(Unnamed)'}</td>
              <td>{item.email}</td>
              <td>{item.status}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  )
}

