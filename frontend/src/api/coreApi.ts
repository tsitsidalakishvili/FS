import {
  coreApiBaseUrl,
  fetchJson,
} from './http'
import type {
  DueDiligenceSubjectSearchResponse,
  InvestigationSearchResponse,
  PersonSearchResponse,
} from '../types/api'

const ensureBaseUrl = () => {
  if (!coreApiBaseUrl) {
    throw new Error('VITE_CORE_API_URL is not configured.')
  }
  return coreApiBaseUrl
}

export function searchPeople(query: string) {
  const baseUrl = ensureBaseUrl()
  const params = new URLSearchParams({ query })
  return fetchJson<PersonSearchResponse>(
    `${baseUrl}/api/v1/crm/people/search?${params.toString()}`,
  )
}

export function searchDueDiligenceSubjects(query: string) {
  const baseUrl = ensureBaseUrl()
  const params = new URLSearchParams({ query })
  return fetchJson<DueDiligenceSubjectSearchResponse>(
    `${baseUrl}/api/v1/due-diligence/subjects/search?${params.toString()}`,
  )
}

export function listSubjectInvestigations(subjectId: string) {
  const baseUrl = ensureBaseUrl()
  return fetchJson<InvestigationSearchResponse>(
    `${baseUrl}/api/v1/due-diligence/subjects/${encodeURIComponent(subjectId)}/investigations`,
  )
}

export function getCoreApiHealth() {
  const baseUrl = ensureBaseUrl()
  return fetchJson<{ status: string; service: string; environment: string }>(
    `${baseUrl}/healthz`,
  )
}
