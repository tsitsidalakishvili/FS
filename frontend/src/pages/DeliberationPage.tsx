import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import {
  ApiError,
  createConversation,
  createConversationComment,
  listConversationComments,
  listConversations,
} from '../api'
import type { Conversation, ConversationComment } from '../types'

export function DeliberationPage() {
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [selectedConversationId, setSelectedConversationId] = useState('')
  const [comments, setComments] = useState<ConversationComment[]>([])
  const [topic, setTopic] = useState('')
  const [description, setDescription] = useState('')
  const [commentText, setCommentText] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function loadConversations() {
    setLoading(true)
    setError('')
    try {
      const rows = await listConversations()
      setConversations(rows)
      if (!selectedConversationId && rows[0]) {
        setSelectedConversationId(rows[0].id)
      }
    } catch (err) {
      const detail = err instanceof ApiError ? err.message : 'Failed loading deliberation data'
      setError(detail)
    } finally {
      setLoading(false)
    }
  }

  async function loadComments(conversationId: string) {
    if (!conversationId) {
      setComments([])
      return
    }
    try {
      const rows = await listConversationComments(conversationId)
      setComments(rows)
    } catch (err) {
      const detail = err instanceof ApiError ? err.message : 'Failed loading comments'
      setError(detail)
    }
  }

  useEffect(() => {
    void loadConversations()
  }, [])

  useEffect(() => {
    void loadComments(selectedConversationId)
  }, [selectedConversationId])

  async function onCreateConversation(e: FormEvent) {
    e.preventDefault()
    setError('')
    try {
      await createConversation({ topic, description: description || undefined })
      setTopic('')
      setDescription('')
      await loadConversations()
    } catch (err) {
      const detail = err instanceof ApiError ? err.message : 'Conversation create failed'
      setError(detail)
    }
  }

  async function onCreateComment(e: FormEvent) {
    e.preventDefault()
    if (!selectedConversationId) return
    setError('')
    try {
      await createConversationComment(selectedConversationId, commentText)
      setCommentText('')
      await loadComments(selectedConversationId)
    } catch (err) {
      const detail = err instanceof ApiError ? err.message : 'Comment submit failed'
      setError(detail)
    }
  }

  return (
    <section>
      <h2>Deliberation</h2>
      <p>Parity mode with deliberation FastAPI service.</p>
      <div className="toolbar">
        <button onClick={() => void loadConversations()} disabled={loading}>
          {loading ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>
      {error ? <p className="error">{error}</p> : null}

      <div className="two-col">
        <div>
          <h3>Conversations</h3>
          <form onSubmit={onCreateConversation} className="stack">
            <input value={topic} onChange={(e) => setTopic(e.target.value)} placeholder="Topic" required />
            <textarea
              rows={2}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Description"
            />
            <button type="submit">Create conversation</button>
          </form>
          <table>
            <thead>
              <tr>
                <th>Topic</th>
                <th>Comments</th>
              </tr>
            </thead>
            <tbody>
              {conversations.map((item) => (
                <tr
                  key={item.id}
                  className={selectedConversationId === item.id ? 'selected-row' : ''}
                  onClick={() => setSelectedConversationId(item.id)}
                >
                  <td>{item.topic}</td>
                  <td>{item.comments || 0}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div>
          <h3>Comments</h3>
          <form onSubmit={onCreateComment} className="stack">
            <textarea
              rows={3}
              value={commentText}
              onChange={(e) => setCommentText(e.target.value)}
              placeholder="Add comment"
              required
            />
            <button type="submit" disabled={!selectedConversationId}>
              Submit comment
            </button>
          </form>
          <table>
            <thead>
              <tr>
                <th>Comment</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {comments.map((item) => (
                <tr key={item.id}>
                  <td>{item.text}</td>
                  <td>{item.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {selectedConversationId && comments.length === 0 ? <p>No comments yet.</p> : null}
        </div>
      </div>
    </section>
  )
}

