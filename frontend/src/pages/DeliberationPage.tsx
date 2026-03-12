import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'

import { StatusBadge } from '../components/StatusBadge'
import {
  createConversation,
  getDeliberationApiHealth,
  listConversations,
} from '../api/deliberationApi'
import type { ConversationSummary } from '../types/api'

const initialForm = {
  topic: '',
  description: '',
  is_open: true,
  allow_comment_submission: true,
  allow_viz: true,
  moderation_required: false,
}

export function DeliberationPage() {
  const [conversations, setConversations] = useState<ConversationSummary[]>([])
  const [health, setHealth] = useState<string>('unknown')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState(false)
  const [formState, setFormState] = useState(initialForm)

  const load = async () => {
    setLoading(true)
    setError('')
    try {
      const [healthResponse, conversationsResponse] = await Promise.all([
        getDeliberationApiHealth(),
        listConversations(),
      ])
      setHealth(`${healthResponse.status} / ${healthResponse.db}`)
      setConversations(conversationsResponse)
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Request failed.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [])

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setCreating(true)
    setError('')
    try {
      await createConversation({
        ...formState,
        topic: formState.topic.trim(),
        description: formState.description.trim(),
      })
      setFormState(initialForm)
      await load()
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Create failed.')
    } finally {
      setCreating(false)
    }
  }

  return (
    <div className="page-stack">
      <section className="section-header">
        <div>
          <p className="eyebrow">Deliberation</p>
          <h2>Conversation manager</h2>
        </div>
        <StatusBadge tone={health.startsWith('ok') ? 'success' : 'warning'}>
          API {health}
        </StatusBadge>
      </section>

      <section className="panel-card">
        <div className="table-header">
          <h3>Existing conversations</h3>
          <button onClick={() => void load()} type="button">
            Refresh
          </button>
        </div>
        {error ? <p className="error-text">{error}</p> : null}
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Topic</th>
                <th>Status</th>
                <th>Comments</th>
                <th>Participants</th>
                <th>Moderation</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td className="empty-state" colSpan={5}>
                    Loading conversations…
                  </td>
                </tr>
              ) : conversations.length === 0 ? (
                <tr>
                  <td className="empty-state" colSpan={5}>
                    No conversations found yet.
                  </td>
                </tr>
              ) : (
                conversations.map((conversation) => (
                  <tr key={conversation.id}>
                    <td>
                      <strong>{conversation.topic}</strong>
                      <div className="table-subtext">{conversation.description ?? 'No description'}</div>
                    </td>
                    <td>{conversation.is_open ? 'Open' : 'Closed'}</td>
                    <td>{conversation.comments ?? '—'}</td>
                    <td>{conversation.participants ?? '—'}</td>
                    <td>{conversation.moderation_required ? 'Required' : 'Optional'}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className="panel-card">
        <div className="table-header">
          <h3>Create conversation</h3>
          <span className="muted">Uses the existing Deliberation FastAPI service</span>
        </div>
        <form className="form-grid" onSubmit={handleSubmit}>
          <label className="field">
            <span>Topic</span>
            <input
              minLength={3}
              onChange={(event) =>
                setFormState((current) => ({ ...current, topic: event.target.value }))
              }
              value={formState.topic}
            />
          </label>
          <label className="field field--full">
            <span>Description</span>
            <textarea
              onChange={(event) =>
                setFormState((current) => ({
                  ...current,
                  description: event.target.value,
                }))
              }
              rows={4}
              value={formState.description}
            />
          </label>
          <div className="checkbox-row field--full">
            <label>
              <input
                checked={formState.is_open}
                onChange={(event) =>
                  setFormState((current) => ({
                    ...current,
                    is_open: event.target.checked,
                  }))
                }
                type="checkbox"
              />
              Open now
            </label>
            <label>
              <input
                checked={formState.allow_comment_submission}
                onChange={(event) =>
                  setFormState((current) => ({
                    ...current,
                    allow_comment_submission: event.target.checked,
                  }))
                }
                type="checkbox"
              />
              Allow comments
            </label>
            <label>
              <input
                checked={formState.allow_viz}
                onChange={(event) =>
                  setFormState((current) => ({
                    ...current,
                    allow_viz: event.target.checked,
                  }))
                }
                type="checkbox"
              />
              Allow visualizations
            </label>
            <label>
              <input
                checked={formState.moderation_required}
                onChange={(event) =>
                  setFormState((current) => ({
                    ...current,
                    moderation_required: event.target.checked,
                  }))
                }
                type="checkbox"
              />
              Moderation required
            </label>
          </div>
          <div className="form-actions">
            <button disabled={creating || formState.topic.trim().length < 3} type="submit">
              {creating ? 'Creating…' : 'Create conversation'}
            </button>
          </div>
        </form>
      </section>
    </div>
  )
}
