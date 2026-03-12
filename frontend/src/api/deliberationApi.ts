import { deliberationApiBaseUrl, fetchJson } from './http'
import type { ConversationSummary } from '../types/api'

const ensureBaseUrl = () => {
  if (!deliberationApiBaseUrl) {
    throw new Error('VITE_DELIBERATION_API_URL is not configured.')
  }
  return deliberationApiBaseUrl
}

export function listConversations() {
  const baseUrl = ensureBaseUrl()
  return fetchJson<ConversationSummary[]>(`${baseUrl}/conversations`)
}

export function createConversation(payload: {
  topic: string
  description?: string
  is_open: boolean
  allow_comment_submission: boolean
  allow_viz: boolean
  moderation_required: boolean
}) {
  const baseUrl = ensureBaseUrl()
  return fetchJson<ConversationSummary>(`${baseUrl}/conversations`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function getDeliberationApiHealth() {
  const baseUrl = ensureBaseUrl()
  return fetchJson<{ status: string; db: string }>(`${baseUrl}/healthz`)
}
