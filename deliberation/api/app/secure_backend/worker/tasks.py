from typing import Optional, Protocol

from sqlalchemy.orm import Session

from ..models import AnalysisJob, JobStatus
from ..services.jobs import JobService
from .queue import TaskQueue


class JobProcessor(Protocol):
    def process(self, job: AnalysisJob) -> dict:
        """Executes the job and returns a JSON-serializable result."""


class DefaultJobProcessor:
    def process(self, job: AnalysisJob) -> dict:
        return {
            "conversation_id": job.conversation_id,
            "task_type": job.task_type,
            "summary": {
                "parameter_count": len(job.payload),
                "keys": sorted(job.payload.keys()),
            },
            "status": "ok",
        }


def run_worker_once(session_factory, queue: TaskQueue, processor: JobProcessor) -> Optional[str]:
    job_id = queue.dequeue(timeout=1)
    if not job_id:
        return None

    session: Session = session_factory()
    try:
        job = session.get(AnalysisJob, job_id)
        if job is None:
            queue.ack(job_id)
            return None
        if job.status == JobStatus.completed.value:
            queue.ack(job_id)
            return job.id

        JobService.mark_processing(session, job)
        try:
            result = processor.process(job)
            JobService.mark_completed(session, job, result)
        except Exception as exc:  # noqa: BLE001 - task failures are recorded in DB
            JobService.mark_failed(session, job, code="task_failed", message=str(exc))
        queue.ack(job_id)
        return job.id
    finally:
        session.close()

