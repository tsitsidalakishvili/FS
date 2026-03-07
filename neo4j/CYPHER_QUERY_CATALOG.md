# Cypher Query Catalog (Critical Production Paths)

All queries are parameterized and intended for Neo4j 5.x.

## 1) Person upsert (write)
**Target latency:** p50 <= 25 ms, p95 <= 120 ms

```cypher
MERGE (p:Person {email: $email})
ON CREATE SET p.personId = randomUUID(), p.createdAt = datetime()
SET p.firstName = $firstName,
    p.lastName = $lastName,
    p.gender = $gender,
    p.age = $age,
    p.phone = $phone,
    p.timeAvailability = coalesce($timeAvailability, p.timeAvailability),
    p.about = coalesce($about, p.about),
    p.updatedAt = datetime()
WITH p
MERGE (st:SupporterType {name: $supporterType})
MERGE (p)-[r1:CLASSIFIED_AS]->(st)
ON CREATE SET r1.createdAt = datetime()
SET r1.updatedAt = datetime()
WITH p
FOREACH (_ IN CASE WHEN $address IS NULL OR trim($address) = "" THEN [] ELSE [1] END |
  MERGE (a:Address {fullAddress: $address})
  ON CREATE SET a.createdAt = datetime()
  SET a.latitude = coalesce($lat, a.latitude),
      a.longitude = coalesce($lon, a.longitude),
      a.updatedAt = datetime()
  MERGE (p)-[r2:LIVES_AT]->(a)
  ON CREATE SET r2.createdAt = datetime()
  SET r2.updatedAt = datetime()
)
RETURN p.personId AS personId;
```

## 2) Person search (read)
**Target latency:** p50 <= 40 ms, p95 <= 180 ms

```cypher
CALL {
  CALL db.index.fulltext.queryNodes("person_search_fulltext", $q) YIELD node, score
  RETURN node AS p, score
  UNION
  MATCH (p:Person)
  WHERE toLower(p.email) CONTAINS toLower($q)
     OR toLower(trim(coalesce(p.firstName, "") + " " + coalesce(p.lastName, ""))) CONTAINS toLower($q)
  RETURN p, 0.0 AS score
}
OPTIONAL MATCH (p)-[:CLASSIFIED_AS]->(st:SupporterType)
WITH p, max(score) AS score, collect(DISTINCT st.name) AS types
WITH p, score,
     CASE WHEN any(x IN types WHERE toLower(x) CONTAINS "member") THEN "Member" ELSE "Supporter" END AS grp
RETURN p.email AS email,
       coalesce(trim(p.firstName + " " + p.lastName), p.email) AS fullName,
       grp AS group
ORDER BY score DESC, fullName ASC
LIMIT $limit;
```

## 3) Person profile load (read)
**Target latency:** p50 <= 35 ms, p95 <= 150 ms

```cypher
MATCH (p:Person {email: $email})
OPTIONAL MATCH (p)-[:CLASSIFIED_AS]->(st:SupporterType)
OPTIONAL MATCH (p)-[:HAS_TAG]->(tag:Tag)
OPTIONAL MATCH (p)-[:CAN_CONTRIBUTE_WITH]->(sk:Skill)
OPTIONAL MATCH (p)-[:INTERESTED_IN]->(ia:InvolvementArea)
RETURN p.email AS email,
       p.firstName AS firstName,
       p.lastName AS lastName,
       p.phone AS phone,
       p.gender AS gender,
       p.age AS age,
       collect(DISTINCT st.name) AS supporterTypes,
       collect(DISTINCT tag.name) AS tags,
       collect(DISTINCT sk.name) AS skills,
       collect(DISTINCT ia.name) AS involvementAreas;
```

## 4) Task create (write)
**Target latency:** p50 <= 20 ms, p95 <= 100 ms

```cypher
MATCH (p:Person {email: $email})
CREATE (t:Task {
  taskId: randomUUID(),
  title: $title,
  description: $description,
  status: $status,
  dueDate: $dueDate,
  createdAt: datetime(),
  updatedAt: datetime()
})
MERGE (p)-[:HAS_TASK]->(t)
RETURN t.taskId AS taskId;
```

## 5) Task queue listing (read)
**Target latency:** p50 <= 60 ms, p95 <= 250 ms

```cypher
MATCH (p:Person)-[:HAS_TASK]->(t:Task)
OPTIONAL MATCH (p)-[:CLASSIFIED_AS]->(st:SupporterType)
WITH p, t, collect(DISTINCT st.name) AS types
WITH p, t,
     CASE WHEN any(x IN types WHERE toLower(x) CONTAINS "member") THEN "Member" ELSE "Supporter" END AS grp
WHERE ($status IS NULL OR t.status = $status)
  AND ($group IS NULL OR grp = $group)
RETURN t.taskId AS taskId,
       t.title AS title,
       t.status AS status,
       t.dueDate AS dueDate,
       p.email AS email,
       grp AS group,
       t.updatedAt AS updatedAt
ORDER BY CASE WHEN t.status = "Done" THEN 1 WHEN t.status = "Cancelled" THEN 2 ELSE 0 END,
         coalesce(t.dueDate, "9999-12-31"),
         t.createdAt DESC
LIMIT $limit;
```

## 6) Event create (write)
**Target latency:** p50 <= 20 ms, p95 <= 100 ms

```cypher
CREATE (e:Event {
  eventId: randomUUID(),
  eventKey: $eventKey,
  name: $name,
  startDate: $startDate,
  endDate: $endDate,
  location: $location,
  status: $status,
  capacity: $capacity,
  notes: $notes,
  createdAt: datetime(),
  updatedAt: datetime()
})
RETURN e.eventId AS eventId;
```

## 7) Event registration upsert (write, atomic)
**Target latency:** p50 <= 30 ms, p95 <= 140 ms

```cypher
MATCH (e:Event {eventId: $eventId})
MERGE (p:Person {email: $email})
ON CREATE SET p.personId = randomUUID(), p.createdAt = datetime()
SET p.firstName = coalesce($firstName, p.firstName),
    p.lastName = coalesce($lastName, p.lastName),
    p.phone = coalesce($phone, p.phone),
    p.updatedAt = datetime()
MERGE (p)-[r:REGISTERED_FOR]->(e)
ON CREATE SET r.registeredAt = datetime()
SET r.status = $status,
    r.notes = $notes,
    r.updatedAt = datetime()
RETURN p.personId AS personId, e.eventId AS eventId;
```

## 8) Event registration listing (read)
**Target latency:** p50 <= 80 ms, p95 <= 300 ms

```cypher
MATCH (e:Event {eventId: $eventId})<-[r:REGISTERED_FOR]-(p:Person)
OPTIONAL MATCH (p)-[:CLASSIFIED_AS]->(st:SupporterType)
WITH p, r, collect(DISTINCT st.name) AS types
RETURN p.email AS email,
       p.firstName AS firstName,
       p.lastName AS lastName,
       CASE
         WHEN any(x IN types WHERE toLower(x) CONTAINS "member") THEN "Member"
         WHEN size(types) = 0 THEN "Supporter"
         ELSE head(types)
       END AS group,
       coalesce(r.status, "Registered") AS registrationStatus,
       r.registeredAt AS registeredAt,
       r.updatedAt AS updatedAt
ORDER BY r.updatedAt DESC
LIMIT $limit;
```

## 9) Segment execution (read)
**Target latency:** p50 <= 120 ms, p95 <= 500 ms

```cypher
MATCH (p:Person)
OPTIONAL MATCH (p)-[:LIVES_AT]->(addr:Address)
OPTIONAL MATCH (p)-[:CLASSIFIED_AS]->(st:SupporterType)
WITH p, addr, collect(DISTINCT st.name) AS types
WITH p, addr,
     trim(coalesce(p.firstName, "") + " " + coalesce(p.lastName, "")) AS fullName,
     CASE WHEN any(x IN types WHERE toLower(x) CONTAINS "member") THEN "Member" ELSE "Supporter" END AS grp
OPTIONAL MATCH (p)-[:HAS_TAG]->(tag:Tag)
WITH p, addr, fullName, grp, collect(DISTINCT tag.name) AS tags
OPTIONAL MATCH (p)-[:CAN_CONTRIBUTE_WITH]->(sk:Skill)
WITH p, addr, fullName, grp, tags, collect(DISTINCT sk.name) AS skills,
     coalesce(p.effortHours, 0.0) AS effortHours,
     coalesce(addr.fullAddress, p.address, "") AS address
WHERE ($group IS NULL OR grp = $group)
  AND ($nameContains IS NULL OR toLower(fullName) CONTAINS toLower($nameContains))
  AND ($addressContains IS NULL OR toLower(address) CONTAINS toLower($addressContains))
RETURN coalesce(fullName, p.email) AS fullName,
       p.email AS email,
       grp AS group,
       address,
       effortHours,
       tags,
       skills
ORDER BY effortHours DESC
LIMIT $limit;
```

## 10) Dashboard aggregate rollup (read)
**Target latency:** p50 <= 200 ms, p95 <= 800 ms

```cypher
MATCH (p:Person)
OPTIONAL MATCH (p)-[:CLASSIFIED_AS]->(st:SupporterType)
OPTIONAL MATCH (p)-[:HAS_ACTIVITY]->(a:Activity)
OPTIONAL MATCH (p)-[r:REGISTERED_FOR]->(:Event)
OPTIONAL MATCH (p)-[:CAN_CONTRIBUTE_WITH]->(sk:Skill)
WITH p,
     collect(DISTINCT st.name) AS types,
     count(DISTINCT a) AS activityCount,
     count(DISTINCT r) AS eventJoinCount,
     count(DISTINCT CASE WHEN r.status = "Attended" THEN r END) AS eventAttendRelCount,
     collect(DISTINCT sk.name) AS skills
RETURN p.email AS email,
       p.firstName AS firstName,
       p.lastName AS lastName,
       types,
       activityCount,
       eventJoinCount,
       eventAttendRelCount,
       skills,
       coalesce(p.effortHours, 0) AS effortHours,
       coalesce(p.donationTotal, 0) AS donationTotal;
```
