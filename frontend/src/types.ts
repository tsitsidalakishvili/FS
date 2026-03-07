export type Person = {
  personId: string
  email: string
  firstName?: string
  lastName?: string
  phone?: string
  status: 'ACTIVE' | 'ARCHIVED' | string
  createdAt: string
  updatedAt: string
}

export type Task = {
  taskId: string
  personId: string
  title: string
  ownerId: string
  status: 'Open' | 'In Progress' | 'Done' | 'Cancelled' | string
  description?: string
  dueDate?: string
  createdAt: string
  updatedAt: string
}

export type Event = {
  eventId: string
  eventKey: string
  name: string
  published: boolean
  createdAt: string
  updatedAt: string
}

export type EventRegistration = {
  registrationId: string
  personId: string
  status: string
  createdAt: string
}

export type DeepLinkResponse = {
  token: string
  expiresAt: string
}

export type PublicRegistrationResponse = {
  registrationId: string
  eventId: string
  status: string
  createdAt: string
}

