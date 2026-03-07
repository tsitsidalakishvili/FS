from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from fastapi import Depends, HTTPException, Request, status


@dataclass(frozen=True)
class Actor:
    actor_id: str
    role: str


def _get_header(request: Request, key: str) -> str | None:
    value = request.headers.get(key)
    return value.strip() if value else None


def require_roles(*allowed_roles: str) -> Callable[[Request], Actor]:
    allowed = set(allowed_roles)

    async def _dep(request: Request) -> Actor:
        actor_id = _get_header(request, "x-actor-id")
        role = _get_header(request, "x-actor-role")
        if not actor_id or not role:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing internal actor identity headers.",
            )
        if role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Role is not authorized for this route.",
            )
        return Actor(actor_id=actor_id, role=role)

    return _dep


PlatformAdmin = Depends(require_roles("platform_admin"))
PeopleReadAccess = Depends(
    require_roles("platform_admin", "ops_coordinator", "case_worker", "read_only_auditor")
)
PeopleWriteAccess = Depends(require_roles("platform_admin", "ops_coordinator", "case_worker"))
EventReadAccess = Depends(
    require_roles("platform_admin", "ops_coordinator", "case_worker", "read_only_auditor")
)
EventWriteAccess = Depends(require_roles("platform_admin", "ops_coordinator"))
TaskReadAccess = Depends(
    require_roles("platform_admin", "ops_coordinator", "case_worker", "read_only_auditor")
)
TaskWriteAccess = Depends(require_roles("platform_admin", "ops_coordinator", "case_worker"))

