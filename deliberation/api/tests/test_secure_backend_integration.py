import sys
from pathlib import Path

import fakeredis
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.secure_backend.config import Settings, TokenConfig
from app.secure_backend.main import create_app
from app.secure_backend.worker.queue import RedisTaskQueue


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _build_client(tmp_path: Path) -> TestClient:
    db_path = tmp_path / "secure_backend_test.db"
    settings = Settings(
        database_url=f"sqlite:///{db_path}",
        redis_url="redis://unused",
        queue_name="tests:secure-backend:jobs",
        request_id_header="X-Request-ID",
        tokens={
            "admin-token": TokenConfig(subject="admin-user", role="admin"),
            "worker-token": TokenConfig(subject="worker-service", role="worker"),
            "viewer-token": TokenConfig(subject="viewer-user", role="viewer"),
        },
    )
    queue = RedisTaskQueue(client=fakeredis.FakeRedis(decode_responses=True), queue_name=settings.queue_name)
    app = create_app(settings=settings, task_queue=queue)
    return TestClient(app)


def test_rejects_invalid_payload_with_structured_error(tmp_path: Path):
    with _build_client(tmp_path) as client:
        response = client.post(
            "/api/v1/jobs",
            json={
                "conversation_id": "abc",
                "task_type": "conversation_report",
                "parameters": {},
                "extra_field": "should-fail",
            },
            headers={
                **_auth("admin-token"),
                "X-Idempotency-Key": "idem-validation-1",
                "X-Request-ID": "req-validation-1",
            },
        )
        assert response.status_code == 422
        payload = response.json()
        assert payload["error"]["code"] == "validation_error"
        assert payload["error"]["request_id"] == "req-validation-1"
        assert response.headers["x-request-id"] == "req-validation-1"


def test_requires_authentication(tmp_path: Path):
    with _build_client(tmp_path) as client:
        response = client.post(
            "/api/v1/jobs",
            json={"conversation_id": "abc", "task_type": "conversation_report", "parameters": {}},
            headers={"X-Idempotency-Key": "idem-auth-1"},
        )
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "unauthorized"


def test_job_idempotency_and_worker_processing_flow(tmp_path: Path):
    with _build_client(tmp_path) as client:
        submit_headers = {
            **_auth("admin-token"),
            "X-Idempotency-Key": "idem-flow-1",
            "X-Request-ID": "req-flow-1",
        }
        payload = {
            "conversation_id": "conversation_001",
            "task_type": "conversation_report",
            "parameters": {"window_days": 14, "include_clusters": True},
        }

        first = client.post("/api/v1/jobs", json=payload, headers=submit_headers)
        assert first.status_code == 202
        first_body = first.json()
        assert first_body["idempotent_replay"] is False
        job_id = first_body["job"]["id"]
        assert first_body["job"]["status"] == "queued"
        assert first_body["job"]["request_trace_id"] == "req-flow-1"

        second = client.post("/api/v1/jobs", json=payload, headers=submit_headers)
        assert second.status_code == 202
        second_body = second.json()
        assert second_body["idempotent_replay"] is True
        assert second_body["job"]["id"] == job_id

        worker = client.post("/api/v1/worker/run-once", headers=_auth("worker-token"))
        assert worker.status_code == 200
        assert worker.json()["status"] == "processed"
        assert worker.json()["processed_job_id"] == job_id

        get_job = client.get(f"/api/v1/jobs/{job_id}", headers=_auth("admin-token"))
        assert get_job.status_code == 200
        body = get_job.json()
        assert body["status"] == "completed"
        assert body["result"]["status"] == "ok"
        assert body["result"]["conversation_id"] == "conversation_001"


def test_forbidden_cross_tenant_job_access(tmp_path: Path):
    with _build_client(tmp_path) as client:
        create_response = client.post(
            "/api/v1/jobs",
            json={"conversation_id": "conv-secure", "task_type": "conversation_report", "parameters": {}},
            headers={**_auth("admin-token"), "X-Idempotency-Key": "idem-admin-private"},
        )
        assert create_response.status_code == 202
        job_id = create_response.json()["job"]["id"]

        viewer_get = client.get(f"/api/v1/jobs/{job_id}", headers=_auth("viewer-token"))
        assert viewer_get.status_code == 403
        payload = viewer_get.json()
        assert payload["error"]["code"] == "forbidden"

