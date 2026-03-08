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

export type Conversation = {
  id: string
  topic: string
  description?: string
  is_open: boolean
  allow_comment_submission: boolean
  allow_viz: boolean
  moderation_required: boolean
  created_at?: string
  comments?: number
  participants?: number
}

export type ConversationComment = {
  id: string
  text: string
  status: 'pending' | 'approved' | 'rejected' | string
  is_seed: boolean
  created_at?: string
  agree_count: number
  disagree_count: number
  pass_count: number
}

