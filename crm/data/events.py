from uuid import uuid4

from crm.db.neo4j import run_query, run_write
from crm.utils.text import clean_text


def list_events(limit=200):
    try:
        limit = int(limit)
    except Exception:
        limit = 200
    limit = max(10, min(1000, limit))
    return run_query(
        """
        MATCH (e:Event)
        OPTIONAL MATCH (p:Person)-[r:REGISTERED_FOR]->(e)
        RETURN
          e.eventId AS eventId,
          e.eventKey AS eventKey,
          e.name AS name,
          e.startDate AS startDate,
          e.endDate AS endDate,
          e.location AS location,
          coalesce(e.status, 'Planned') AS status,
          coalesce(e.capacity, 0) AS capacity,
          count(r) AS registrations,
          coalesce(e.notes, '') AS notes
        ORDER BY e.startDate DESC
        LIMIT $limit
        """,
        {"limit": limit},
        silent=True,
    )


def create_event(payload):
    name = clean_text(payload.get("name"))
    if not name:
        return False
    event_key = clean_text(payload.get("eventKey")) or str(uuid4())
    return run_write(
        """
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
          createdAt: datetime()
        })
        """,
        {
            "eventKey": event_key,
            "name": name,
            "startDate": clean_text(payload.get("startDate")),
            "endDate": clean_text(payload.get("endDate")),
            "location": clean_text(payload.get("location")),
            "status": clean_text(payload.get("status")) or "Planned",
            "capacity": payload.get("capacity") if payload.get("capacity") is not None else 0,
            "notes": clean_text(payload.get("notes")),
        },
    )
