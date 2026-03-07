from collections.abc import Generator

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session

from ...auth import Principal, require_roles
from ...db import db_session
from ...errors import AppError
from ...models import AnalysisJob
from ...schemas import (
    JobResponse,
    ListJobsResponse,
    SubmitJobRequest,
    SubmitJobResponse,
    WorkerRunResponse,
)
from ...services.jobs import JobService
from ...worker.tasks import run_worker_once

router = APIRouter(prefix="/api/v1", tags=["jobs"])


def _to_job_response(job: AnalysisJob) -> JobResponse:
    return JobResponse(
        id=job.id,
        conversation_id=job.conversation_id,
        task_type=job.task_type,
        status=job.status,
        requested_by=job.requested_by,
        requested_by_role=job.requested_by_role,
        idempotency_key=job.idempotency_key,
        request_trace_id=job.request_trace_id,
        result=job.result,
        error_code=job.error_code,
        error_message=job.error_message,
        created_at=job.created_at,
        updated_at=job.updated_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
    )


def get_session(request: Request) -> Generator[Session, None, None]:
    yield from db_session(request.app.state.session_factory)


@router.post("/jobs", response_model=SubmitJobResponse, status_code=202)
def submit_job(
    payload: SubmitJobRequest,
    request: Request,
    idempotency_key: str = Header(..., alias="X-Idempotency-Key", min_length=8, max_length=128),
    principal: Principal = Depends(require_roles("admin", "viewer")),
    session: Session = Depends(get_session),
):
    request_id = getattr(request.state, "request_id", None)
    job, replay = JobService.submit_job(
        session=session,
        principal=principal,
        payload=payload,
        idempotency_key=idempotency_key,
        request_id=request_id,
        queue=request.app.state.task_queue,
    )
    return SubmitJobResponse(job=_to_job_response(job), idempotent_replay=replay)


@router.get("/jobs", response_model=ListJobsResponse)
def list_jobs(
    principal: Principal = Depends(require_roles("admin", "viewer")),
    session: Session = Depends(get_session),
):
    jobs = JobService.list_jobs_for_principal(session, principal)
    return ListJobsResponse(jobs=[_to_job_response(job) for job in jobs])


@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(
    job_id: str,
    principal: Principal = Depends(require_roles("admin", "viewer")),
    session: Session = Depends(get_session),
):
    job = JobService.get_job(session, principal, job_id)
    return _to_job_response(job)


@router.post("/worker/run-once", response_model=WorkerRunResponse)
def worker_run_once(
    request: Request,
    principal: Principal = Depends(require_roles("worker")),
):
    if principal.role != "worker":
        raise AppError(403, "forbidden", "Only worker role can execute this endpoint")

    processed_job_id = run_worker_once(
        session_factory=request.app.state.session_factory,
        queue=request.app.state.task_queue,
        processor=request.app.state.job_processor,
    )
    if processed_job_id:
        return WorkerRunResponse(processed_job_id=processed_job_id, status="processed")
    return WorkerRunResponse(processed_job_id=None, status="idle")

