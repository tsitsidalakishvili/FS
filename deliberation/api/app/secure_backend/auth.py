from dataclasses import dataclass
from typing import Iterable

from fastapi import Depends, Header, Request

from .errors import AppError


@dataclass(frozen=True)
class Principal:
    subject: str
    role: str


def _extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise AppError(status_code=401, code="unauthorized", message="Missing Authorization header")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise AppError(status_code=401, code="unauthorized", message="Authorization must use Bearer token")
    return token


def get_principal(request: Request, authorization: str | None = Header(default=None)) -> Principal:
    token = _extract_bearer_token(authorization)
    token_cfg = request.app.state.settings.tokens.get(token)
    if token_cfg is None:
        raise AppError(status_code=401, code="unauthorized", message="Invalid API token")
    return Principal(subject=token_cfg.subject, role=token_cfg.role)


def require_roles(*roles: str):
    allowed = set(roles)

    def _dependency(principal: Principal = Depends(get_principal)) -> Principal:
        if principal.role not in allowed:
            raise AppError(
                status_code=403,
                code="forbidden",
                message="Token role does not have access to this resource",
                details={"allowed_roles": sorted(allowed), "actual_role": principal.role},
            )
        return principal

    return _dependency

