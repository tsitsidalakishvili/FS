from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class HealthOut(BaseModel):
    status: str
    service: str
    environment: str
    neo4j: dict[str, Any]


class PersonSummary(BaseModel):
    person_id: str
    full_name: str
    email: str | None = None
    group: str | None = None
    time_availability: str | None = None


class PersonSearchOut(BaseModel):
    items: list[PersonSummary]


class InvestigationRunSummary(BaseModel):
    run_id: str
    subject_id: str
    subject_name: str
    subject_label: str
    status: str | None = None
    run_kind: str | None = None
    start_mode: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    selected_sources: list[str] = Field(default_factory=list)
    opensanctions_dataset: str | None = None
    error_count: int = 0
    dossier_generated_at: str | None = None
    report_generated_at: str | None = None


class InvestigationSearchOut(BaseModel):
    items: list[InvestigationRunSummary]


class DueDiligenceSubjectSummary(BaseModel):
    subject_id: str
    subject_name: str
    subject_label: str
    last_launch_at: str | None = None
    investigation_count: int = 0


class DueDiligenceSubjectSearchOut(BaseModel):
    items: list[DueDiligenceSubjectSummary]


class ConversationSummary(BaseModel):
    id: str
    topic: str
    description: str | None = None
    is_open: bool = True
    allow_comment_submission: bool = True
    moderation_required: bool = False
    comments: int | None = None
    participants: int | None = None
