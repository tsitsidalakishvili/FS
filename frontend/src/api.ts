import { buildInternalHeaders } from './authHeaders'
import type {
  DeepLinkResponse,
  Event,
  EventRegistration,
  Person,
  PublicRegistrationResponse,
  Task,
} from './types'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8020/api/v1'

export class ApiError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.status = status
  }
}

async function request<T>(
  path: string,
  init: RequestInit = {},
  opts: { internal?: boolean } = {},
): Promise<T> {
  const headers = new Headers(init.headers || {})
  headers.set('Content-Type', 'application/json')
  if (opts.internal !== false) {
    const internalHeaders = buildInternalHeaders()
    Object.entries(internalHeaders).forEach(([k, v]) => headers.set(k, v))
  }
  const response = await fetch(`${API_BASE_URL}${path}`, { ...init, headers })
  if (!response.ok) {
    let detail = `Request failed (${response.status})`
    try {
      const payload = (await response.json()) as { detail?: string }
      if (payload.detail) detail = payload.detail
    } catch {
      // use default detail
    }
    throw new ApiError(detail, response.status)
  }
  return (await response.json()) as T
}

export async function listPeople(params: {
  q?: string
  includeArchived?: boolean
  limit?: number
}): Promise<Person[]> {
  const q = new URLSearchParams()
  if (params.q) q.set('q', params.q)
  if (params.includeArchived) q.set('includeArchived', 'true')
  q.set('limit', String(params.limit || 100))
  return request<Person[]>(`/people?${q.toString()}`)
}

export async function createPerson(payload: {
  email: string
  firstName?: string
  lastName?: string
  phone?: string
}): Promise<Person> {
  return request<Person>('/people', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function patchPerson(
  personId: string,
  payload: Partial<{ firstName: string; lastName: string; phone: string; status: string }>,
): Promise<Person> {
  return request<Person>(`/people/${personId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export async function listTasks(params: {
  status?: string
  ownerId?: string
  limit?: number
}): Promise<Task[]> {
  const q = new URLSearchParams()
  if (params.status) q.set('status', params.status)
  if (params.ownerId) q.set('ownerId', params.ownerId)
  q.set('limit', String(params.limit || 200))
  return request<Task[]>(`/tasks?${q.toString()}`)
}

export async function createTask(payload: {
  personId: string
  title: string
  ownerId: string
  description?: string
  dueDate?: string
}): Promise<Task> {
  return request<Task>('/tasks', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function patchTaskStatus(taskId: string, status: string): Promise<Task> {
  return request<Task>(`/tasks/${taskId}/status`, {
    method: 'PATCH',
    body: JSON.stringify({ status }),
  })
}

export async function createEvent(payload: {
  eventKey: string
  name: string
  published?: boolean
}): Promise<Event> {
  return request<Event>('/events', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function getEvent(eventId: string): Promise<Event> {
  return request<Event>(`/events/${eventId}`)
}

export async function createDeepLink(
  eventId: string,
  payload: { subjectPersonId: string; expiresInHours: number },
): Promise<DeepLinkResponse> {
  return request<DeepLinkResponse>(`/events/${eventId}/deeplinks`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function listEventRegistrations(
  eventId: string,
  limit: number,
): Promise<EventRegistration[]> {
  return request<EventRegistration[]>(`/events/${eventId}/registrations?limit=${limit}`)
}

export async function submitPublicRegistration(payload: {
  token: string
  status: string
  guestCount?: number
  accessibilityNeeds?: string
  consentVersion?: string
  notes?: string
}): Promise<PublicRegistrationResponse> {
  return request<PublicRegistrationResponse>(
    '/public/registrations',
    {
      method: 'POST',
      body: JSON.stringify(payload),
    },
    { internal: false },
  )
}

