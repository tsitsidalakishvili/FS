from datetime import datetime
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _is_json_compatible(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, (str, int, float, bool)):
        return True
    if isinstance(value, list):
        return all(_is_json_compatible(item) for item in value)
    if isinstance(value, dict):
        return all(isinstance(k, str) and _is_json_compatible(v) for k, v in value.items())
    return False


class ErrorBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    request_id: Optional[str] = None


class ErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    error: ErrorBody


class SubmitJobRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, strict=True)

    conversation_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_\-]+$")
    task_type: Literal["conversation_report"] = "conversation_report"
    parameters: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("parameters")
    @classmethod
    def validate_json_compatible_parameters(cls, value: Dict[str, Any]) -> Dict[str, Any]:
        if not _is_json_compatible(value):
            raise ValueError("parameters must be JSON-compatible and use string keys")
        return value


class JobResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    conversation_id: str
    task_type: str
    status: str
    requested_by: str
    requested_by_role: str
    idempotency_key: str
    request_trace_id: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class SubmitJobResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job: JobResponse
    idempotent_replay: bool


class ListJobsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    jobs: list[JobResponse]


class WorkerRunResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    processed_job_id: Optional[str] = None
    status: Literal["processed", "idle"]

