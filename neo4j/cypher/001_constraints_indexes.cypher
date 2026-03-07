// Mandatory uniqueness constraints
CREATE CONSTRAINT person_email_unique IF NOT EXISTS
FOR (p:Person)
REQUIRE p.email IS UNIQUE;

CREATE CONSTRAINT person_personid_unique IF NOT EXISTS
FOR (p:Person)
REQUIRE p.personId IS UNIQUE;

CREATE CONSTRAINT supporter_type_name_unique IF NOT EXISTS
FOR (st:SupporterType)
REQUIRE st.name IS UNIQUE;

CREATE CONSTRAINT address_full_address_unique IF NOT EXISTS
FOR (a:Address)
REQUIRE a.fullAddress IS UNIQUE;

CREATE CONSTRAINT skill_name_unique IF NOT EXISTS
FOR (s:Skill)
REQUIRE s.name IS UNIQUE;

CREATE CONSTRAINT tag_name_unique IF NOT EXISTS
FOR (t:Tag)
REQUIRE t.name IS UNIQUE;

CREATE CONSTRAINT involvement_area_name_unique IF NOT EXISTS
FOR (ia:InvolvementArea)
REQUIRE ia.name IS UNIQUE;

CREATE CONSTRAINT education_level_name_unique IF NOT EXISTS
FOR (e:EducationLevel)
REQUIRE e.name IS UNIQUE;

CREATE CONSTRAINT segment_id_unique IF NOT EXISTS
FOR (s:Segment)
REQUIRE s.segmentId IS UNIQUE;

CREATE CONSTRAINT segment_name_unique IF NOT EXISTS
FOR (s:Segment)
REQUIRE s.name IS UNIQUE;

CREATE CONSTRAINT task_id_unique IF NOT EXISTS
FOR (t:Task)
REQUIRE t.taskId IS UNIQUE;

CREATE CONSTRAINT event_id_unique IF NOT EXISTS
FOR (e:Event)
REQUIRE e.eventId IS UNIQUE;

CREATE CONSTRAINT event_key_unique IF NOT EXISTS
FOR (e:Event)
REQUIRE e.eventKey IS UNIQUE;

CREATE CONSTRAINT competitor_id_unique IF NOT EXISTS
FOR (c:Competitor)
REQUIRE c.competitorId IS UNIQUE;

CREATE CONSTRAINT competitor_name_type_unique IF NOT EXISTS
FOR (c:Competitor)
REQUIRE (c.nameKey, c.competitorType) IS UNIQUE;

CREATE CONSTRAINT whatsapp_group_id_unique IF NOT EXISTS
FOR (g:WhatsAppGroup)
REQUIRE g.groupId IS UNIQUE;

CREATE CONSTRAINT whatsapp_group_name_unique IF NOT EXISTS
FOR (g:WhatsAppGroup)
REQUIRE g.name IS UNIQUE;

CREATE CONSTRAINT migration_batch_id_unique IF NOT EXISTS
FOR (m:MigrationBatch)
REQUIRE m.migrationId IS UNIQUE;

// Performance indexes
CREATE FULLTEXT INDEX person_search_fulltext IF NOT EXISTS
FOR (p:Person)
ON EACH [p.email, p.firstName, p.lastName, p.phone];

CREATE INDEX person_time_availability_updated_idx IF NOT EXISTS
FOR (p:Person)
ON (p.timeAvailability, p.updatedAt);

CREATE INDEX person_created_at_idx IF NOT EXISTS
FOR (p:Person)
ON (p.createdAt);

CREATE INDEX task_status_due_updated_idx IF NOT EXISTS
FOR (t:Task)
ON (t.status, t.dueDate, t.updatedAt);

CREATE INDEX event_status_start_end_idx IF NOT EXISTS
FOR (e:Event)
ON (e.status, e.startDate, e.endDate);

CREATE INDEX registered_for_status_updated_idx IF NOT EXISTS
FOR ()-[r:REGISTERED_FOR]-()
ON (r.status, r.updatedAt);

CREATE POINT INDEX address_location_point_idx IF NOT EXISTS
FOR (a:Address)
ON (a.location);
