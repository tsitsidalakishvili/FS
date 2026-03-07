from datetime import datetime
from enum import Enum
from uuid import uuid4

from sqlalchemy import DateTime, Index, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class JobStatus(str, Enum):
    queued = "queued"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"
    __table_args__ = (
        UniqueConstraint("requested_by", "idempotency_key", name="uq_analysis_jobs_requester_idempotency"),
        Index("ix_analysis_jobs_status", "status"),
        Index("ix_analysis_jobs_conversation_id", "conversation_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    conversation_id: Mapped[str] = mapped_column(String(128), nullable=False)
    task_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=JobStatus.queued.value)
    requested_by: Mapped[str] = mapped_column(String(120), nullable=False)
    requested_by_role: Mapped[str] = mapped_column(String(32), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    request_trace_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    queue_dedup_key: Mapped[str | None] = mapped_column(String(200), nullable=True)

    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

