import os

from fastapi.testclient import TestClient

os.environ["DELIBERATION_SKIP_DB_INIT"] = "true"
from deliberation.api.app.main import app


def test_healthz_returns_ok():
    with TestClient(app) as client:
        response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_readyz_ok_when_db_init_skipped(monkeypatch):
    monkeypatch.setenv("DELIBERATION_SKIP_DB_INIT", "true")
    monkeypatch.delenv("REDIS_URL", raising=False)
    with TestClient(app) as client:
        response = client.get("/readyz")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["checks"]["neo4j"]["ok"] is True


def test_metrics_endpoint_exposes_prometheus_format():
    with TestClient(app) as client:
        client.get("/healthz")
        response = client.get("/metrics")
    assert response.status_code == 200
    assert "deliberation_http_requests_total" in response.text
