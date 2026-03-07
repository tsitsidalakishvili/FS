// Run before applying uniqueness constraints.
// Any non-zero duplicate_count should block migration.

// Duplicate Person.email
MATCH (p:Person)
WHERE p.email IS NOT NULL AND trim(p.email) <> ""
WITH toLower(trim(p.email)) AS key, count(*) AS c
WHERE c > 1
RETURN "duplicate_person_email" AS check_name, sum(c - 1) AS duplicate_count;

// Duplicate Event.eventId
MATCH (e:Event)
WHERE e.eventId IS NOT NULL AND trim(toString(e.eventId)) <> ""
WITH trim(toString(e.eventId)) AS key, count(*) AS c
WHERE c > 1
RETURN "duplicate_event_id" AS check_name, sum(c - 1) AS duplicate_count;

// Duplicate Event.eventKey
MATCH (e:Event)
WHERE e.eventKey IS NOT NULL AND trim(toString(e.eventKey)) <> ""
WITH trim(toString(e.eventKey)) AS key, count(*) AS c
WHERE c > 1
RETURN "duplicate_event_key" AS check_name, sum(c - 1) AS duplicate_count;

// Duplicate Task.taskId
MATCH (t:Task)
WHERE t.taskId IS NOT NULL AND trim(toString(t.taskId)) <> ""
WITH trim(toString(t.taskId)) AS key, count(*) AS c
WHERE c > 1
RETURN "duplicate_task_id" AS check_name, sum(c - 1) AS duplicate_count;

// Duplicate Segment.segmentId
MATCH (s:Segment)
WHERE s.segmentId IS NOT NULL AND trim(toString(s.segmentId)) <> ""
WITH trim(toString(s.segmentId)) AS key, count(*) AS c
WHERE c > 1
RETURN "duplicate_segment_id" AS check_name, sum(c - 1) AS duplicate_count;

// Duplicate Segment.name
MATCH (s:Segment)
WHERE s.name IS NOT NULL AND trim(s.name) <> ""
WITH toLower(trim(s.name)) AS key, count(*) AS c
WHERE c > 1
RETURN "duplicate_segment_name" AS check_name, sum(c - 1) AS duplicate_count;

// Duplicate WhatsAppGroup.name
MATCH (g:WhatsAppGroup)
WHERE g.name IS NOT NULL AND trim(g.name) <> ""
WITH toLower(trim(g.name)) AS key, count(*) AS c
WHERE c > 1
RETURN "duplicate_whatsapp_group_name" AS check_name, sum(c - 1) AS duplicate_count;

// Potentially invalid competitor composite key
MATCH (c:Competitor)
WHERE c.nameKey IS NOT NULL AND c.competitorType IS NOT NULL
WITH toLower(trim(c.nameKey)) AS key1, trim(c.competitorType) AS key2, count(*) AS c
WHERE c > 1
RETURN "duplicate_competitor_namekey_type" AS check_name, sum(c - 1) AS duplicate_count;

// Existing records missing business key fields (must be remediated before constraints)
MATCH (p:Person)
WHERE p.email IS NULL OR trim(p.email) = ""
RETURN "person_missing_email" AS check_name, count(*) AS duplicate_count;

MATCH (e:Event)
WHERE e.eventKey IS NULL OR trim(toString(e.eventKey)) = ""
RETURN "event_missing_event_key" AS check_name, count(*) AS duplicate_count;
