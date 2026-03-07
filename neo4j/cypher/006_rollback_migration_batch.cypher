// Rollback for additive objects tagged by migrationBatchId.
// Required parameter:
//   $migrationId
//
// Note: This removes only nodes/relationships created by the tagged migration.
// Property-level changes on pre-existing nodes are not reverted here; use full
// backup restore for full rollback.

MATCH ()-[r]->()
WHERE r.migrationBatchId = $migrationId
DELETE r;

MATCH (n)
WHERE n.migrationBatchId = $migrationId
  AND NOT n:MigrationBatch
DETACH DELETE n;

MERGE (m:MigrationBatch {migrationId: $migrationId})
ON CREATE SET m.startedAt = datetime()
SET m.status = "rolled_back",
    m.completedAt = datetime(),
    m.notes = coalesce(m.notes, "") + " | additive rollback applied";
