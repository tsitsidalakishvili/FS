from __future__ import annotations

from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Query, Request, status

from .auth import (
    Actor,
    EventReadAccess,
    EventWriteAccess,
    PeopleReadAccess,
    PeopleWriteAccess,
    TaskReadAccess,
    TaskWriteAccess,
)
from .repository import Repository, get_default_repository
from .schemas import (
    DeepLinkCreate,
    DeepLinkOut,
    EventCreate,
    EventOut,
    EventRegistrationOut,
    PersonCreate,
    PersonOut,
    PersonPatch,
    PublicRegistrationCreate,
    PublicRegistrationOut,
    TaskCreate,
    TaskOut,
    TaskStatusPatch,
)


def create_app() -> FastAPI:
    app = FastAPI(title="CRM Production Backend", version="0.1.0")

    def get_repo() -> Repository:
        return get_default_repository()

    @app.get("/api/v1/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/v1/people", response_model=list[PersonOut])
    def list_people(
        _: Actor = PeopleReadAccess,
        q: str | None = Query(default=None),
        limit: int = Query(default=50, ge=1, le=500),
        includeArchived: bool = Query(default=False),
        repo: Repository = Depends(get_repo),
    ) -> list[dict]:
        return repo.list_people(q=q, limit=limit, include_archived=includeArchived)

    @app.post("/api/v1/people", response_model=PersonOut)
    def create_person(
        payload: PersonCreate,
        actor: Actor = PeopleWriteAccess,
        repo: Repository = Depends(get_repo),
    ) -> dict:
        return repo.create_person(payload.model_dump(), actor_id=actor.actor_id)

    @app.patch("/api/v1/people/{person_id}", response_model=PersonOut)
    def update_person(
        person_id: str,
        payload: PersonPatch,
        actor: Actor = PeopleWriteAccess,
        repo: Repository = Depends(get_repo),
    ) -> dict:
        try:
            return repo.update_person(person_id, payload.model_dump(exclude_none=True), actor_id=actor.actor_id)
        except KeyError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    @app.get("/api/v1/tasks", response_model=list[TaskOut])
    def list_tasks(
        _: Actor = TaskReadAccess,
        status_filter: str | None = Query(default=None, alias="status"),
        owner_id: str | None = Query(default=None, alias="ownerId"),
        limit: int = Query(default=100, ge=1, le=500),
        repo: Repository = Depends(get_repo),
    ) -> list[dict]:
        return repo.list_tasks(status=status_filter, owner_id=owner_id, limit=limit)

    @app.post("/api/v1/tasks", response_model=TaskOut)
    def create_task(
        payload: TaskCreate,
        actor: Actor = TaskWriteAccess,
        repo: Repository = Depends(get_repo),
    ) -> dict:
        try:
            return repo.create_task(payload.model_dump(), actor_id=actor.actor_id)
        except KeyError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    @app.patch("/api/v1/tasks/{task_id}/status", response_model=TaskOut)
    def update_task_status(
        task_id: str,
        payload: TaskStatusPatch,
        actor: Actor = TaskWriteAccess,
        repo: Repository = Depends(get_repo),
    ) -> dict:
        try:
            return repo.update_task_status(task_id, status=payload.status, actor_id=actor.actor_id)
        except KeyError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    @app.post("/api/v1/events", response_model=EventOut)
    def create_event(
        payload: EventCreate,
        actor: Actor = EventWriteAccess,
        repo: Repository = Depends(get_repo),
    ) -> dict:
        return repo.create_event(payload.model_dump(), actor_id=actor.actor_id)

    @app.get("/api/v1/events/{event_id}", response_model=EventOut)
    def get_event(
        event_id: str,
        _: Actor = EventReadAccess,
        repo: Repository = Depends(get_repo),
    ) -> dict:
        event = repo.get_event(event_id)
        if not event:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="event_not_found")
        return event

    @app.post("/api/v1/events/{event_id}/deeplinks", response_model=DeepLinkOut)
    def create_deeplink(
        event_id: str,
        payload: DeepLinkCreate,
        actor: Actor = EventWriteAccess,
        repo: Repository = Depends(get_repo),
    ) -> dict:
        try:
            return repo.create_deeplink(
                event_id=event_id,
                subject_person_id=payload.subjectPersonId,
                expires_in_hours=payload.expiresInHours,
                actor_id=actor.actor_id,
            )
        except KeyError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    @app.get("/api/v1/events/{event_id}/registrations", response_model=list[EventRegistrationOut])
    def list_event_registrations(
        event_id: str,
        _: Actor = EventReadAccess,
        limit: int = Query(default=200, ge=1, le=500),
        repo: Repository = Depends(get_repo),
    ) -> list[dict]:
        return repo.list_event_registrations(event_id=event_id, limit=limit)

    @app.post("/api/v1/public/registrations", response_model=PublicRegistrationOut)
    def public_registration(
        payload: PublicRegistrationCreate,
        request: Request,
        repo: Repository = Depends(get_repo),
    ) -> dict:
        request_id = request.headers.get("x-request-id") or str(uuid4())
        try:
            reg = repo.register_from_token(
                token=payload.token,
                payload=payload.model_dump(exclude={"token"}),
                request_id=request_id,
            )
        except PermissionError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(exc),
            ) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        return reg

    return app


app = create_app()

