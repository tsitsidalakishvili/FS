// Post-migration validation checks.
// Expected: every row returns violation_count = 0 (except warning rows where noted).

MATCH (p:Person)
WHERE p.email IS NULL OR trim(p.email) = ""
RETURN "person_missing_email" AS check_name, "error" AS severity, count(*) AS violation_count;

MATCH (p:Person)
WHERE p.personId IS NULL OR trim(toString(p.personId)) = ""
RETURN "person_missing_person_id" AS check_name, "error" AS severity, count(*) AS violation_count;

MATCH (p:Person)
WHERE p.email IS NOT NULL AND trim(p.email) <> ""
WITH toLower(trim(p.email)) AS key, count(*) AS c
WHERE c > 1
RETURN "duplicate_person_email_case_insensitive" AS check_name, "error" AS severity, sum(c - 1) AS violation_count;

MATCH (e:Event)
WHERE e.eventId IS NULL OR trim(toString(e.eventId)) = ""
RETURN "event_missing_event_id" AS check_name, "error" AS severity, count(*) AS violation_count;

MATCH (e:Event)
WHERE e.eventKey IS NULL OR trim(toString(e.eventKey)) = ""
RETURN "event_missing_event_key" AS check_name, "error" AS severity, count(*) AS violation_count;

MATCH (t:Task)
WHERE t.taskId IS NULL OR trim(toString(t.taskId)) = ""
RETURN "task_missing_task_id" AS check_name, "error" AS severity, count(*) AS violation_count;

MATCH (p:Person)
WHERE NOT (p)-[:CLASSIFIED_AS]->(:SupporterType)
RETURN "person_without_supporter_type" AS check_name, "error" AS severity, count(*) AS violation_count;

MATCH (p:Person)-[:HAS_TASK]->(t:Task)
WITH t, count(*) AS owner_count
WHERE owner_count > 1
RETURN "task_with_multiple_owners" AS check_name, "warning" AS severity, count(*) AS violation_count;

MATCH (t:Task)
WHERE NOT ( :Person )-[:HAS_TASK]->(t)
RETURN "orphan_task_without_owner" AS check_name, "error" AS severity, count(*) AS violation_count;

MATCH ()-[r:REGISTERED_FOR]->()
WHERE r.status IS NULL OR trim(toString(r.status)) = ""
RETURN "registration_missing_status" AS check_name, "error" AS severity, count(*) AS violation_count;

MATCH ()-[r:REGISTERED_FOR]->()
WHERE r.status IS NOT NULL
  AND NOT trim(toString(r.status)) IN ["Registered", "Attended", "Cancelled", "No Show"]
RETURN "registration_invalid_status" AS check_name, "warning" AS severity, count(*) AS violation_count;

MATCH (a:Address)
WHERE (a.latitude IS NOT NULL AND a.longitude IS NOT NULL) AND a.location IS NULL
RETURN "address_missing_point_location" AS check_name, "warning" AS severity, count(*) AS violation_count;

MATCH (m:MigrationBatch {migrationId: $migrationId})
RETURN "migration_batch_status" AS check_name,
       CASE WHEN m.status = "completed" THEN "info" ELSE "error" END AS severity,
       CASE WHEN m.status = "completed" THEN 0 ELSE 1 END AS violation_count;
