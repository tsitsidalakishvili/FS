# Neo4j Production Migration Plan (CRM)

This document defines the production migration baseline for making Neo4j the
primary DBMS for the CRM currently served through Streamlit pages.

Related files:
- `neo4j/cypher/000_preflight_checks.cypher`
- `neo4j/cypher/001_constraints_indexes.cypher`
- `neo4j/cypher/002_migrate_streamlit_legacy.cypher`
- `neo4j/cypher/003_seed_reference_data.cypher`
- `neo4j/cypher/004_query_catalog.cypher`
- `neo4j/CYPHER_QUERY_CATALOG.md`
- `neo4j/cypher/005_post_migration_validation.cypher`
- `neo4j/cypher/006_rollback_migration_batch.cypher`
- `scripts/neo4j_migration.py`
- `scripts/neo4j_seed_from_csv.py`

## 1) Graph domain model

### 1.1 Nodes

| Label | Key property | Purpose | Core properties |
|---|---|---|---|
| `Person` | `email` (unique) | CRM profile root entity | `personId`, `firstName`, `lastName`, `phone`, `gender`, `age`, `timeAvailability`, `about`, `agreesWithManifesto`, `interestedInMembership`, `facebookGroupMember`, `effortHours`, `eventsAttendedCount`, `referralCount`, `donationTotal`, `createdAt`, `updatedAt` |
| `SupporterType` | `name` (unique) | Person classification (`Supporter`, `Member`) | `createdAt`, `updatedAt` |
| `Address` | `fullAddress` (unique) | Normalized location node | `latitude`, `longitude`, `location` (point), `createdAt`, `updatedAt` |
| `Skill` | `name` (unique) | Capability taxonomy | `createdAt` |
| `Tag` | `name` (unique) | Segmentation taxonomy | `createdAt` |
| `InvolvementArea` | `name` (unique) | Interest taxonomy | `createdAt` |
| `EducationLevel` | `name` (unique) | Education taxonomy | `createdAt` |
| `Segment` | `segmentId` (unique), `name` (unique) | Saved filter segment | `description`, `filterJson`, `createdAt`, `updatedAt` |
| `Task` | `taskId` (unique) | Follow-up task entity | `title`, `description`, `status`, `dueDate`, `createdAt`, `updatedAt` |
| `Event` | `eventId` (unique), `eventKey` (unique) | Event/campaign activity | `name`, `startDate`, `endDate`, `location`, `status`, `capacity`, `notes`, `createdAt`, `updatedAt` |
| `Competitor` | `competitorId` (unique), `(nameKey, competitorType)` (composite) | Competitor tracking | `name`, `notes`, `createdAt`, `updatedAt` |
| `WhatsAppGroup` | `groupId` (unique), `name` (unique) | Outreach channel | `inviteLink`, `notes`, `createdAt`, `updatedAt` |
| `MigrationBatch` | `migrationId` (unique) | Migration audit/control | `startedAt`, `completedAt`, `status`, `notes` |

### 1.2 Relationships (explicit direction, cardinality, properties)

| Relationship | Direction | Cardinality | Properties |
|---|---|---|---|
| `(:Person)-[:CLASSIFIED_AS]->(:SupporterType)` | Person -> SupporterType | `N:1` target set (usually 1 active) | `createdAt`, `updatedAt`, `migrationBatchId` |
| `(:Person)-[:LIVES_AT]->(:Address)` | Person -> Address | `N:1` preferred; historical `N:N` tolerated | `since`, `isPrimary`, `migrationBatchId` |
| `(:Person)-[:CAN_CONTRIBUTE_WITH]->(:Skill)` | Person -> Skill | `N:N` | `proficiency`, `migrationBatchId` |
| `(:Person)-[:HAS_TAG]->(:Tag)` | Person -> Tag | `N:N` | `source`, `migrationBatchId` |
| `(:Person)-[:INTERESTED_IN]->(:InvolvementArea)` | Person -> InvolvementArea | `N:N` | `interestLevel`, `migrationBatchId` |
| `(:Person)-[:HAS_EDUCATION]->(:EducationLevel)` | Person -> EducationLevel | `N:N` | `isHighest`, `migrationBatchId` |
| `(:Person)-[:REFERRED_BY]->(:Person)` | Person -> Person (referrer) | `N:1` preferred | `referralDate`, `source`, `migrationBatchId` |
| `(:Person)-[:HAS_TASK]->(:Task)` | Person -> Task | `1:N` | `assignedAt`, `migrationBatchId` |
| `(:Person)-[:REGISTERED_FOR]->(:Event)` | Person -> Event | `N:N` | `status`, `registeredAt`, `updatedAt`, `notes`, `migrationBatchId` |

## 2) Constraints and indexes plan

Apply schema from `001_constraints_indexes.cypher` only after preflight duplicate
checks pass.

### 2.1 Mandatory uniqueness constraints

- `Person.email`
- `Person.personId`
- `SupporterType.name`
- `Address.fullAddress`
- `Skill.name`
- `Tag.name`
- `InvolvementArea.name`
- `EducationLevel.name`
- `Segment.segmentId`
- `Segment.name`
- `Task.taskId`
- `Event.eventId`
- `Event.eventKey`
- `Competitor.competitorId`
- Composite uniqueness for `Competitor(nameKey, competitorType)`
- `WhatsAppGroup.groupId`
- `WhatsAppGroup.name`
- `MigrationBatch.migrationId`

### 2.2 Performance indexes

- Fulltext index for person lookup: `email`, `firstName`, `lastName`, `phone`.
- Range indexes for:
  - `Task(status, dueDate, updatedAt)`
  - `Event(status, startDate, endDate)`
  - `Person(timeAvailability, updatedAt)`
  - `Person(createdAt)`
- Relationship index:
  - `REGISTERED_FOR(status, updatedAt)`
- Point index:
  - `Address(location)`

## 3) Critical query catalog + latency SLO targets

Canonical query catalog is in `neo4j/CYPHER_QUERY_CATALOG.md`.

Target latencies assume:
- Neo4j 5.x
- warm page cache
- data size up to ~2M `Person` nodes, ~20M relationships
- p95 measured from app/API boundary (excluding client render)

| Path | p50 target | p95 target |
|---|---:|---:|
| Person upsert | <= 25 ms | <= 120 ms |
| Person search (name/email contains/fulltext) | <= 40 ms | <= 180 ms |
| Profile load | <= 35 ms | <= 150 ms |
| Segment run (up to 2k rows) | <= 120 ms | <= 500 ms |
| Task create | <= 20 ms | <= 100 ms |
| Task list queue | <= 60 ms | <= 250 ms |
| Event create | <= 20 ms | <= 100 ms |
| Registration upsert | <= 30 ms | <= 140 ms |
| Event registration list | <= 80 ms | <= 300 ms |
| Dashboard aggregates | <= 200 ms | <= 800 ms |

## 4) Transaction boundaries and consistency assumptions

### 4.1 Boundaries

- **Single-entity writes** (`Person`, `Task`, `Event`) use one write transaction per
  request.
- **Registration flow** (`Person` + `REGISTERED_FOR`) is atomic in one transaction.
- **Bulk seed/import** uses chunked transactions (`500-2000` rows per transaction).
- **Schema migration** executes statement-by-statement; each statement is atomic.
- **Validation** runs in read transactions and is side-effect free.

### 4.2 Consistency assumptions

- Neo4j provides ACID semantics per transaction; reads are eventually consistent
  across concurrent sessions at query level but always transactionally consistent.
- `MERGE` on constrained keys is used to guarantee idempotent upserts.
- Relationship duplication is prevented via `MERGE` patterns.
- No cross-database distributed transaction is assumed.
- During migration, writes should be routed to one writer service instance to
  avoid race conditions around first-time normalization.

## 5) Rollback-safe migration strategy

1. **Pre-backup**: take full backup (or Aura export) before any migration write.
2. **Preflight**: run `000_preflight_checks.cypher`; block rollout on any duplicate
   key findings.
3. **Schema**: apply `001_constraints_indexes.cypher`.
4. **Migration batch start**: create `(:MigrationBatch {migrationId})`.
5. **Backfill/normalize**: run `002_migrate_streamlit_legacy.cypher` with
   `migrationId` so all new edges/nodes are tagged.
6. **Seed defaults**: run `003_seed_reference_data.cypher`.
7. **Validate**: run `005_post_migration_validation.cypher`; compare expected
   counts and invariant checks.
8. **Cutover**: route all read/write traffic to production Neo4j path.
9. **Observe**: monitor latency/errors for a defined bake period.

Rollback options:
- **Fast logical rollback**: run `006_rollback_migration_batch.cypher` for the
  specific `migrationId` to remove tagged entities/relationships created by the
  batch.
- **Hard rollback**: restore full backup/snapshot taken before step 3.

## 6) Data validation checks (blocking)

Mandatory pass criteria:
- `Person.email` duplicates = 0
- `Event.eventId/eventKey` duplicates = 0
- `Task.taskId` duplicates = 0
- No `REGISTERED_FOR` relationship missing `status`
- No orphan `Task` without inbound `HAS_TASK`
- No orphan `Event` registrations with missing `Person` or `Event`
- At least 99.9% of `Person` nodes have `personId`

## 7) Backup and restore plan

### 7.1 Self-hosted Neo4j

**Online backup (Enterprise):**
- Run before migration and on schedule (daily full + hourly differential):
  - `neo4j-admin database backup --from=<host:6362> --database=neo4j --to-path=/backups`

**Consistency check (post-backup):**
- `neo4j-admin database check neo4j --from-path=/backups/<artifact>`

**Restore to new DB (preferred):**
- Stop target DB; restore snapshot into staging DB name:
  - `neo4j-admin database restore --from-path=/backups/<artifact> --database=neo4j_restore --overwrite-destination=true`
- Validate, then swap traffic.

### 7.2 Neo4j Aura

- Use scheduled Aura backups and on-demand export prior to migration window.
- Keep at least one known-good snapshot for the full migration bake period.
- Restore by creating a new Aura instance from snapshot; run validation checks;
  switch application connection settings.

### 7.3 Backup policy targets

- **RPO**: <= 1 hour
- **RTO**: <= 30 minutes for logical rollback, <= 2 hours for full restore
- Encrypt backups at rest; restrict restore credentials to ops-only role.

