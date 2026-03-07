from __future__ import annotations

from fastapi.testclient import TestClient

from crm_backend.app.main import create_app
from crm_backend.app.repository import InMemoryRepository
import crm_backend.app.repository as repo_module


def _client() -> TestClient:
    repo_module._DEFAULT_REPO = InMemoryRepository()
    app = create_app()
    return TestClient(app)


def _admin_headers() -> dict[str, str]:
    return {"x-actor-id": "admin-1", "x-actor-role": "platform_admin"}


def test_internal_routes_are_deny_by_default() -> None:
    client = _client()
    response = client.get("/api/v1/people")
    assert response.status_code == 401


def test_write_forbidden_for_read_only_role() -> None:
    client = _client()
    response = client.post(
        "/api/v1/people",
        headers={"x-actor-id": "auditor-1", "x-actor-role": "read_only_auditor"},
        json={"email": "auditor@example.org", "firstName": "Read", "lastName": "Only"},
    )
    assert response.status_code == 403


def test_public_registration_rejects_unexpected_fields() -> None:
    client = _client()
    response = client.post(
        "/api/v1/public/registrations",
        json={"token": "not-a-real-token", "eventId": "should-be-rejected"},
    )
    assert response.status_code == 422


def test_token_bound_public_registration_flow() -> None:
    client = _client()
    headers = _admin_headers()

    person = client.post(
        "/api/v1/people",
        headers=headers,
        json={"email": "person@example.org", "firstName": "P", "lastName": "One"},
    )
    assert person.status_code == 200
    person_id = person.json()["personId"]

    event = client.post(
        "/api/v1/events",
        headers=headers,
        json={"eventKey": "event-001", "name": "Townhall"},
    )
    assert event.status_code == 200
    event_id = event.json()["eventId"]

    deeplink = client.post(
        f"/api/v1/events/{event_id}/deeplinks",
        headers=headers,
        json={"subjectPersonId": person_id, "expiresInHours": 24},
    )
    assert deeplink.status_code == 200
    token = deeplink.json()["token"]

    registration = client.post(
        "/api/v1/public/registrations",
        json={"token": token, "status": "Registered", "guestCount": 1},
    )
    assert registration.status_code == 200
    payload = registration.json()
    assert payload["eventId"] == event_id
    assert payload["status"] == "Registered"

    replay = client.post("/api/v1/public/registrations", json={"token": token})
    assert replay.status_code == 401


def test_task_lifecycle_flow() -> None:
    client = _client()
    headers = _admin_headers()

    person = client.post(
        "/api/v1/people",
        headers=headers,
        json={"email": "worker@example.org", "firstName": "Worker", "lastName": "One"},
    )
    assert person.status_code == 200
    person_id = person.json()["personId"]

    task = client.post(
        "/api/v1/tasks",
        headers=headers,
        json={"personId": person_id, "title": "Call volunteer", "ownerId": "owner-1"},
    )
    assert task.status_code == 200
    task_id = task.json()["taskId"]

    task_list = client.get("/api/v1/tasks", headers=headers)
    assert task_list.status_code == 200
    assert any(t["taskId"] == task_id for t in task_list.json())

    task_update = client.patch(
        f"/api/v1/tasks/{task_id}/status",
        headers=headers,
        json={"status": "Done"},
    )
    assert task_update.status_code == 200
    assert task_update.json()["status"] == "Done"


def test_event_registration_is_visible_to_internal_readers() -> None:
    client = _client()
    headers = _admin_headers()

    person = client.post(
        "/api/v1/people",
        headers=headers,
        json={"email": "attendee@example.org", "firstName": "Att", "lastName": "Endee"},
    )
    person_id = person.json()["personId"]
    event = client.post(
        "/api/v1/events",
        headers=headers,
        json={"eventKey": "event-002", "name": "Rally"},
    )
    event_id = event.json()["eventId"]
    deeplink = client.post(
        f"/api/v1/events/{event_id}/deeplinks",
        headers=headers,
        json={"subjectPersonId": person_id, "expiresInHours": 24},
    )
    token = deeplink.json()["token"]
    registration = client.post("/api/v1/public/registrations", json={"token": token})
    assert registration.status_code == 200

    registrations = client.get(f"/api/v1/events/{event_id}/registrations", headers=headers)
    assert registrations.status_code == 200
    assert len(registrations.json()) == 1

