import { useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ApiError, createDeepLink, getEvent, listEventRegistrations } from '../api'
import type { DeepLinkResponse, Event, EventRegistration } from '../types'

export function EventDetailPage() {
  const { eventId = '' } = useParams()
  const [event, setEvent] = useState<Event | null>(null)
  const [registrations, setRegistrations] = useState<EventRegistration[]>([])
  const [subjectPersonId, setSubjectPersonId] = useState('')
  const [expiresInHours, setExpiresInHours] = useState(24)
  const [deepLink, setDeepLink] = useState<DeepLinkResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const registrationUrl = useMemo(() => {
    if (!deepLink) return ''
    return `${window.location.origin}/public/event-registration?token=${encodeURIComponent(deepLink.token)}`
  }, [deepLink])

  async function load() {
    setLoading(true)
    setError('')
    try {
      const [eventRow, registrationRows] = await Promise.all([
        getEvent(eventId),
        listEventRegistrations(eventId, 200),
      ])
      setEvent(eventRow)
      setRegistrations(registrationRows)
    } catch (err) {
      const detail = err instanceof ApiError ? err.message : 'Event load failed'
      setError(detail)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
    // route change
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [eventId])

  async function onCreateLink(e: FormEvent) {
    e.preventDefault()
    setError('')
    try {
      const response = await createDeepLink(eventId, { subjectPersonId, expiresInHours })
      setDeepLink(response)
      await load()
    } catch (err) {
      const detail = err instanceof ApiError ? err.message : 'Deep-link creation failed'
      setError(detail)
    }
  }

  if (loading) return <p>Loading event...</p>

  return (
    <section>
      <h2>Event detail</h2>
      <p>
        <strong>ID:</strong> {eventId}
      </p>
      {event ? (
        <p>
          <strong>Name:</strong> {event.name} ({event.eventKey})
        </p>
      ) : null}
      <p>
        <Link to="/app/events">Back to events</Link>
      </p>

      <form onSubmit={onCreateLink} className="stack">
        <h3>Create registration deep link</h3>
        <label>
          Subject Person ID
          <input
            value={subjectPersonId}
            onChange={(e) => setSubjectPersonId(e.target.value)}
            required
          />
        </label>
        <label>
          Expires in hours
          <input
            type="number"
            value={expiresInHours}
            min={1}
            max={720}
            onChange={(e) => setExpiresInHours(Number(e.target.value))}
          />
        </label>
        <button type="submit">Create deep link</button>
      </form>

      {deepLink ? (
        <div className="stack">
          <h4>Generated link</h4>
          <code>{registrationUrl}</code>
          <p>Expires: {new Date(deepLink.expiresAt).toLocaleString()}</p>
        </div>
      ) : null}

      {error ? <p className="error">{error}</p> : null}

      <h3>Registrations</h3>
      <table>
        <thead>
          <tr>
            <th>Registration ID</th>
            <th>Person ID</th>
            <th>Status</th>
            <th>Created</th>
          </tr>
        </thead>
        <tbody>
          {registrations.map((item) => (
            <tr key={item.registrationId}>
              <td>{item.registrationId}</td>
              <td>{item.personId}</td>
              <td>{item.status}</td>
              <td>{new Date(item.createdAt).toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {registrations.length === 0 ? <p>No registrations yet.</p> : null}
    </section>
  )
}

