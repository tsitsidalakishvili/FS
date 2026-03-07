// Unified CRM + Deliberation schema migration
// Safe to re-run (idempotent DDL via IF NOT EXISTS).
// Run duplicate audit queries before enforcing unique constraints in production.

// ------------------------------------------------------------------
// 1) Normalization/backfill
// ------------------------------------------------------------------

MATCH (p:Person)
WHERE p.email IS NOT NULL
SET p.emailNormalized = toLower(trim(p.email));

MATCH (st:SupporterType)
WHERE st.name IS NOT NULL
SET st.name = trim(st.name);

MATCH (t:Tag)
WHERE t.name IS NOT NULL
SET t.name = trim(t.name);

MATCH (s:Skill)
WHERE s.name IS NOT NULL
SET s.name = trim(s.name);

MATCH (ia:InvolvementArea)
WHERE ia.name IS NOT NULL
SET ia.name = trim(ia.name);

MATCH (ed:EducationLevel)
WHERE ed.name IS NOT NULL
SET ed.name = trim(ed.name);

// ------------------------------------------------------------------
// 2) Duplicate audit (inspect result sets; resolve before constraints)
// ------------------------------------------------------------------

MATCH (p:Person)
WHERE p.emailNormalized IS NOT NULL
WITH p.emailNormalized AS key, count(*) AS c, collect(p.email)[0..10] AS sample
WHERE c > 1
RETURN "Person.emailNormalized duplicate" AS issue, key, c, sample
ORDER BY c DESC;

MATCH (n:SupporterType)
WHERE n.name IS NOT NULL
WITH toLower(trim(n.name)) AS key, count(*) AS c
WHERE c > 1
RETURN "SupporterType.name duplicate" AS issue, key, c
ORDER BY c DESC;

MATCH (n:Tag)
WHERE n.name IS NOT NULL
WITH toLower(trim(n.name)) AS key, count(*) AS c
WHERE c > 1
RETURN "Tag.name duplicate" AS issue, key, c
ORDER BY c DESC;

MATCH (n:Skill)
WHERE n.name IS NOT NULL
WITH toLower(trim(n.name)) AS key, count(*) AS c
WHERE c > 1
RETURN "Skill.name duplicate" AS issue, key, c
ORDER BY c DESC;

// ------------------------------------------------------------------
// 3) Constraints (uniqueness)
// ------------------------------------------------------------------

CREATE CONSTRAINT person_person_id_unique IF NOT EXISTS
FOR (p:Person)
REQUIRE p.personId IS UNIQUE;

CREATE CONSTRAINT person_email_unique IF NOT EXISTS
FOR (p:Person)
REQUIRE p.email IS UNIQUE;

CREATE CONSTRAINT person_email_normalized_unique IF NOT EXISTS
FOR (p:Person)
REQUIRE p.emailNormalized IS UNIQUE;

CREATE CONSTRAINT supporter_type_name_unique IF NOT EXISTS
FOR (st:SupporterType)
REQUIRE st.name IS UNIQUE;

CREATE CONSTRAINT tag_name_unique IF NOT EXISTS
FOR (t:Tag)
REQUIRE t.name IS UNIQUE;

CREATE CONSTRAINT skill_name_unique IF NOT EXISTS
FOR (s:Skill)
REQUIRE s.name IS UNIQUE;

CREATE CONSTRAINT involvement_area_name_unique IF NOT EXISTS
FOR (ia:InvolvementArea)
REQUIRE ia.name IS UNIQUE;

CREATE CONSTRAINT education_level_name_unique IF NOT EXISTS
FOR (ed:EducationLevel)
REQUIRE ed.name IS UNIQUE;

CREATE CONSTRAINT task_task_id_unique IF NOT EXISTS
FOR (t:Task)
REQUIRE t.taskId IS UNIQUE;

CREATE CONSTRAINT event_event_id_unique IF NOT EXISTS
FOR (e:Event)
REQUIRE e.eventId IS UNIQUE;

CREATE CONSTRAINT event_event_key_unique IF NOT EXISTS
FOR (e:Event)
REQUIRE e.eventKey IS UNIQUE;

CREATE CONSTRAINT segment_segment_id_unique IF NOT EXISTS
FOR (s:Segment)
REQUIRE s.segmentId IS UNIQUE;

CREATE CONSTRAINT segment_name_unique IF NOT EXISTS
FOR (s:Segment)
REQUIRE s.name IS UNIQUE;

CREATE CONSTRAINT conversation_id_unique IF NOT EXISTS
FOR (c:Conversation)
REQUIRE c.id IS UNIQUE;

CREATE CONSTRAINT comment_id_unique IF NOT EXISTS
FOR (c:Comment)
REQUIRE c.id IS UNIQUE;

CREATE CONSTRAINT participant_id_unique IF NOT EXISTS
FOR (p:Participant)
REQUIRE p.id IS UNIQUE;

CREATE CONSTRAINT cluster_id_unique IF NOT EXISTS
FOR (c:Cluster)
REQUIRE c.id IS UNIQUE;

CREATE CONSTRAINT analysis_run_id_unique IF NOT EXISTS
FOR (a:AnalysisRun)
REQUIRE a.id IS UNIQUE;

// ------------------------------------------------------------------
// 4) Secondary indexes (read performance)
// ------------------------------------------------------------------

CREATE INDEX person_name_idx IF NOT EXISTS
FOR (p:Person)
ON (p.firstName, p.lastName);

CREATE INDEX address_full_address_idx IF NOT EXISTS
FOR (a:Address)
ON (a.fullAddress);

CREATE INDEX task_status_due_date_idx IF NOT EXISTS
FOR (t:Task)
ON (t.status, t.dueDate);

CREATE INDEX event_start_status_idx IF NOT EXISTS
FOR (e:Event)
ON (e.startDate, e.status);

CREATE INDEX conversation_created_at_idx IF NOT EXISTS
FOR (c:Conversation)
ON (c.createdAt);

CREATE INDEX comment_status_created_at_idx IF NOT EXISTS
FOR (c:Comment)
ON (c.status, c.createdAt);

CREATE INDEX participant_created_at_idx IF NOT EXISTS
FOR (p:Participant)
ON (p.createdAt);

CREATE INDEX cluster_run_id_idx IF NOT EXISTS
FOR (c:Cluster)
ON (c.runId);

CREATE FULLTEXT INDEX person_search_fulltext IF NOT EXISTS
FOR (p:Person)
ON EACH [p.email, p.firstName, p.lastName];
