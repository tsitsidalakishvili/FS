from __future__ import annotations

from fastapi import APIRouter, Query

from ..db import get_client
from ..schemas import PersonSearchOut


router = APIRouter(prefix="/api/v1/crm", tags=["crm"])


@router.get("/people/search", response_model=PersonSearchOut)
def search_people(query: str = Query(..., min_length=2), limit: int = Query(25, ge=1, le=100)):
    client = get_client()
    rows = client.run(
        """
        MATCH (p:Person)
        OPTIONAL MATCH (p)-[:CLASSIFIED_AS]->(st:SupporterType)
        WITH p, collect(DISTINCT st.name) AS types
        WITH p,
          trim(coalesce(p.firstName,'') + ' ' + coalesce(p.lastName,'')) AS fullName,
          CASE
            WHEN any(x IN types WHERE toLower(x) CONTAINS 'member') THEN 'Member'
            ELSE 'Supporter'
          END AS group
        WHERE toLower(coalesce(p.email, '')) CONTAINS toLower($query)
           OR toLower(fullName) CONTAINS toLower($query)
        RETURN
          coalesce(p.personId, p.email) AS person_id,
          CASE WHEN fullName = '' THEN coalesce(p.email, 'Unknown person') ELSE fullName END AS full_name,
          p.email AS email,
          group AS group,
          coalesce(p.timeAvailability, 'Unspecified') AS time_availability
        ORDER BY full_name
        LIMIT $limit
        """,
        {"query": query.strip(), "limit": int(limit)},
    )
    return {"items": rows}
