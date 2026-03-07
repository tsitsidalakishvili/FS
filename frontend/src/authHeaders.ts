const ACTOR_ID_KEY = 'crm_actor_id'
const ACTOR_ROLE_KEY = 'crm_actor_role'

export type ActorIdentity = {
  actorId: string
  actorRole: string
}

export function loadActorIdentity(): ActorIdentity {
  const actorId = localStorage.getItem(ACTOR_ID_KEY) || 'supervisor-1'
  const actorRole = localStorage.getItem(ACTOR_ROLE_KEY) || 'platform_admin'
  return { actorId, actorRole }
}

export function saveActorIdentity(identity: ActorIdentity): void {
  localStorage.setItem(ACTOR_ID_KEY, identity.actorId)
  localStorage.setItem(ACTOR_ROLE_KEY, identity.actorRole)
}

export function buildInternalHeaders(): Record<string, string> {
  const { actorId, actorRole } = loadActorIdentity()
  return {
    'x-actor-id': actorId,
    'x-actor-role': actorRole,
  }
}

