# Stage 4 — Neo4jDBEngineer

## Approved model (Increment 1)
- Nodes: `Person`, `Task`, `Event`, `Registration`, `DeepLink`
- Relationships:
  - `(Person)-[:HAS_TASK]->(Task)`
  - `(Person)-[:SUBMITTED]->(Registration)`
  - `(Registration)-[:FOR_EVENT]->(Event)`
  - `(Registration)-[:CREATED_VIA]->(DeepLink)` (optional)
  - `(DeepLink)-[:RESOLVES_TO]->(Event)`

## Required constraints/indexes
- Uniques: `Person.email`, `Person.personId`, `Task.taskId`, `Event.eventId`, `Event.eventKey`,
  `Registration.registrationId`, `Registration.registrationKey`, `DeepLink.linkId`, `DeepLink.tokenHash`
- Query indexes: person status, task owner/status/dueDate, event publish/startDate, registration status, deepLink active/expiry

## Cypher catalog coverage
- People upsert/list/archive
- Task create/list/update status
- Event create/publish
- Deep-link create/resolve
- Registration create/list (idempotent key pattern)

## Data boundary contract
- Backend-only writes to Neo4j
- DTO validation/normalization at API layer
- Audit fields managed server-side

## Gate result
- Neo4jDBEngineer Gate: PASS
- Artifact delivered: YES
