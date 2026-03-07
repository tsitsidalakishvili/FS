# Stage 4 — Neo4jDBEngineer Route-Back Remediation

## Scope
Database-layer remediations for security gate blockers:
1. token-bound registration (event resolved only from token)
2. no public mutation of canonical `Person` fields
3. authZ/audit fields required at DB write boundaries
4. retention/anonymization + DSAR Cypher operations
5. data-integrity checks proving controls are working

---

## 1) Token-bound registration Cypher pattern (event resolved only from token)

### Required schema controls
```cypher
CREATE CONSTRAINT deep_link_token_hash_unique IF NOT EXISTS
FOR (t:DeepLinkToken) REQUIRE t.tokenHash IS UNIQUE;

CREATE CONSTRAINT token_use_jti_unique IF NOT EXISTS
FOR (u:TokenUse) REQUIRE u.jti IS UNIQUE;

CREATE CONSTRAINT registration_key_unique IF NOT EXISTS
FOR (r:Registration) REQUIRE r.registrationKey IS UNIQUE;

CREATE CONSTRAINT person_id_unique IF NOT EXISTS
FOR (p:Person) REQUIRE p.personId IS UNIQUE;

CREATE CONSTRAINT event_id_unique IF NOT EXISTS
FOR (e:Event) REQUIRE e.eventId IS UNIQUE;
```

### Public registration write query (single transaction)
**Contract:** repository accepts `tokenHash`, `registrationInput`, and `ctx`.  
**Contract:** repository does **not** accept `eventId` from caller.

```cypher
// Params:
// $tokenHash: STRING
// $registrationInput: { status, guestCount, accessibilityNeeds, consentVersion, notes }
// $ctx: { requestId, traceId, actorType, actorId, tokenJti, route, method, ipHash, uaHash,
//         authzDecision, authzPolicyId, authzPolicyVersion, decisionReason }

MATCH (t:DeepLinkToken {tokenHash: $tokenHash})
WHERE t.status = 'ACTIVE'
  AND t.expiresAt > datetime()
  AND t.aud = 'public-registration'
  AND 'registration:write' IN t.scopes
WITH t

// Replay protection: only first requestId for a jti is accepted
MERGE (u:TokenUse {jti: t.jti})
  ON CREATE SET
    u.requestId = $ctx.requestId,
    u.usedAt = datetime(),
    u.tokenHash = $tokenHash
WITH t, u
WHERE u.requestId = $ctx.requestId

// Event is resolved strictly from token claim/node, never from input payload
MATCH (e:Event {eventId: t.eventId})
MERGE (p:Person {personId: t.subjectPersonId})
  ON CREATE SET p.createdAt = datetime(), p.createdBy = 'public-registration-token'

MERGE (r:Registration {registrationKey: 'token:' + t.jti})
  ON CREATE SET
    r.registrationId = randomUUID(),
    r.channel = 'PUBLIC',
    r.sourceTokenJti = t.jti,
    r.createdAt = datetime(),
    r.createdBy = $ctx.actorId
SET
  r.status = coalesce($registrationInput.status, r.status),
  r.guestCount = coalesce($registrationInput.guestCount, r.guestCount),
  r.accessibilityNeeds = coalesce($registrationInput.accessibilityNeeds, r.accessibilityNeeds),
  r.consentVersion = coalesce($registrationInput.consentVersion, r.consentVersion),
  r.notes = coalesce($registrationInput.notes, r.notes),
  r.updatedAt = datetime(),
  r.updatedBy = $ctx.actorId,
  r.lastRequestId = $ctx.requestId,
  r.lastTraceId = $ctx.traceId

MERGE (p)-[:SUBMITTED]->(r)
MERGE (r)-[:FOR_EVENT]->(e)
SET
  t.status = 'CONSUMED',
  t.consumedAt = coalesce(t.consumedAt, datetime()),
  t.consumedByRequestId = coalesce(t.consumedByRequestId, $ctx.requestId)

CREATE (a:AuditLog {
  auditId: randomUUID(),
  occurredAt: datetime(),
  action: 'registration.public_upsert',
  outcome: 'ALLOW',
  requestId: $ctx.requestId,
  traceId: $ctx.traceId,
  actorType: $ctx.actorType,
  actorId: $ctx.actorId,
  tokenJti: t.jti,
  route: $ctx.route,
  method: $ctx.method,
  ipHash: $ctx.ipHash,
  uaHash: $ctx.uaHash,
  authzDecision: $ctx.authzDecision,
  authzPolicyId: $ctx.authzPolicyId,
  authzPolicyVersion: $ctx.authzPolicyVersion,
  decisionReason: $ctx.decisionReason,
  resourceType: 'Registration',
  resourceId: r.registrationId
})
MERGE (a)-[:TARGETS]->(r)
RETURN r.registrationId AS registrationId, e.eventId AS eventId;
```

**Security effect:** token validation + replay defense + event binding are in the same transaction, with `eventId` sourced only from token-linked data.

---

## 2) Prevent public mutation of canonical `Person` fields

### DB write-path separation rule
- Public flow query must never execute `SET p += $map` or `SET p.<canonicalField> = ...`.
- Public flow may only:
  - `MERGE (p:Person {personId: t.subjectPersonId})` for identity linkage
  - create/update `Registration` node properties
  - create relationships and audit records

### Neo4j privilege hardening (Enterprise)
```cypher
// Public writer can read person identity keys but cannot mutate person properties
DENY SET PROPERTY {*} ON GRAPH neo4j NODES Person TO public_registration_writer;
DENY CREATE ON GRAPH neo4j NODES Person TO public_registration_writer;
DENY DELETE ON GRAPH neo4j NODES Person TO public_registration_writer;

GRANT MATCH {*} ON GRAPH neo4j NODES Person TO public_registration_writer;
GRANT CREATE ON GRAPH neo4j NODES Registration TO public_registration_writer;
GRANT SET PROPERTY {*} ON GRAPH neo4j NODES Registration TO public_registration_writer;
```

### Canonical field contract
Canonical `Person` fields (`fullName`, `email`, `phone`, `address`, `dob`, `tags`, `internalNotes`) are internal-only and must be mutated only by internal service role/query path.

---

## 3) AuthZ/audit data fields required at DB write boundaries

### Required context parameter (`$ctx`) for every write query
- `requestId` (idempotency + audit correlation)
- `traceId`
- `actorType` (`human`, `service`, `public_token_subject`)
- `actorId` (user/service principal or token subject)
- `route`, `method`
- `ipHash`, `uaHash` (hashed client metadata)
- `authzDecision` (`ALLOW`/`DENY`)
- `authzPolicyId`, `authzPolicyVersion`, `decisionReason`
- `tokenJti` (for token-bound writes)
- `issuedAt`, `authnStrength` (recommended for internal writes)

### Required write metadata on mutable domain nodes
- `createdAt`, `createdBy`
- `updatedAt`, `updatedBy`
- `lastRequestId`, `lastTraceId`
- `writeChannel` (`PUBLIC`, `INTERNAL_API`, `BATCH_JOB`)

### Required immutable audit log fields
- `auditId`, `occurredAt`
- `action`, `outcome`, `resourceType`, `resourceId`
- `requestId`, `traceId`
- `actorType`, `actorId`
- `authzDecision`, `authzPolicyId`, `authzPolicyVersion`, `decisionReason`
- `tokenJti` (if applicable)

---

## 4) Retention/anonymization and DSAR Cypher operations

### 4.1 Expired deep-link token cleanup (30-day grace after expiry)
```cypher
MATCH (t:DeepLinkToken)
WHERE t.expiresAt < datetime() - duration('P30D')
DETACH DELETE t
RETURN count(*) AS deletedTokens;
```

### 4.2 Registration anonymization after event retention window (24 months)
```cypher
MATCH (r:Registration)-[:FOR_EVENT]->(e:Event)
WHERE e.endAt < datetime() - duration('P24M')
  AND coalesce(r.legalHold, false) = false
  AND r.anonymizedAt IS NULL
SET
  r.guestName = null,
  r.contactEmail = null,
  r.contactPhone = null,
  r.notes = null,
  r.accessibilityNeeds = null,
  r.contactEmailHash = CASE
    WHEN r.contactEmail IS NOT NULL THEN sha256(toString(r.contactEmail))
    ELSE r.contactEmailHash
  END,
  r.retentionState = 'ANONYMIZED',
  r.anonymizedAt = datetime(),
  r.updatedAt = datetime(),
  r.updatedBy = 'retention-job'
RETURN count(*) AS anonymizedRegistrations;
```

### 4.3 DSAR subject export (discovery/read phase)
```cypher
MATCH (p:Person {personId: $subjectPersonId})
OPTIONAL MATCH (p)-[:SUBMITTED]->(r:Registration)
OPTIONAL MATCH (r)-[:FOR_EVENT]->(e:Event)
RETURN
  p { .* } AS person,
  collect(DISTINCT r { .* }) AS registrations,
  collect(DISTINCT e { .eventId, .eventKey, .title, .startAt, .endAt }) AS events;
```

### 4.4 DSAR anonymization transaction (idempotent by jobId)
```cypher
CREATE CONSTRAINT dsar_job_id_unique IF NOT EXISTS
FOR (j:DSARJob) REQUIRE j.jobId IS UNIQUE;

MERGE (j:DSARJob {jobId: $jobId})
  ON CREATE SET
    j.subjectPersonId = $subjectPersonId,
    j.requestedAt = datetime(),
    j.status = 'STARTED'
WITH j
WHERE j.subjectPersonId = $subjectPersonId

MATCH (p:Person {personId: $subjectPersonId})
OPTIONAL MATCH (p)-[:SUBMITTED]->(r:Registration)
WHERE coalesce(r.legalHold, false) = false
WITH j, p, collect(DISTINCT r) AS regs

FOREACH (reg IN regs |
  SET
    reg.guestName = null,
    reg.contactEmail = null,
    reg.contactPhone = null,
    reg.notes = null,
    reg.accessibilityNeeds = null,
    reg.retentionState = 'DSAR_ANONYMIZED',
    reg.anonymizedAt = datetime(),
    reg.dsarJobId = j.jobId,
    reg.updatedAt = datetime(),
    reg.updatedBy = 'dsar-job'
)

SET
  p.fullName = null,
  p.email = null,
  p.phone = null,
  p.address = null,
  p.dob = null,
  p.tags = [],
  p.internalNotes = null,
  p.dsarState = 'ANONYMIZED',
  p.anonymizedAt = datetime(),
  p.dsarJobId = j.jobId,
  p.updatedAt = datetime(),
  p.updatedBy = 'dsar-job',
  j.status = 'COMPLETED',
  j.completedAt = datetime(),
  j.anonymizedRegistrationCount = size(regs)

CREATE (:DSAREvidence {
  evidenceId: randomUUID(),
  jobId: j.jobId,
  subjectPersonId: $subjectPersonId,
  recordedAt: datetime(),
  action: 'ANONYMIZE',
  registrationCount: size(regs),
  outcome: 'SUCCESS'
})
RETURN j.jobId AS jobId, j.status AS status, j.anonymizedRegistrationCount AS registrationCount;
```

---

## 5) Data-integrity checks for these controls

Run as scheduled controls; each query should return **0 rows** (or expected threshold).

### 5.1 Public registrations missing token binding
```cypher
MATCH (r:Registration {channel: 'PUBLIC'})
WHERE r.sourceTokenJti IS NULL
RETURN r.registrationId, r.createdAt
LIMIT 100;
```

### 5.2 Token replay/control failure (same jti used by multiple requests)
```cypher
MATCH (u:TokenUse)
WITH u.jti AS jti, collect(DISTINCT u.requestId) AS reqs
WHERE size(reqs) > 1
RETURN jti, reqs
LIMIT 100;
```

### 5.3 Canonical `Person` touched by public channel (should never happen)
```cypher
MATCH (p:Person)
WHERE coalesce(p.writeChannel, '') = 'PUBLIC'
RETURN p.personId, p.updatedAt, p.updatedBy
LIMIT 100;
```

### 5.4 Missing authZ/audit context on security-relevant writes
```cypher
MATCH (a:AuditLog)
WHERE a.requestId IS NULL
   OR a.traceId IS NULL
   OR a.actorId IS NULL
   OR a.authzDecision IS NULL
   OR a.authzPolicyVersion IS NULL
RETURN a.auditId, a.occurredAt
LIMIT 100;
```

### 5.5 Registrations without audit evidence
```cypher
MATCH (r:Registration)
WHERE r.updatedAt >= datetime() - duration('P1D')
OPTIONAL MATCH (a:AuditLog)-[:TARGETS]->(r)
WITH r, count(a) AS auditCount
WHERE auditCount = 0
RETURN r.registrationId, r.updatedAt
LIMIT 100;
```

### 5.6 Retention SLA breach detector
```cypher
MATCH (r:Registration)-[:FOR_EVENT]->(e:Event)
WHERE e.endAt < datetime() - duration('P24M')
  AND coalesce(r.legalHold, false) = false
  AND r.anonymizedAt IS NULL
RETURN r.registrationId, e.eventId, e.endAt
LIMIT 100;
```

## Implementation gate for Neo4j layer
- Public registration repository method signature forbids `eventId` input.
- Public write transaction includes token validation, replay protection, registration upsert, token consume, and audit append atomically.
- Role privileges deny all `Person` mutations from public-writer role.
- Retention and DSAR jobs run with idempotent job IDs and emit evidence nodes.
- Integrity-check queries are wired to daily monitoring; non-zero result is release-blocking.

Neo4jDBEngineer Remediation: COMPLETE
