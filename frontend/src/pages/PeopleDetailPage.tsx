import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ApiError, listPeople, patchPerson } from '../api'

export function PeopleDetailPage() {
  const { personId = '' } = useParams()
  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [phone, setPhone] = useState('')
  const [status, setStatus] = useState<'ACTIVE' | 'ARCHIVED'>('ACTIVE')
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  async function loadPerson() {
    setLoading(true)
    setError('')
    try {
      const people = await listPeople({ includeArchived: true, limit: 500 })
      const person = people.find((p) => p.personId === personId)
      if (!person) {
        setError('Person not found')
      } else {
        setEmail(person.email)
        setFirstName(person.firstName || '')
        setLastName(person.lastName || '')
        setPhone(person.phone || '')
        setStatus(person.status === 'ARCHIVED' ? 'ARCHIVED' : 'ACTIVE')
      }
    } catch (err) {
      const detail = err instanceof ApiError ? err.message : 'Load failed'
      setError(detail)
    } finally {
      setLoading(false)
    }
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setSaving(true)
    setError('')
    try {
      await patchPerson(personId, {
        firstName: firstName || undefined,
        lastName: lastName || undefined,
        phone: phone || undefined,
        status,
      })
      await loadPerson()
    } catch (err) {
      const detail = err instanceof ApiError ? err.message : 'Save failed'
      setError(detail)
    } finally {
      setSaving(false)
    }
  }

  useEffect(() => {
    void loadPerson()
    // route param driven
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [personId])

  if (loading) return <p>Loading person...</p>

  return (
    <section>
      <h2>Person detail</h2>
      <p>
        <strong>ID:</strong> {personId}
      </p>
      <p>
        <strong>Email:</strong> {email || '-'}
      </p>
      <form onSubmit={onSubmit} className="stack">
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
        <label>
          Status
          <select value={status} onChange={(e) => setStatus(e.target.value as 'ACTIVE' | 'ARCHIVED')}>
            <option value="ACTIVE">ACTIVE</option>
            <option value="ARCHIVED">ARCHIVED</option>
          </select>
        </label>
        {error ? <p className="error">{error}</p> : null}
        <div className="toolbar">
          <button type="submit" disabled={saving}>
            {saving ? 'Saving...' : 'Save'}
          </button>
          <Link to="/app/people">Back</Link>
        </div>
      </form>
    </section>
  )
}

