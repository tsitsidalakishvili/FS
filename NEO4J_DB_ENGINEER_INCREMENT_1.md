# Increment 1 Rewrite: Neo4j DBMS Artifact

## Scope alignment (Increment 1)
- In scope: `Person`, `Task`, `Event`, `Registration`, deep-link resolution for public event signup.
- Single-tenant assumption.
- Soft archive for people (no hard delete for people).
- Audit fields on all mutable entities: `createdAt`, `updatedAt`, `createdBy`, `updatedBy`.

---

## 1) Approved graph model (nodes / relationships / properties)

### 1.1 Nodes

#### `(:Person)`
Core identity and CRM profile.

Required properties:
- `personId: STRING` (UUID, immutable)
- `email: STRING` (normalized lowercase, unique)
- `status: STRING` (`ACTIVE` | `ARCHIVED`)
- `createdAt: DATETIME`
- `updatedAt: DATETIME`
- `createdBy: STRING`
- `updatedBy: STRING`

Optional properties:
- `firstName: STRING`
- `lastName: STRING`
- `phone: STRING`
- `gender: STRING`
- `age: INTEGER`
- `timeAvailability: STRING`
- `about: STRING`
- `agreesWithManifesto: BOOLEAN`
- `interestedInMembership: BOOLEAN`
- `facebookGroupMember: BOOLEAN`
- `archivedAt: DATETIME`
- `archivedBy: STRING`

---

#### `(:Task)`
Follow-up work item linked to a person record.

Required properties:
- `taskId: STRING` (UUID, unique)
- `title: STRING`
- `status: STRING` (`Open` | `In Progress` | `Done` | `Cancelled`)
- `ownerId: STRING` (backend auth principal id)
- `createdAt: DATETIME`
- `updatedAt: DATETIME`
- `createdBy: STRING`
- `updatedBy: STRING`

Optional properties:
- `description: STRING`
- `dueDate: DATE`

---

#### `(:Event)`
Event definition and publication metadata.

Required properties:
- `eventId: STRING` (UUID, unique)
- `eventKey: STRING` (stable external key, unique)
- `name: STRING`
- `published: BOOLEAN`
- `status: STRING` (`Planned` | `Scheduled` | `Completed` | `Cancelled`)
- `createdAt: DATETIME`
- `updatedAt: DATETIME`
- `createdBy: STRING`
- `updatedBy: STRING`

Optional properties:
- `startDate: DATE`
- `endDate: DATE`
- `location: STRING`
- `capacity: INTEGER`
- `notes: STRING`

---

#### `(:Registration)`
Event signup record (first-class node for auditability and dedupe).

Required properties:
- `registrationId: STRING` (UUID, unique)
- `registrationKey: STRING` (`<eventId>|<email>`, unique idempotency key)
- `status: STRING` (`Registered` | `Attended` | `Cancelled` | `No Show`)
- `registeredAt: DATETIME`
- `createdAt: DATETIME`
- `updatedAt: DATETIME`
- `createdBy: STRING`
- `updatedBy: STRING`

Optional properties:
- `notes: STRING`
- `source: STRING` (`crm_internal` | `public_deeplink`)

---

#### `(:DeepLink)`
Public registration link token metadata and lifecycle controls.

Required properties:
- `linkId: STRING` (UUID, unique)
- `tokenHash: STRING` (hash of opaque token, unique)
- `purpose: STRING` (`EVENT_REGISTRATION`)
- `active: BOOLEAN`
- `createdAt: DATETIME`
- `createdBy: STRING`

Optional properties:
- `expiresAt: DATETIME`
- `maxUses: INTEGER`
- `useCount: INTEGER`
- `revokedAt: DATETIME`
- `revokedBy: STRING`

---

### 1.2 Relationships
- `(:Person)-[:HAS_TASK]->(:Task)`
- `(:Person)-[:SUBMITTED]->(:Registration)`
- `(:Registration)-[:FOR_EVENT]->(:Event)`
- `(:Registration)-[:CREATED_VIA]->(:DeepLink)` (optional)
- `(:DeepLink)-[:RESOLVES_TO]->(:Event)`

Model decision:
- Registration is a node (not only a relationship property) to support robust audit fields, dedupe keys, and deep-link provenance.

---

## 2) Required constraints and indexes

> Neo4j 5 syntax, deploy once in migration step.

```cypher
CREATE CONSTRAINT person_email_unique IF NOT EXISTS
FOR (p:Person) REQUIRE p.email IS UNIQUE;

CREATE CONSTRAINT person_id_unique IF NOT EXISTS
FOR (p:Person) REQUIRE p.personId IS UNIQUE;

CREATE CONSTRAINT task_id_unique IF NOT EXISTS
FOR (t:Task) REQUIRE t.taskId IS UNIQUE;

CREATE CONSTRAINT event_id_unique IF NOT EXISTS
FOR (e:Event) REQUIRE e.eventId IS UNIQUE;

CREATE CONSTRAINT event_key_unique IF NOT EXISTS
FOR (e:Event) REQUIRE e.eventKey IS UNIQUE;

CREATE CONSTRAINT registration_id_unique IF NOT EXISTS
FOR (r:Registration) REQUIRE r.registrationId IS UNIQUE;

CREATE CONSTRAINT registration_key_unique IF NOT EXISTS
FOR (r:Registration) REQUIRE r.registrationKey IS UNIQUE;

CREATE CONSTRAINT deeplink_id_unique IF NOT EXISTS
FOR (d:DeepLink) REQUIRE d.linkId IS UNIQUE;

CREATE CONSTRAINT deeplink_tokenhash_unique IF NOT EXISTS
FOR (d:DeepLink) REQUIRE d.tokenHash IS UNIQUE;
```

```cypher
CREATE INDEX person_status_idx IF NOT EXISTS
FOR (p:Person) ON (p.status);

CREATE INDEX task_owner_status_due_idx IF NOT EXISTS
FOR (t:Task) ON (t.ownerId, t.status, t.dueDate);

CREATE INDEX event_publish_start_idx IF NOT EXISTS
FOR (e:Event) ON (e.published, e.startDate);

CREATE INDEX registration_status_idx IF NOT EXISTS
FOR (r:Registration) ON (r.status);

CREATE INDEX deeplink_active_expiry_idx IF NOT EXISTS
FOR (d:DeepLink) ON (d.active, d.expiresAt);
```

---

## 3) Cypher catalog for core API operations

### 3.1 People

#### Create or update person (idempotent on `email`)
```cypher
MERGE (p:Person {email: toLower(trim($email))})
ON CREATE SET
  p.personId = randomUUID(),
  p.status = 'ACTIVE',
  p.createdAt = datetime(),
  p.createdBy = $actorId
SET
  p.firstName = $firstName,
  p.lastName = $lastName,
  p.phone = $phone,
  p.gender = $gender,
  p.age = $age,
  p.timeAvailability = $timeAvailability,
  p.about = $about,
  p.agreesWithManifesto = coalesce($agreesWithManifesto, false),
  p.interestedInMembership = coalesce($interestedInMembership, false),
  p.facebookGroupMember = coalesce($facebookGroupMember, false),
  p.updatedAt = datetime(),
  p.updatedBy = $actorId
RETURN p;
```

#### List/search people (active by default)
```cypher
MATCH (p:Person)
WHERE ($includeArchived = true OR p.status = 'ACTIVE')
  AND (
    $q IS NULL OR $q = '' OR
    toLower(coalesce(p.email, '')) CONTAINS toLower($q) OR
    toLower(trim(coalesce(p.firstName,'') + ' ' + coalesce(p.lastName,''))) CONTAINS toLower($q)
  )
RETURN p
ORDER BY coalesce(p.lastName, ''), coalesce(p.firstName, ''), p.email
LIMIT $limit;
```

#### Soft archive person
```cypher
MATCH (p:Person {email: toLower(trim($email))})
SET p.status = 'ARCHIVED',
    p.archivedAt = datetime(),
    p.archivedBy = $actorId,
    p.updatedAt = datetime(),
    p.updatedBy = $actorId
RETURN p.personId AS personId, p.status AS status;
```

---

### 3.2 Tasks

#### Create task linked to person
```cypher
MATCH (p:Person {email: toLower(trim($email))})
WHERE p.status = 'ACTIVE'
CREATE (t:Task {
  taskId: randomUUID(),
  title: $title,
  description: $description,
  status: coalesce($status, 'Open'),
  dueDate: CASE WHEN $dueDate IS NULL OR $dueDate = '' THEN NULL ELSE date($dueDate) END,
  ownerId: $ownerId,
  createdAt: datetime(),
  updatedAt: datetime(),
  createdBy: $actorId,
  updatedBy: $actorId
})
MERGE (p)-[:HAS_TASK]->(t)
RETURN t.taskId AS taskId;
```

#### List tasks by owner/status
```cypher
MATCH (p:Person)-[:HAS_TASK]->(t:Task)
WHERE ($ownerId IS NULL OR t.ownerId = $ownerId)
  AND ($status IS NULL OR t.status = $status)
RETURN t, p.email AS personEmail, p.firstName AS firstName, p.lastName AS lastName
ORDER BY
  CASE WHEN t.status = 'Done' THEN 1 WHEN t.status = 'Cancelled' THEN 2 ELSE 0 END,
  coalesce(t.dueDate, date('9999-12-31')) ASC,
  t.createdAt DESC
LIMIT $limit;
```

#### Update task status
```cypher
MATCH (t:Task {taskId: $taskId})
SET t.status = $status,
    t.updatedAt = datetime(),
    t.updatedBy = $actorId
RETURN t.taskId AS taskId, t.status AS status;
```

---

### 3.3 Events

#### Create event
```cypher
CREATE (e:Event {
  eventId: randomUUID(),
  eventKey: $eventKey,
  name: $name,
  startDate: CASE WHEN $startDate IS NULL OR $startDate = '' THEN NULL ELSE date($startDate) END,
  endDate: CASE WHEN $endDate IS NULL OR $endDate = '' THEN NULL ELSE date($endDate) END,
  location: $location,
  status: coalesce($status, 'Planned'),
  capacity: coalesce($capacity, 0),
  notes: $notes,
  published: coalesce($published, false),
  createdAt: datetime(),
  updatedAt: datetime(),
  createdBy: $actorId,
  updatedBy: $actorId
})
RETURN e.eventId AS eventId, e.eventKey AS eventKey;
```

#### Publish/unpublish event
```cypher
MATCH (e:Event {eventId: $eventId})
SET e.published = $published,
    e.updatedAt = datetime(),
    e.updatedBy = $actorId
RETURN e.eventId AS eventId, e.published AS published;
```

---

### 3.4 Deep link generation + resolve

#### Create deep link token metadata (token is generated in backend; only hash stored)
```cypher
MATCH (e:Event {eventId: $eventId})
CREATE (d:DeepLink {
  linkId: randomUUID(),
  tokenHash: $tokenHash,
  purpose: 'EVENT_REGISTRATION',
  active: true,
  expiresAt: $expiresAt,
  maxUses: $maxUses,
  useCount: 0,
  createdAt: datetime(),
  createdBy: $actorId
})
MERGE (d)-[:RESOLVES_TO]->(e)
RETURN d.linkId AS linkId;
```

#### Resolve deep link (public)
```cypher
MATCH (d:DeepLink {tokenHash: $tokenHash, active: true})-[:RESOLVES_TO]->(e:Event)
WHERE e.published = true
  AND (d.expiresAt IS NULL OR d.expiresAt >= datetime())
  AND (d.maxUses IS NULL OR coalesce(d.useCount, 0) < d.maxUses)
RETURN d, e
LIMIT 1;
```

---

### 3.5 Registrations

#### Create registration from public link (idempotent per event+email)
```cypher
MATCH (e:Event {eventId: $eventId})
MERGE (p:Person {email: toLower(trim($email))})
ON CREATE SET
  p.personId = randomUUID(),
  p.status = 'ACTIVE',
  p.createdAt = datetime(),
  p.createdBy = 'public_registration'
SET
  p.firstName = coalesce($firstName, p.firstName),
  p.lastName = coalesce($lastName, p.lastName),
  p.phone = coalesce($phone, p.phone),
  p.updatedAt = datetime(),
  p.updatedBy = 'public_registration'
WITH e, p, ($eventId + '|' + toLower(trim($email))) AS rk
MERGE (r:Registration {registrationKey: rk})
ON CREATE SET
  r.registrationId = randomUUID(),
  r.registeredAt = datetime(),
  r.createdAt = datetime(),
  r.createdBy = 'public_registration'
SET
  r.status = coalesce($status, 'Registered'),
  r.notes = $notes,
  r.source = 'public_deeplink',
  r.updatedAt = datetime(),
  r.updatedBy = 'public_registration'
MERGE (p)-[:SUBMITTED]->(r)
MERGE (r)-[:FOR_EVENT]->(e)
WITH r, e
OPTIONAL MATCH (d:DeepLink {tokenHash: $tokenHash})-[:RESOLVES_TO]->(e)
FOREACH (_ IN CASE WHEN d IS NULL THEN [] ELSE [1] END |
  MERGE (r)-[:CREATED_VIA]->(d)
  SET d.useCount = coalesce(d.useCount, 0) + 1
)
RETURN r.registrationId AS registrationId, r.status AS status;
```

#### List registrations for event
```cypher
MATCH (r:Registration)-[:FOR_EVENT]->(e:Event {eventId: $eventId})
MATCH (p:Person)-[:SUBMITTED]->(r)
RETURN
  r.registrationId AS registrationId,
  p.email AS email,
  p.firstName AS firstName,
  p.lastName AS lastName,
  p.phone AS phone,
  r.status AS registrationStatus,
  r.notes AS notes,
  r.registeredAt AS registeredAt,
  r.updatedAt AS updatedAt
ORDER BY r.updatedAt DESC
LIMIT $limit;
```

---

## 4) Data boundary contract with backend

### 4.1 Ownership boundaries
- Backend service is the **only writer** to Neo4j in production.
- UI/clients send validated DTOs; they do not send raw Cypher.
- Backend enforces normalization (email lowercasing/trimming, status enum checks, date parsing, default values).
- Backend sets audit fields and actor identity from auth context.

### 4.2 Contracted payloads (minimum)

#### People
- `POST /people`
  - Request: `{email, firstName?, lastName?, phone?, gender?, age?, timeAvailability?, about?, agreesWithManifesto?, interestedInMembership?, facebookGroupMember?}`
  - Response: `{personId, email, status, createdAt, updatedAt}`
- `PATCH /people/{email}`
  - Request: partial updatable fields above
  - Response: updated person projection
- `POST /people/{email}/archive`
  - Request: `{reason?}`
  - Response: `{personId, status: "ARCHIVED"}`

#### Tasks
- `POST /tasks`
  - Request: `{personEmail, title, description?, dueDate?, status?, ownerId}`
  - Response: `{taskId}`
- `PATCH /tasks/{taskId}/status`
  - Request: `{status}`
  - Response: `{taskId, status}`
- `GET /tasks?ownerId=&status=&limit=`
  - Response: paged task list with linked person summary

#### Events and deep links
- `POST /events`
  - Request: `{eventKey, name, startDate?, endDate?, location?, status?, capacity?, notes?, published?}`
  - Response: `{eventId, eventKey}`
- `POST /events/{eventId}/publish`
  - Request: `{published: boolean}`
  - Response: `{eventId, published}`
- `POST /events/{eventId}/deeplinks`
  - Request: `{ttlHours?, maxUses?}`
  - Response: `{linkId, url, expiresAt}`
- `GET /deeplinks/{token}/resolve`
  - Response: `{eventId, eventKey, name, startDate, location, registrationOpen}`

#### Registrations
- `POST /events/{eventId}/registrations` (internal)
- `POST /public/registrations` (via deep link)
  - Request: `{token, email, fullName|firstName+lastName, phone?, notes?}`
  - Response: `{registrationId, status}`

### 4.3 Behavioral rules
- Registration writes are idempotent by `registrationKey = eventId|email`.
- Capacity check must run in backend transaction before final registration write.
- Archived people are excluded from default people search/list APIs.
- For deep links, store only `tokenHash` (never raw token) in Neo4j.

---

## 5) Migration and backfill approach

### Phase A: Schema deployment
1. Apply constraints and indexes (Section 2).
2. Deploy new write paths in backend (dual-read compatibility enabled).

### Phase B: Dual-write compatibility window
1. New registration writes create `:Registration` node model.
2. Keep legacy `(:Person)-[:REGISTERED_FOR]->(:Event)` reads temporarily for fallback.
3. New reads prefer `:Registration`; fallback to legacy relationship if none exists.

### Phase C: Backfill legacy registrations
Run once, idempotent:

```cypher
MATCH (p:Person)-[rf:REGISTERED_FOR]->(e:Event)
WITH p, e, rf, (e.eventId + '|' + toLower(trim(p.email))) AS rk
MERGE (r:Registration {registrationKey: rk})
ON CREATE SET
  r.registrationId = randomUUID(),
  r.registeredAt = coalesce(rf.registeredAt, datetime()),
  r.createdAt = coalesce(rf.registeredAt, datetime()),
  r.createdBy = 'migration_backfill'
SET
  r.status = coalesce(rf.status, 'Registered'),
  r.notes = coalesce(rf.notes, ''),
  r.source = coalesce(r.source, 'legacy_relationship'),
  r.updatedAt = datetime(),
  r.updatedBy = 'migration_backfill'
MERGE (p)-[:SUBMITTED]->(r)
MERGE (r)-[:FOR_EVENT]->(e);
```

### Phase D: Cutover
1. Remove fallback reads to legacy relationship.
2. Optionally delete legacy `REGISTERED_FOR` relationship after reconciliation signoff.

### Rollback plan
- Keep migration scripts idempotent.
- If needed, revert read preference to legacy edges while keeping newly created registration nodes (non-destructive rollback).

---

## 6) Data quality checks

Run as scheduled checks (daily + pre-release gate).

### 6.1 Duplicate/identity checks
```cypher
MATCH (p:Person)
WITH toLower(trim(p.email)) AS email, count(*) AS c
WHERE email <> '' AND c > 1
RETURN email, c;
```
Expected: zero rows.

### 6.2 Orphan tasks
```cypher
MATCH (t:Task)
WHERE NOT ( (:Person)-[:HAS_TASK]->(t) )
RETURN count(t) AS orphanTasks;
```
Expected: `0`.

### 6.3 Orphan registrations
```cypher
MATCH (r:Registration)
WHERE NOT ( (:Person)-[:SUBMITTED]->(r) )
   OR NOT ( (r)-[:FOR_EVENT]->(:Event) )
RETURN count(r) AS orphanRegistrations;
```
Expected: `0`.

### 6.4 Invalid enum values
```cypher
MATCH (t:Task)
WHERE NOT t.status IN ['Open', 'In Progress', 'Done', 'Cancelled']
RETURN count(t) AS invalidTaskStatuses;
```
Expected: `0`.

```cypher
MATCH (r:Registration)
WHERE NOT r.status IN ['Registered', 'Attended', 'Cancelled', 'No Show']
RETURN count(r) AS invalidRegistrationStatuses;
```
Expected: `0`.

### 6.5 Event capacity breaches
```cypher
MATCH (e:Event)<-[:FOR_EVENT]-(r:Registration)
WHERE coalesce(e.capacity, 0) > 0
WITH e, count(r) AS regCount
WHERE regCount > e.capacity
RETURN e.eventId AS eventId, e.name AS eventName, e.capacity AS capacity, regCount;
```
Expected: zero rows unless explicit overbook policy is enabled.

### 6.6 Deep-link hygiene
```cypher
MATCH (d:DeepLink)
WHERE d.active = true
  AND d.expiresAt IS NOT NULL
  AND d.expiresAt < datetime()
RETURN count(d) AS expiredStillActive;
```
Expected: `0`.

### 6.7 Audit completeness
```cypher
MATCH (n)
WHERE any(label IN labels(n) WHERE label IN ['Person','Task','Event','Registration'])
  AND (
    n.createdAt IS NULL OR n.updatedAt IS NULL OR
    n.createdBy IS NULL OR n.updatedBy IS NULL
  )
RETURN labels(n) AS labels, count(*) AS missingAuditCount;
```
Expected: zero rows.

---

Neo4jDBEngineer Gate: PASS — all required sections are present with an implementable Neo4j model, constraints/indexes, Cypher operation catalog, backend contract, migration/backfill plan, and data-quality checks aligned to Increment 1.
