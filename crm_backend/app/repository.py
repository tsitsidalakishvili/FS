from __future__ import annotations

import hashlib
import os
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Protocol
from uuid import uuid4

from neo4j import GraphDatabase, basic_auth


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _to_iso(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if hasattr(value, "to_native"):
        native = value.to_native()
        return native if isinstance(native, datetime) else utc_now()
    if hasattr(value, "isoformat"):
        try:
            parsed = datetime.fromisoformat(value.isoformat())
            return parsed
        except Exception:
            return utc_now()
    return utc_now()


def _node_to_dict(node: Any) -> dict[str, Any]:
    data = dict(node)
    for key, value in list(data.items()):
        if hasattr(value, "to_native"):
            data[key] = value.to_native()
    return data


class Repository(Protocol):
    def list_people(self, *, q: str | None, limit: int, include_archived: bool) -> list[dict[str, Any]]: ...

    def create_person(self, payload: dict[str, Any], *, actor_id: str) -> dict[str, Any]: ...

    def update_person(self, person_id: str, payload: dict[str, Any], *, actor_id: str) -> dict[str, Any]: ...

    def list_tasks(self, *, status: str | None, owner_id: str | None, limit: int) -> list[dict[str, Any]]: ...

    def create_task(self, payload: dict[str, Any], *, actor_id: str) -> dict[str, Any]: ...

    def update_task_status(self, task_id: str, *, status: str, actor_id: str) -> dict[str, Any]: ...

    def create_event(self, payload: dict[str, Any], *, actor_id: str) -> dict[str, Any]: ...

    def list_events(self, *, limit: int) -> list[dict[str, Any]]: ...

    def get_event(self, event_id: str) -> dict[str, Any] | None: ...

    def create_deeplink(
        self,
        *,
        event_id: str,
        subject_person_id: str,
        expires_in_hours: int,
        actor_id: str,
    ) -> dict[str, Any]: ...

    def list_event_registrations(self, *, event_id: str, limit: int) -> list[dict[str, Any]]: ...

    def register_from_token(self, *, token: str, payload: dict[str, Any], request_id: str) -> dict[str, Any]: ...


@dataclass
class InMemoryRepository:
    people: dict[str, dict[str, Any]]
    tasks: dict[str, dict[str, Any]]
    events: dict[str, dict[str, Any]]
    deep_links: dict[str, dict[str, Any]]
    token_use: set[str]
    registrations: dict[str, dict[str, Any]]

    def __init__(self) -> None:
        self.people = {}
        self.tasks = {}
        self.events = {}
        self.deep_links = {}
        self.token_use = set()
        self.registrations = {}

    def list_people(self, *, q: str | None, limit: int, include_archived: bool) -> list[dict[str, Any]]:
        rows = list(self.people.values())
        if not include_archived:
            rows = [r for r in rows if r.get("status") != "ARCHIVED"]
        if q:
            qn = q.lower()
            rows = [
                r
                for r in rows
                if qn in str(r.get("email", "")).lower()
                or qn in f"{r.get('firstName','')} {r.get('lastName','')}".lower()
            ]
        rows.sort(key=lambda r: (str(r.get("lastName", "")), str(r.get("firstName", ""))))
        return rows[:limit]

    def create_person(self, payload: dict[str, Any], *, actor_id: str) -> dict[str, Any]:
        email = str(payload["email"]).strip().lower()
        now = utc_now()
        for person in self.people.values():
            if person["email"] == email:
                person.update(
                    {
                        "firstName": payload.get("firstName"),
                        "lastName": payload.get("lastName"),
                        "phone": payload.get("phone"),
                        "updatedAt": now,
                    }
                )
                return person
        person_id = str(uuid4())
        person = {
            "personId": person_id,
            "email": email,
            "firstName": payload.get("firstName"),
            "lastName": payload.get("lastName"),
            "phone": payload.get("phone"),
            "status": "ACTIVE",
            "createdAt": now,
            "updatedAt": now,
            "createdBy": actor_id,
            "updatedBy": actor_id,
        }
        self.people[person_id] = person
        return person

    def update_person(self, person_id: str, payload: dict[str, Any], *, actor_id: str) -> dict[str, Any]:
        person = self.people.get(person_id)
        if not person:
            raise KeyError("person_not_found")
        for key in ("firstName", "lastName", "phone", "status"):
            if key in payload and payload[key] is not None:
                person[key] = payload[key]
        person["updatedAt"] = utc_now()
        person["updatedBy"] = actor_id
        return person

    def list_tasks(self, *, status: str | None, owner_id: str | None, limit: int) -> list[dict[str, Any]]:
        rows = list(self.tasks.values())
        if status:
            rows = [r for r in rows if r.get("status") == status]
        if owner_id:
            rows = [r for r in rows if r.get("ownerId") == owner_id]
        rows.sort(key=lambda r: str(r.get("createdAt")))
        return rows[:limit]

    def create_task(self, payload: dict[str, Any], *, actor_id: str) -> dict[str, Any]:
        person = self.people.get(payload["personId"])
        if not person:
            raise KeyError("person_not_found")
        now = utc_now()
        task = {
            "taskId": str(uuid4()),
            "personId": person["personId"],
            "title": payload["title"],
            "ownerId": payload["ownerId"],
            "status": "Open",
            "description": payload.get("description"),
            "dueDate": payload.get("dueDate"),
            "createdAt": now,
            "updatedAt": now,
            "createdBy": actor_id,
            "updatedBy": actor_id,
        }
        self.tasks[task["taskId"]] = task
        return task

    def update_task_status(self, task_id: str, *, status: str, actor_id: str) -> dict[str, Any]:
        task = self.tasks.get(task_id)
        if not task:
            raise KeyError("task_not_found")
        task["status"] = status
        task["updatedAt"] = utc_now()
        task["updatedBy"] = actor_id
        return task

    def create_event(self, payload: dict[str, Any], *, actor_id: str) -> dict[str, Any]:
        now = utc_now()
        event = {
            "eventId": str(uuid4()),
            "eventKey": payload["eventKey"],
            "name": payload["name"],
            "published": bool(payload.get("published", False)),
            "createdAt": now,
            "updatedAt": now,
            "createdBy": actor_id,
            "updatedBy": actor_id,
        }
        self.events[event["eventId"]] = event
        return event

    def get_event(self, event_id: str) -> dict[str, Any] | None:
        return self.events.get(event_id)

    def list_events(self, *, limit: int) -> list[dict[str, Any]]:
        rows = list(self.events.values())
        rows.sort(key=lambda r: r["createdAt"], reverse=True)
        return rows[:limit]

    def create_deeplink(
        self,
        *,
        event_id: str,
        subject_person_id: str,
        expires_in_hours: int,
        actor_id: str,
    ) -> dict[str, Any]:
        if event_id not in self.events:
            raise KeyError("event_not_found")
        if subject_person_id not in self.people:
            raise KeyError("person_not_found")
        token = secrets.token_urlsafe(32)
        self.deep_links[token] = {
            "eventId": event_id,
            "subjectPersonId": subject_person_id,
            "jti": str(uuid4()),
            "expiresAt": utc_now() + timedelta(hours=expires_in_hours),
            "status": "ACTIVE",
            "createdBy": actor_id,
        }
        return {"token": token, "expiresAt": self.deep_links[token]["expiresAt"]}

    def list_event_registrations(self, *, event_id: str, limit: int) -> list[dict[str, Any]]:
        rows = [r for r in self.registrations.values() if r["eventId"] == event_id]
        rows.sort(key=lambda r: r["createdAt"], reverse=True)
        return rows[:limit]

    def register_from_token(self, *, token: str, payload: dict[str, Any], request_id: str) -> dict[str, Any]:
        token_row = self.deep_links.get(token)
        if not token_row:
            raise PermissionError("invalid_token")
        if token_row["status"] != "ACTIVE" or token_row["expiresAt"] <= utc_now():
            raise PermissionError("invalid_token")
        jti = token_row["jti"]
        if jti in self.token_use:
            raise RuntimeError("token_replay")
        self.token_use.add(jti)
        token_row["status"] = "CONSUMED"

        reg_key = f"token:{jti}"
        now = utc_now()
        registration = {
            "registrationId": str(uuid4()),
            "registrationKey": reg_key,
            "personId": token_row["subjectPersonId"],
            "eventId": token_row["eventId"],
            "status": payload.get("status", "Registered"),
            "guestCount": payload.get("guestCount"),
            "accessibilityNeeds": payload.get("accessibilityNeeds"),
            "consentVersion": payload.get("consentVersion"),
            "notes": payload.get("notes"),
            "createdAt": now,
            "updatedAt": now,
            "createdBy": "public_registration",
            "updatedBy": "public_registration",
            "lastRequestId": request_id,
        }
        self.registrations[registration["registrationId"]] = registration
        return registration


class Neo4jRepository:
    def __init__(self, *, uri: str, username: str, password: str, database: str = "neo4j"):
        self.database = database
        self.driver = GraphDatabase.driver(uri, auth=basic_auth(username, password))

    @classmethod
    def from_env(cls) -> Neo4jRepository | None:
        uri = os.getenv("NEO4J_URI")
        username = os.getenv("NEO4J_USER") or os.getenv("NEO4J_USERNAME")
        password = os.getenv("NEO4J_PASSWORD")
        database = os.getenv("NEO4J_DATABASE", "neo4j")
        if not uri or not username or not password:
            return None
        return cls(uri=uri, username=username, password=password, database=database)

    def close(self) -> None:
        self.driver.close()

    def _read(self, query: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        with self.driver.session(database=self.database) as session:
            if hasattr(session, "execute_read"):
                records = session.execute_read(lambda tx: list(tx.run(query, params or {})))
            else:
                records = session.read_transaction(lambda tx: list(tx.run(query, params or {})))
        return [record.data() for record in records]

    def _write(self, query: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        def _run(tx: Any) -> list[Any]:
            return list(tx.run(query, params or {}))

        with self.driver.session(database=self.database) as session:
            if hasattr(session, "execute_write"):
                records = session.execute_write(_run)
            else:
                records = session.write_transaction(_run)
        return [record.data() for record in records]

    def init_constraints(self) -> None:
        statements = [
            "CREATE CONSTRAINT person_id_unique IF NOT EXISTS FOR (p:Person) REQUIRE p.personId IS UNIQUE",
            "CREATE CONSTRAINT person_email_unique IF NOT EXISTS FOR (p:Person) REQUIRE p.email IS UNIQUE",
            "CREATE CONSTRAINT task_id_unique IF NOT EXISTS FOR (t:Task) REQUIRE t.taskId IS UNIQUE",
            "CREATE CONSTRAINT event_id_unique IF NOT EXISTS FOR (e:Event) REQUIRE e.eventId IS UNIQUE",
            "CREATE CONSTRAINT event_key_unique IF NOT EXISTS FOR (e:Event) REQUIRE e.eventKey IS UNIQUE",
            "CREATE CONSTRAINT registration_key_unique IF NOT EXISTS FOR (r:Registration) REQUIRE r.registrationKey IS UNIQUE",
            "CREATE CONSTRAINT deeplink_hash_unique IF NOT EXISTS FOR (d:DeepLinkToken) REQUIRE d.tokenHash IS UNIQUE",
            "CREATE CONSTRAINT tokenuse_jti_unique IF NOT EXISTS FOR (u:TokenUse) REQUIRE u.jti IS UNIQUE",
        ]
        for statement in statements:
            self._write(statement)

    def list_people(self, *, q: str | None, limit: int, include_archived: bool) -> list[dict[str, Any]]:
        rows = self._read(
            """
            MATCH (p:Person)
            WHERE ($includeArchived = true OR p.status = 'ACTIVE')
              AND (
                $q IS NULL OR $q = '' OR
                toLower(coalesce(p.email, '')) CONTAINS toLower($q) OR
                toLower(coalesce(p.firstName, '') + ' ' + coalesce(p.lastName, '')) CONTAINS toLower($q)
              )
            RETURN p
            ORDER BY coalesce(p.lastName, ''), coalesce(p.firstName, '')
            LIMIT $limit
            """,
            {"q": q, "limit": int(limit), "includeArchived": bool(include_archived)},
        )
        result: list[dict[str, Any]] = []
        for row in rows:
            person = _node_to_dict(row["p"])
            person["createdAt"] = _to_iso(person.get("createdAt"))
            person["updatedAt"] = _to_iso(person.get("updatedAt"))
            result.append(person)
        return result

    def create_person(self, payload: dict[str, Any], *, actor_id: str) -> dict[str, Any]:
        rows = self._write(
            """
            MERGE (p:Person {email: toLower(trim($email))})
            ON CREATE SET
              p.personId = randomUUID(),
              p.status = 'ACTIVE',
              p.createdAt = datetime(),
              p.createdBy = $actor
            SET
              p.firstName = $firstName,
              p.lastName = $lastName,
              p.phone = $phone,
              p.updatedAt = datetime(),
              p.updatedBy = $actor
            RETURN p
            """,
            {
                "email": payload["email"],
                "firstName": payload.get("firstName"),
                "lastName": payload.get("lastName"),
                "phone": payload.get("phone"),
                "actor": actor_id,
            },
        )
        person = _node_to_dict(rows[0]["p"])
        person["createdAt"] = _to_iso(person.get("createdAt"))
        person["updatedAt"] = _to_iso(person.get("updatedAt"))
        return person

    def update_person(self, person_id: str, payload: dict[str, Any], *, actor_id: str) -> dict[str, Any]:
        updates = {k: v for k, v in payload.items() if v is not None}
        rows = self._write(
            """
            MATCH (p:Person {personId: $personId})
            SET p += $updates,
                p.updatedAt = datetime(),
                p.updatedBy = $actor
            RETURN p
            """,
            {"personId": person_id, "updates": updates, "actor": actor_id},
        )
        if not rows:
            raise KeyError("person_not_found")
        person = _node_to_dict(rows[0]["p"])
        person["createdAt"] = _to_iso(person.get("createdAt"))
        person["updatedAt"] = _to_iso(person.get("updatedAt"))
        return person

    def list_tasks(self, *, status: str | None, owner_id: str | None, limit: int) -> list[dict[str, Any]]:
        rows = self._read(
            """
            MATCH (p:Person)-[:HAS_TASK]->(t:Task)
            WHERE ($status IS NULL OR t.status = $status)
              AND ($ownerId IS NULL OR t.ownerId = $ownerId)
            RETURN t, p.personId AS personId
            ORDER BY t.createdAt DESC
            LIMIT $limit
            """,
            {"status": status, "ownerId": owner_id, "limit": int(limit)},
        )
        tasks: list[dict[str, Any]] = []
        for row in rows:
            task = _node_to_dict(row["t"])
            task["personId"] = row["personId"]
            task["createdAt"] = _to_iso(task.get("createdAt"))
            task["updatedAt"] = _to_iso(task.get("updatedAt"))
            tasks.append(task)
        return tasks

    def create_task(self, payload: dict[str, Any], *, actor_id: str) -> dict[str, Any]:
        rows = self._write(
            """
            MATCH (p:Person {personId: $personId})
            CREATE (t:Task {
              taskId: randomUUID(),
              title: $title,
              ownerId: $ownerId,
              status: 'Open',
              description: $description,
              dueDate: $dueDate,
              createdAt: datetime(),
              updatedAt: datetime(),
              createdBy: $actor,
              updatedBy: $actor
            })
            MERGE (p)-[:HAS_TASK]->(t)
            RETURN t, p.personId AS personId
            """,
            {
                "personId": payload["personId"],
                "title": payload["title"],
                "ownerId": payload["ownerId"],
                "description": payload.get("description"),
                "dueDate": payload.get("dueDate"),
                "actor": actor_id,
            },
        )
        if not rows:
            raise KeyError("person_not_found")
        task = _node_to_dict(rows[0]["t"])
        task["personId"] = rows[0]["personId"]
        task["createdAt"] = _to_iso(task.get("createdAt"))
        task["updatedAt"] = _to_iso(task.get("updatedAt"))
        return task

    def update_task_status(self, task_id: str, *, status: str, actor_id: str) -> dict[str, Any]:
        rows = self._write(
            """
            MATCH (t:Task {taskId: $taskId})
            OPTIONAL MATCH (p:Person)-[:HAS_TASK]->(t)
            SET t.status = $status,
                t.updatedAt = datetime(),
                t.updatedBy = $actor
            RETURN t, p.personId AS personId
            """,
            {"taskId": task_id, "status": status, "actor": actor_id},
        )
        if not rows:
            raise KeyError("task_not_found")
        task = _node_to_dict(rows[0]["t"])
        task["personId"] = rows[0]["personId"]
        task["createdAt"] = _to_iso(task.get("createdAt"))
        task["updatedAt"] = _to_iso(task.get("updatedAt"))
        return task

    def create_event(self, payload: dict[str, Any], *, actor_id: str) -> dict[str, Any]:
        rows = self._write(
            """
            CREATE (e:Event {
              eventId: randomUUID(),
              eventKey: $eventKey,
              name: $name,
              published: $published,
              createdAt: datetime(),
              updatedAt: datetime(),
              createdBy: $actor,
              updatedBy: $actor
            })
            RETURN e
            """,
            {
                "eventKey": payload["eventKey"],
                "name": payload["name"],
                "published": bool(payload.get("published", False)),
                "actor": actor_id,
            },
        )
        event = _node_to_dict(rows[0]["e"])
        event["createdAt"] = _to_iso(event.get("createdAt"))
        event["updatedAt"] = _to_iso(event.get("updatedAt"))
        return event

    def get_event(self, event_id: str) -> dict[str, Any] | None:
        rows = self._read("MATCH (e:Event {eventId: $eventId}) RETURN e", {"eventId": event_id})
        if not rows:
            return None
        event = _node_to_dict(rows[0]["e"])
        event["createdAt"] = _to_iso(event.get("createdAt"))
        event["updatedAt"] = _to_iso(event.get("updatedAt"))
        return event

    def list_events(self, *, limit: int) -> list[dict[str, Any]]:
        rows = self._read(
            """
            MATCH (e:Event)
            RETURN e
            ORDER BY e.createdAt DESC
            LIMIT $limit
            """,
            {"limit": int(limit)},
        )
        result: list[dict[str, Any]] = []
        for row in rows:
            event = _node_to_dict(row["e"])
            event["createdAt"] = _to_iso(event.get("createdAt"))
            event["updatedAt"] = _to_iso(event.get("updatedAt"))
            result.append(event)
        return result

    def create_deeplink(
        self,
        *,
        event_id: str,
        subject_person_id: str,
        expires_in_hours: int,
        actor_id: str,
    ) -> dict[str, Any]:
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        jti = str(uuid4())
        rows = self._write(
            """
            MATCH (e:Event {eventId: $eventId})
            MATCH (p:Person {personId: $subjectPersonId})
            CREATE (d:DeepLinkToken {
              tokenHash: $tokenHash,
              jti: $jti,
              eventId: e.eventId,
              subjectPersonId: p.personId,
              status: 'ACTIVE',
              scopes: ['registration:write'],
              expiresAt: datetime($expiresAt),
              createdAt: datetime(),
              createdBy: $actor
            })
            MERGE (d)-[:RESOLVES_TO]->(e)
            RETURN d.expiresAt AS expiresAt
            """,
            {
                "eventId": event_id,
                "subjectPersonId": subject_person_id,
                "tokenHash": token_hash,
                "jti": jti,
                "expiresAt": (utc_now() + timedelta(hours=expires_in_hours)).isoformat(),
                "actor": actor_id,
            },
        )
        if not rows:
            raise KeyError("event_or_person_not_found")
        return {"token": token, "expiresAt": _to_iso(rows[0]["expiresAt"])}

    def list_event_registrations(self, *, event_id: str, limit: int) -> list[dict[str, Any]]:
        rows = self._read(
            """
            MATCH (r:Registration)-[:FOR_EVENT]->(e:Event {eventId: $eventId})
            MATCH (p:Person)-[:SUBMITTED]->(r)
            RETURN r, p.personId AS personId
            ORDER BY r.createdAt DESC
            LIMIT $limit
            """,
            {"eventId": event_id, "limit": int(limit)},
        )
        result: list[dict[str, Any]] = []
        for row in rows:
            reg = _node_to_dict(row["r"])
            reg["personId"] = row["personId"]
            reg["createdAt"] = _to_iso(reg.get("createdAt"))
            reg["updatedAt"] = _to_iso(reg.get("updatedAt"))
            result.append(reg)
        return result

    def register_from_token(self, *, token: str, payload: dict[str, Any], request_id: str) -> dict[str, Any]:
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        rows = self._write(
            """
            MATCH (d:DeepLinkToken {tokenHash: $tokenHash})
            WHERE d.status = 'ACTIVE'
              AND d.expiresAt > datetime()
              AND 'registration:write' IN d.scopes
            MERGE (u:TokenUse {jti: d.jti})
              ON CREATE SET u.requestId = $requestId, u.usedAt = datetime()
            WITH d, u
            WHERE u.requestId = $requestId
            MATCH (e:Event {eventId: d.eventId})
            MERGE (p:Person {personId: d.subjectPersonId})
              ON CREATE SET
                p.status = 'ACTIVE',
                p.createdAt = datetime(),
                p.updatedAt = datetime(),
                p.createdBy = 'public_registration',
                p.updatedBy = 'public_registration'
            MERGE (r:Registration {registrationKey: 'token:' + d.jti})
              ON CREATE SET
                r.registrationId = randomUUID(),
                r.createdAt = datetime(),
                r.createdBy = 'public_registration'
            SET
              r.status = $status,
              r.guestCount = $guestCount,
              r.accessibilityNeeds = $accessibilityNeeds,
              r.consentVersion = $consentVersion,
              r.notes = $notes,
              r.updatedAt = datetime(),
              r.updatedBy = 'public_registration',
              r.lastRequestId = $requestId
            MERGE (p)-[:SUBMITTED]->(r)
            MERGE (r)-[:FOR_EVENT]->(e)
            SET
              d.status = 'CONSUMED',
              d.consumedAt = coalesce(d.consumedAt, datetime()),
              d.consumedByRequestId = coalesce(d.consumedByRequestId, $requestId)
            RETURN r, e.eventId AS eventId
            """,
            {
                "tokenHash": token_hash,
                "requestId": request_id,
                "status": payload.get("status", "Registered"),
                "guestCount": payload.get("guestCount"),
                "accessibilityNeeds": payload.get("accessibilityNeeds"),
                "consentVersion": payload.get("consentVersion"),
                "notes": payload.get("notes"),
            },
        )
        if not rows:
            raise PermissionError("invalid_or_replayed_token")
        reg = _node_to_dict(rows[0]["r"])
        reg["eventId"] = rows[0]["eventId"]
        reg["createdAt"] = _to_iso(reg.get("createdAt"))
        reg["updatedAt"] = _to_iso(reg.get("updatedAt"))
        return reg


_DEFAULT_REPO: Repository | None = None


def get_default_repository() -> Repository:
    global _DEFAULT_REPO
    if _DEFAULT_REPO is not None:
        return _DEFAULT_REPO
    neo4j_repo = Neo4jRepository.from_env()
    if neo4j_repo is not None:
        neo4j_repo.init_constraints()
        _DEFAULT_REPO = neo4j_repo
    else:
        _DEFAULT_REPO = InMemoryRepository()
    return _DEFAULT_REPO

