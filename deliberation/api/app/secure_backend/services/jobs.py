from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..auth import Principal
from ..errors import AppError
from ..models import AnalysisJob, JobStatus
from ..schemas import SubmitJobRequest
from ..worker.queue import TaskQueue


class JobService:
    @staticmethod
    def submit_job(
        session: Session,
        principal: Principal,
        payload: SubmitJobRequest,
        idempotency_key: str,
        request_id: str | None,
        queue: TaskQueue,
    ) -> tuple[AnalysisJob, bool]:
        existing = session.execute(
            select(AnalysisJob).where(
                AnalysisJob.requested_by == principal.subject,
                AnalysisJob.idempotency_key == idempotency_key,
            )
        ).scalar_one_or_none()
        if existing is not None:
            return existing, True

        job = AnalysisJob(
            conversation_id=payload.conversation_id,
            task_type=payload.task_type,
            payload=payload.parameters,
            status=JobStatus.queued.value,
            requested_by=principal.subject,
            requested_by_role=principal.role,
            idempotency_key=idempotency_key,
            request_trace_id=request_id,
            queue_dedup_key=f"job:{principal.subject}:{idempotency_key}",
        )
        session.add(job)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            existing = session.execute(
                select(AnalysisJob).where(
                    AnalysisJob.requested_by == principal.subject,
                    AnalysisJob.idempotency_key == idempotency_key,
                )
            ).scalar_one_or_none()
            if existing is None:
                raise AppError(500, "job_create_failed", "Failed to persist job")
            return existing, True

        queue.enqueue(job.id)
        return job, False

    @staticmethod
    def list_jobs_for_principal(session: Session, principal: Principal) -> list[AnalysisJob]:
        stmt = select(AnalysisJob).order_by(AnalysisJob.created_at.desc())
        if principal.role != "admin":
            stmt = stmt.where(AnalysisJob.requested_by == principal.subject)
        return list(session.execute(stmt).scalars())

    @staticmethod
    def get_job(session: Session, principal: Principal, job_id: str) -> AnalysisJob:
        job = session.get(AnalysisJob, job_id)
        if job is None:
            raise AppError(status_code=404, code="not_found", message="Job not found")
        if principal.role != "admin" and job.requested_by != principal.subject:
            raise AppError(status_code=403, code="forbidden", message="Cannot access this job")
        return job

    @staticmethod
    def mark_processing(session: Session, job: AnalysisJob) -> AnalysisJob:
        if job.status == JobStatus.completed.value:
            return job
        if job.status != JobStatus.processing.value:
            job.status = JobStatus.processing.value
            job.started_at = datetime.now(timezone.utc)
            session.add(job)
            session.commit()
        return job

    @staticmethod
    def mark_completed(session: Session, job: AnalysisJob, result: dict) -> AnalysisJob:
        job.status = JobStatus.completed.value
        job.result = result
        job.error_code = None
        job.error_message = None
        job.completed_at = datetime.now(timezone.utc)
        session.add(job)
        session.commit()
        return job

    @staticmethod
    def mark_failed(session: Session, job: AnalysisJob, code: str, message: str) -> AnalysisJob:
        job.status = JobStatus.failed.value
        job.error_code = code
        job.error_message = message
        job.completed_at = datetime.now(timezone.utc)
        session.add(job)
        session.commit()
        return job

