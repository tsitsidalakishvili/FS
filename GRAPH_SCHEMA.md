# Unified Neo4j Graph Model (CRM + Deliberation)

This document is the authoritative graph model and query guidance for this repository.

Goals:
- prevent duplicate entities (especially people and taxonomy nodes),
- keep common reads/writes index-backed,
- isolate and minimize personally identifiable information (PII).

---

## 1) Canonical node model

### CRM domain

| Label | Key property/properties | Purpose | PII class |
|---|---|---|---|
| `Person` | `email` (current key), `personId` (internal UUID), `emailNormalized` (migration key) | Core supporter/member profile | **High** |
| `SupporterType` | `name` | Supporter/member classification | Low |
| `Tag` | `name` | Segmenting tag taxonomy | Low |
| `Skill` | `name` | Skill taxonomy | Low |
| `InvolvementArea` | `name` | Interest taxonomy | Low |
| `EducationLevel` | `name` | Education taxonomy | Low |
| `Address` | `fullAddress` | Shared address/location node | **High** |
| `Task` | `taskId` | Work item assigned to person | Medium |
| `Event` | `eventId`, `eventKey` | Event metadata | Medium |
| `Segment` | `segmentId`, `name` | Saved segment definitions (`filterJson`) | Low |
| `Activity` *(legacy)* | `activityId` | Participation activity records | Medium |
| `Supporter` *(legacy)* | implementation-specific | Legacy compatibility for analytics queries | Medium |

### Deliberation domain

| Label | Key property/properties | Purpose | PII class |
|---|---|---|---|
| `Conversation` | `id` | Deliberation thread | Low |
| `Comment` | `id` | Submitted/seed comment | Medium |
| `Participant` | `id` (salted hash only) | Voter identity abstraction | **Pseudonymous** |
| `AnalysisRun` | `id` | Analytics execution metadata | Low |
| `Cluster` | `id` | Derived participant cluster | Low |

---

## 2) Canonical relationship model

### CRM relationships
- `(p:Person)-[:CLASSIFIED_AS]->(st:SupporterType)`
- `(p:Person)-[:LIVES_AT]->(a:Address)`
- `(p:Person)-[:HAS_TAG]->(t:Tag)`
- `(p:Person)-[:CAN_CONTRIBUTE_WITH]->(s:Skill)`
- `(p:Person)-[:INTERESTED_IN]->(ia:InvolvementArea)`
- `(p:Person)-[:HAS_EDUCATION]->(ed:EducationLevel)`
- `(p:Person)-[:HAS_TASK]->(t:Task)`
- `(p:Person)-[r:REGISTERED_FOR]->(e:Event)` (`r.status`, etc.)
- `(referrer:Person)-[:REFERRED_BY]->(target:Person)` *(legacy usage is incoming to profiled person)*
- `(p:Person)-[:HAS_ACTIVITY]->(a:Activity)` *(legacy)*
- `(p:Person)-[:IS_SUPPORTER]->(s:Supporter)` and `(s)-[:RECRUITED]->(s2:Supporter)` *(legacy)*

### Deliberation relationships
- `(c:Conversation)-[:HAS_COMMENT]->(cm:Comment)`
- `(p:Participant)-[:PARTICIPATED_IN]->(c:Conversation)`
- `(p:Participant)-[v:VOTED]->(cm:Comment)` (`v.choice`, `v.votedAt`)
- `(ar:AnalysisRun)-[:FOR_CONVERSATION]->(c:Conversation)`
- `(cl:Cluster)-[:OF_CONVERSATION]->(c:Conversation)`
- `(p:Participant)-[:IN_CLUSTER {runId}]->(cl:Cluster)`
- `(ar)-[res:HAS_RESULT]->(cm:Comment)` (consensus/polarity metrics)

---

## 3) PII modeling and handling rules

1. `Person.email`, `Person.phone`, and `Address.fullAddress` are **sensitive**; keep reads scoped and avoid broad exports.
2. Introduce and use `emailNormalized = toLower(trim(email))` for dedupe-safe identity.
3. Never store raw deliberation participant IDs in graph; only salted hashes (`Participant.id`).
4. `ANON_SALT` must be environment-managed and rotated through a planned process (rotation implies remapping strategy).
5. Analytics/reporting should project only required fields (avoid `RETURN p` in user-facing paths).

---

## 4) Constraints and indexes (target state)

Executable migration statements live in:
- `neo4j/migrations/001_core_schema.cypher`

High-priority constraints (uniqueness):
- `Person.personId`, `Person.email`, `Person.emailNormalized`
- `Task.taskId`, `Event.eventId`, `Event.eventKey`, `Segment.segmentId`, `Segment.name`
- `SupporterType.name`, `Tag.name`, `Skill.name`, `EducationLevel.name`, `InvolvementArea.name`
- `Conversation.id`, `Comment.id`, `Participant.id`, `Cluster.id`, `AnalysisRun.id`

High-priority indexes:
- `Person(firstName, lastName)` and fulltext `Person(email, firstName, lastName)`
- `Task(status, dueDate)`, `Event(startDate, status)`, `Address(fullAddress)`
- `Comment(status, createdAt)`, `Conversation(createdAt)`, `Participant(createdAt)`, `Cluster(runId)`

---

## 5) Migration plan

### Phase 0 - Preflight
- Snapshot database and capture baseline counts by label/relationship.
- Run duplicate audits for `Person.emailNormalized` and taxonomy `name` properties.

### Phase 1 - Normalize
- Backfill `emailNormalized` on `Person`.
- Trim canonical name fields for taxonomy labels (`Tag`, `Skill`, `SupporterType`, etc.).

### Phase 2 - Resolve duplicates
- Merge case-variant duplicate entities in controlled batches.
- Rewire relationships to canonical nodes; then remove obsolete duplicates.

### Phase 3 - Enforce schema
- Apply uniqueness constraints and indexes (`001_core_schema.cypher`).
- Validate all application write paths remain idempotent under constraints.

### Phase 4 - Query hardening
- Update write paths to always pass normalized keys (especially email).
- Convert expensive broad scans to indexed starts plus `EXISTS { ... }` subqueries where appropriate.

### Rollback strategy
- If constraint creation fails, keep existing graph unchanged, inspect duplicate audit output, repair data, and rerun.
- Perform schema rollout in non-production first and compare cardinalities and key endpoint latencies.

---

## 6) Key Cypher patterns

### Pattern A - Idempotent person upsert (duplication-safe)
```cypher
MERGE (p:Person {emailNormalized: toLower(trim($email))})
ON CREATE SET
  p.personId = coalesce($personId, randomUUID()),
  p.createdAt = datetime()
SET
  p.email = $email,
  p.firstName = $firstName,
  p.lastName = $lastName,
  p.updatedAt = datetime();
```

### Pattern B - Taxonomy normalization without duplicate edges
```cypher
MATCH (p:Person {emailNormalized: toLower(trim($email))})
UNWIND $skills AS rawSkill
WITH p, trim(rawSkill) AS skill
WHERE skill <> ""
MERGE (s:Skill {name: skill})
MERGE (p)-[:CAN_CONTRIBUTE_WITH]->(s);
```

### Pattern C - Vote upsert (single vote per participant/comment)
```cypher
MATCH (c:Conversation {id: $conversationId})-[:HAS_COMMENT]->(cm:Comment {id: $commentId})
WHERE cm.status = "approved"
MERGE (p:Participant {id: $participantHash})
  ON CREATE SET p.createdAt = datetime()
MERGE (p)-[:PARTICIPATED_IN]->(c)
MERGE (p)-[v:VOTED]->(cm)
SET v.choice = $choice, v.votedAt = datetime();
```

### Pattern D - Segment query with controlled fan-out
```cypher
MATCH (p:Person)
WHERE ($group IS NULL OR EXISTS {
  MATCH (p)-[:CLASSIFIED_AS]->(st:SupporterType)
  WHERE ($group = "Member" AND toLower(st.name) CONTAINS "member")
     OR ($group = "Supporter" AND NOT toLower(st.name) CONTAINS "member")
})
AND ($minEffort IS NULL OR coalesce(p.effortHours, 0.0) >= $minEffort)
RETURN p.email, p.firstName, p.lastName
LIMIT $limit;
```

### Pattern E - Conversation metrics projection (no over-fetch)
```cypher
MATCH (c:Conversation {id: $id})
OPTIONAL MATCH (c)-[:HAS_COMMENT]->(cm:Comment)
WITH c, count(cm) AS comments
OPTIONAL MATCH (:Participant)-[:PARTICIPATED_IN]->(c)
RETURN c.id AS id, c.topic AS topic, comments, count(*) AS participants;
```

---

## 7) Performance and quality checklist

- Always `MERGE` on constrained key properties.
- Avoid `CONTAINS` over unindexed large properties for high-volume paths unless using fulltext.
- Keep multi-hop analytics in background/report endpoints, not transactional API paths.
- Prefer bounded `LIMIT` and explicit projection of fields.
- Use periodic duplicate audits as operational checks after bulk imports.
