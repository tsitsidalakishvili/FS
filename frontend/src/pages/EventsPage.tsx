import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { ApiError, createEvent, listEvents } from '../api'
import type { Event } from '../types'

export function EventsPage() {
  const [eventKey, setEventKey] = useState('')
  const [name, setName] = useState('')
  const [published, setPublished] = useState(false)
  const [events, setEvents] = useState<Event[]>([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function load() {
    setLoading(true)
    setError('')
    try {
      const rows = await listEvents(250)
      setEvents(rows)
    } catch (err) {
      const detail = err instanceof ApiError ? err.message : 'Event load failed'
      setError(detail)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [])

  async function onCreate(e: FormEvent) {
    e.preventDefault()
    setError('')
    try {
      await createEvent({ eventKey, name, published })
      setEventKey('')
      setName('')
      setPublished(false)
      await load()
    } catch (err) {
      const detail = err instanceof ApiError ? err.message : 'Event create failed'
      setError(detail)
    }
  }

  return (
    <section>
      <h2>Events</h2>
      <form onSubmit={onCreate} className="stack">
        <label>
          Event key
          <input value={eventKey} onChange={(e) => setEventKey(e.target.value)} required />
        </label>
        <label>
          Name
          <input value={name} onChange={(e) => setName(e.target.value)} required />
        </label>
        <label>
          <input
            type="checkbox"
            checked={published}
            onChange={(e) => setPublished(e.target.checked)}
          />
          Published
        </label>
        <button type="submit">Create event</button>
      </form>
      {error ? <p className="error">{error}</p> : null}

      <div className="toolbar">
        <button onClick={() => void load()} disabled={loading}>
          {loading ? 'Refreshing...' : 'Refresh events'}
        </button>
      </div>

      <h3>Events</h3>
      <table>
        <thead>
          <tr>
            <th>Name</th>
            <th>Event key</th>
            <th>ID</th>
            <th>Published</th>
          </tr>
        </thead>
        <tbody>
          {events.map((event) => (
            <tr key={event.eventId}>
              <td>
                <Link to={`/app/events/${event.eventId}`}>{event.name}</Link>
              </td>
              <td>{event.eventKey}</td>
              <td>{event.eventId}</td>
              <td>{event.published ? 'Yes' : 'No'}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {events.length === 0 ? <p>No events found.</p> : null}
    </section>
  )
}

