import { useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { ApiError, submitPublicRegistration } from '../api'

export function PublicEventRegistrationPage() {
  const [searchParams] = useSearchParams()
  const tokenFromUrl = searchParams.get('token') || ''
  const [token, setToken] = useState(tokenFromUrl)
  const [status, setStatus] = useState('Registered')
  const [guestCount, setGuestCount] = useState('')
  const [accessibilityNeeds, setAccessibilityNeeds] = useState('')
  const [consentVersion, setConsentVersion] = useState('')
  const [notes, setNotes] = useState('')
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const parsedGuestCount = useMemo(() => {
    if (!guestCount.trim()) return undefined
    const n = Number(guestCount)
    return Number.isFinite(n) ? n : undefined
  }, [guestCount])

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')
    setSuccess('')
    setSubmitting(true)
    try {
      const response = await submitPublicRegistration({
        token,
        status,
        guestCount: parsedGuestCount,
        accessibilityNeeds: accessibilityNeeds || undefined,
        consentVersion: consentVersion || undefined,
        notes: notes || undefined,
      })
      setSuccess(`Registered: ${response.registrationId} (event ${response.eventId})`)
    } catch (err) {
      const detail = err instanceof ApiError ? err.message : 'Registration failed'
      setError(detail)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <section className="public-section">
      <h2>Public Event Registration</h2>
      <p>This route is token-bound. Do not provide eventId manually.</p>
      <form onSubmit={onSubmit} className="stack">
        <label>
          Token
          <input value={token} onChange={(e) => setToken(e.target.value)} required />
        </label>
        <label>
          Status
          <select value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="Registered">Registered</option>
            <option value="Attended">Attended</option>
            <option value="Cancelled">Cancelled</option>
            <option value="No Show">No Show</option>
          </select>
        </label>
        <label>
          Guest count
          <input value={guestCount} onChange={(e) => setGuestCount(e.target.value)} />
        </label>
        <label>
          Accessibility needs
          <input value={accessibilityNeeds} onChange={(e) => setAccessibilityNeeds(e.target.value)} />
        </label>
        <label>
          Consent version
          <input value={consentVersion} onChange={(e) => setConsentVersion(e.target.value)} />
        </label>
        <label>
          Notes
          <textarea value={notes} onChange={(e) => setNotes(e.target.value)} />
        </label>
        <button type="submit" disabled={submitting}>
          {submitting ? 'Submitting...' : 'Submit registration'}
        </button>
      </form>
      {error ? <p className="error">{error}</p> : null}
      {success ? <p className="success">{success}</p> : null}
      <p>
        <Link to="/app/events">Back to internal app</Link>
      </p>
    </section>
  )
}

