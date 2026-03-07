import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ApiError, createPerson } from '../api'

export function PeopleCreatePage() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [phone, setPhone] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setSubmitting(true)
    setError('')
    try {
      const person = await createPerson({
        email,
        firstName: firstName || undefined,
        lastName: lastName || undefined,
        phone: phone || undefined,
      })
      navigate(`/app/people/${person.personId}`)
    } catch (err) {
      const detail = err instanceof ApiError ? err.message : 'Create failed'
      setError(detail)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <section>
      <h2>Create person</h2>
      <form onSubmit={onSubmit} className="stack">
        <label>
          Email
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </label>
        <label>
          First name
          <input value={firstName} onChange={(e) => setFirstName(e.target.value)} />
        </label>
        <label>
          Last name
          <input value={lastName} onChange={(e) => setLastName(e.target.value)} />
        </label>
        <label>
          Phone
          <input value={phone} onChange={(e) => setPhone(e.target.value)} />
        </label>
        {error ? <p className="error">{error}</p> : null}
        <div className="toolbar">
          <button type="submit" disabled={submitting}>
            {submitting ? 'Saving...' : 'Create'}
          </button>
          <Link to="/app/people">Back</Link>
        </div>
      </form>
    </section>
  )
}

