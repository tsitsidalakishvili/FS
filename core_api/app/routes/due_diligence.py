from __future__ import annotations

from fastapi import APIRouter, Query

from ..db import get_client
from ..schemas import (
    DueDiligenceSubjectSearchOut,
    InvestigationSearchOut,
)


router = APIRouter(prefix="/api/v1/due-diligence", tags=["due-diligence"])


@router.get("/subjects/search", response_model=DueDiligenceSubjectSearchOut)
def search_subjects(query: str = Query(..., min_length=2), limit: int = Query(20, ge=1, le=100)):
    client = get_client()
    rows = client.run(
        """
        MATCH (s)
        WHERE (s:Person OR s:Company)
          AND (
            toLower(coalesce(s.full_name, s.name, '')) CONTAINS toLower($query)
            OR any(alias IN coalesce(s.aliases, []) WHERE toLower(alias) CONTAINS toLower($query))
          )
        OPTIONAL MATCH (s)-[:HAS_INVESTIGATION]->(run:InvestigationRun)
        RETURN
          s.id AS subject_id,
          coalesce(s.full_name, s.name, s.id) AS subject_name,
          labels(s)[0] AS subject_label,
          s.last_launch_at AS last_launch_at,
          count(DISTINCT run) AS investigation_count
        ORDER BY investigation_count DESC, toLower(subject_name) ASC
        LIMIT $limit
        """,
        {"query": query.strip(), "limit": int(limit)},
    )
    return {"items": rows}


@router.get("/investigations", response_model=InvestigationSearchOut)
def list_investigations(
    subject_name: str = Query(..., min_length=2),
    subject_type: str = Query(..., pattern="^(Person|Organization|Company)$"),
    crm_subject_source: str = "",
    crm_subject_id: str = "",
    limit: int = Query(12, ge=1, le=100),
):
    client = get_client()
    rows = client.run(
        """
        MATCH (s)
        WHERE (
            $subject_type = "Person" AND s:Person
        ) OR (
            $subject_type IN ["Organization", "Company"] AND s:Company
        )
        WITH s, toLower(coalesce(s.full_name, s.name, "")) AS normalized_name
        WHERE (
            $crm_subject_id <> ""
            AND coalesce(s.crm_subject_id, "") = $crm_subject_id
            AND coalesce(s.crm_subject_source, "") = $crm_subject_source
        ) OR normalized_name = toLower($subject_name)
        MATCH (s)-[:HAS_INVESTIGATION]->(run:InvestigationRun)
        WITH DISTINCT s, run, coalesce(run.started_at, run.completed_at, run.created_at) AS sort_time
        RETURN
          run.id AS run_id,
          s.id AS subject_id,
          coalesce(s.full_name, s.name, s.id) AS subject_name,
          labels(s)[0] AS subject_label,
          run.status AS status,
          run.run_kind AS run_kind,
          run.start_mode AS start_mode,
          run.started_at AS started_at,
          run.completed_at AS completed_at,
          coalesce(run.selected_sources, []) AS selected_sources,
          run.opensanctions_dataset AS opensanctions_dataset,
          coalesce(run.error_count, 0) AS error_count,
          run.dossier_generated_at AS dossier_generated_at,
          run.report_generated_at AS report_generated_at
        ORDER BY sort_time DESC
        LIMIT $limit
        """,
        {
            "subject_name": subject_name.strip(),
            "subject_type": subject_type.strip(),
            "crm_subject_source": crm_subject_source.strip(),
            "crm_subject_id": crm_subject_id.strip(),
            "limit": int(limit),
        },
    )
    return {"items": rows}


@router.get("/subjects/{subject_id}/investigations", response_model=InvestigationSearchOut)
def list_subject_investigations(subject_id: str, limit: int = Query(12, ge=1, le=100)):
    client = get_client()
    rows = client.run(
        """
        MATCH (s {id: $subject_id})-[:HAS_INVESTIGATION]->(run:InvestigationRun)
        RETURN
          run.id AS run_id,
          s.id AS subject_id,
          coalesce(s.full_name, s.name, s.id) AS subject_name,
          labels(s)[0] AS subject_label,
          run.status AS status,
          run.run_kind AS run_kind,
          run.start_mode AS start_mode,
          run.started_at AS started_at,
          run.completed_at AS completed_at,
          coalesce(run.selected_sources, []) AS selected_sources,
          run.opensanctions_dataset AS opensanctions_dataset,
          coalesce(run.error_count, 0) AS error_count,
          run.dossier_generated_at AS dossier_generated_at,
          run.report_generated_at AS report_generated_at
        ORDER BY coalesce(run.started_at, run.completed_at, run.created_at) DESC
        LIMIT $limit
        """,
        {"subject_id": subject_id.strip(), "limit": int(limit)},
    )
    return {"items": rows}
