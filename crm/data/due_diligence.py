import pandas as pd

from crm.db.neo4j import run_query


def list_investigation_runs_for_subject(
    subject_name, subject_type, crm_subject_source="", crm_subject_id="", limit=12
):
    normalized_name = str(subject_name or "").strip()
    normalized_type = str(subject_type or "").strip()
    normalized_source = str(crm_subject_source or "").strip()
    normalized_source_id = str(crm_subject_id or "").strip()
    if not normalized_name or normalized_type not in {"Person", "Organization", "Company"}:
        return pd.DataFrame()

    return run_query(
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
        WITH DISTINCT s, run, coalesce(run.started_at, run.completed_at, run.created_at) AS sortTime
        RETURN
          s.id AS subjectId,
          coalesce(s.full_name, s.name) AS subjectName,
          labels(s)[0] AS subjectLabel,
          run.id AS runId,
          run.status AS status,
          run.run_kind AS runKind,
          run.start_mode AS startMode,
          run.started_at AS startedAt,
          run.completed_at AS completedAt,
          run.selected_sources AS selectedSources,
          run.opensanctions_dataset AS opensanctionsDataset,
          coalesce(run.error_count, 0) AS errorCount,
          run.dossier_generated_at AS dossierGeneratedAt,
          run.report_generated_at AS reportGeneratedAt,
          run.crm_subject_source AS crmSubjectSource,
          run.crm_subject_id AS crmSubjectId,
          run.source_runs_json AS sourceRunsJson
        ORDER BY sortTime DESC
        LIMIT $limit
        """,
        {
            "subject_name": normalized_name,
            "subject_type": normalized_type,
            "crm_subject_source": normalized_source,
            "crm_subject_id": normalized_source_id,
            "limit": int(limit),
        },
        silent=True,
    )
