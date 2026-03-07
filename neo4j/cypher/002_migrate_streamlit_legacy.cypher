// Required parameter:
//   $migrationId (string, e.g. "2026-03-07-prod-cutover-01")

MERGE (m:MigrationBatch {migrationId: $migrationId})
ON CREATE SET m.startedAt = datetime(), m.status = "running"
SET m.notes = "Legacy Streamlit-to-Neo4j normalization/backfill";

// Ensure canonical IDs exist on core entities.
MATCH (p:Person)
WHERE p.personId IS NULL
SET p.personId = randomUUID(),
    p.updatedAt = datetime();

MATCH (t:Task)
WHERE t.taskId IS NULL
SET t.taskId = randomUUID(),
    t.updatedAt = datetime();

MATCH (e:Event)
WHERE e.eventId IS NULL
SET e.eventId = randomUUID(),
    e.updatedAt = datetime();

MATCH (e:Event)
WHERE e.eventKey IS NULL OR trim(toString(e.eventKey)) = ""
SET e.eventKey = randomUUID(),
    e.updatedAt = datetime();

MATCH (s:Segment)
WHERE s.segmentId IS NULL
SET s.segmentId = randomUUID(),
    s.updatedAt = datetime();

MATCH (g:WhatsAppGroup)
WHERE g.groupId IS NULL
SET g.groupId = randomUUID(),
    g.updatedAt = datetime();

MATCH (c:Competitor)
WHERE c.competitorId IS NULL
SET c.competitorId = randomUUID(),
    c.updatedAt = datetime();

MATCH (c:Competitor)
WHERE c.name IS NOT NULL AND (c.nameKey IS NULL OR trim(c.nameKey) = "")
SET c.nameKey = toLower(trim(c.name)),
    c.updatedAt = datetime();

// Normalize supporter classification from legacy Supporter node if present.
MATCH (p:Person)-[:IS_SUPPORTER]->(s:Supporter)
WITH p,
     CASE
       WHEN toLower(coalesce(s.supporterType, s.group, s.type, "")) CONTAINS "member"
       THEN "Member"
       ELSE "Supporter"
     END AS normalized
MERGE (st:SupporterType {name: normalized})
ON CREATE SET st.createdAt = datetime()
SET st.updatedAt = datetime()
MERGE (p)-[r:CLASSIFIED_AS]->(st)
ON CREATE SET r.createdAt = datetime(), r.migrationBatchId = $migrationId
SET r.updatedAt = datetime();

// Ensure all persons have at least one classification.
MATCH (p:Person)
WHERE NOT (p)-[:CLASSIFIED_AS]->(:SupporterType)
MERGE (st:SupporterType {name: "Supporter"})
ON CREATE SET st.createdAt = datetime()
SET st.updatedAt = datetime()
MERGE (p)-[r:CLASSIFIED_AS]->(st)
ON CREATE SET r.createdAt = datetime(), r.migrationBatchId = $migrationId
SET r.updatedAt = datetime();

// Backfill Address nodes from legacy Person.address + Person.lat/lon.
MATCH (p:Person)
WHERE p.address IS NOT NULL AND trim(toString(p.address)) <> ""
WITH p, trim(toString(p.address)) AS fullAddress
MERGE (a:Address {fullAddress: fullAddress})
ON CREATE SET a.createdAt = datetime(), a.migrationBatchId = $migrationId
SET a.latitude = coalesce(a.latitude, p.lat),
    a.longitude = coalesce(a.longitude, p.lon),
    a.updatedAt = datetime()
MERGE (p)-[r:LIVES_AT]->(a)
ON CREATE SET r.createdAt = datetime(), r.migrationBatchId = $migrationId
SET r.updatedAt = datetime();

MATCH (a:Address)
WITH a, toFloat(a.latitude) AS lat, toFloat(a.longitude) AS lon
WHERE lat IS NOT NULL AND lon IS NOT NULL
SET a.location = point({latitude: lat, longitude: lon}),
    a.updatedAt = datetime();

// Backfill Skill nodes/relationships from Person.skills property (list or CSV string).
MATCH (p:Person)
WITH p,
     CASE
       WHEN p.skills IS NULL THEN []
       WHEN p.skills IS LIST THEN [x IN p.skills | trim(toString(x))]
       ELSE [x IN split(toString(p.skills), ",") | trim(x)]
     END AS rawSkills
WITH p, [x IN rawSkills WHERE x <> ""] AS skills
FOREACH (skillName IN skills |
  MERGE (sk:Skill {name: skillName})
  ON CREATE SET sk.createdAt = datetime()
  MERGE (p)-[r:CAN_CONTRIBUTE_WITH]->(sk)
  ON CREATE SET r.createdAt = datetime(), r.migrationBatchId = $migrationId
  SET r.updatedAt = datetime()
);

// Backfill Tag nodes/relationships from Person.tags property (list or CSV string).
MATCH (p:Person)
WITH p,
     CASE
       WHEN p.tags IS NULL THEN []
       WHEN p.tags IS LIST THEN [x IN p.tags | trim(toString(x))]
       ELSE [x IN split(toString(p.tags), ",") | trim(x)]
     END AS rawTags
WITH p, [x IN rawTags WHERE x <> ""] AS tags
FOREACH (tagName IN tags |
  MERGE (t:Tag {name: tagName})
  ON CREATE SET t.createdAt = datetime()
  MERGE (p)-[r:HAS_TAG]->(t)
  ON CREATE SET r.createdAt = datetime(), r.migrationBatchId = $migrationId
  SET r.updatedAt = datetime()
);

// Backfill InvolvementArea nodes/relationships from Person.involvementAreas property.
MATCH (p:Person)
WITH p,
     CASE
       WHEN p.involvementAreas IS NULL THEN []
       WHEN p.involvementAreas IS LIST THEN [x IN p.involvementAreas | trim(toString(x))]
       ELSE [x IN split(toString(p.involvementAreas), ",") | trim(x)]
     END AS rawAreas
WITH p, [x IN rawAreas WHERE x <> ""] AS areas
FOREACH (areaName IN areas |
  MERGE (ia:InvolvementArea {name: areaName})
  ON CREATE SET ia.createdAt = datetime()
  MERGE (p)-[r:INTERESTED_IN]->(ia)
  ON CREATE SET r.createdAt = datetime(), r.migrationBatchId = $migrationId
  SET r.updatedAt = datetime()
);

// Backfill EducationLevel nodes/relationships from Person.education property.
MATCH (p:Person)
WHERE p.education IS NOT NULL AND trim(toString(p.education)) <> ""
WITH p, trim(toString(p.education)) AS educationName
MERGE (ed:EducationLevel {name: educationName})
ON CREATE SET ed.createdAt = datetime()
MERGE (p)-[r:HAS_EDUCATION]->(ed)
ON CREATE SET r.createdAt = datetime(), r.migrationBatchId = $migrationId
SET r.updatedAt = datetime();

// Backfill referrals from legacy Person.referrerEmail.
MATCH (p:Person)
WHERE p.referrerEmail IS NOT NULL AND trim(toString(p.referrerEmail)) <> ""
WITH p, toLower(trim(toString(p.referrerEmail))) AS refEmail
MERGE (ref:Person {email: refEmail})
ON CREATE SET ref.personId = randomUUID(), ref.createdAt = datetime(), ref.migrationBatchId = $migrationId
MERGE (p)-[r:REFERRED_BY]->(ref)
ON CREATE SET r.createdAt = datetime(), r.migrationBatchId = $migrationId
SET r.updatedAt = datetime();

// Ensure registration relationship status is always present.
MATCH ()-[r:REGISTERED_FOR]->()
WHERE r.status IS NULL OR trim(toString(r.status)) = ""
SET r.status = "Registered",
    r.updatedAt = datetime();

MATCH (m:MigrationBatch {migrationId: $migrationId})
SET m.completedAt = datetime(),
    m.status = "completed";
