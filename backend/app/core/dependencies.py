import uuid
from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Header, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import AppError
from app.core.middleware import get_request_id
from app.core.permissions import Permission
from app.services.audit_service import AuditContext
from app.services.auth_service import AuthService, AuthenticatedUser

security = HTTPBearer(auto_error=False)


def _audit_context(request: Request, user: AuthenticatedUser | None = None) -> AuditContext:
    return AuditContext(
        organization_id=user.organization_id if user else None,
        user_id=user.id if user else None,
        ip_address=request.client.host if request.client else None,
        request_id=get_request_id(request),
    )


async def get_current_user_optional(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuthenticatedUser | None:
    if credentials is None or not credentials.credentials:
        return None
    auth = AuthService(db)
    return await auth.get_current_user_from_token(credentials.credentials)


async def get_current_user(
    user: Annotated[AuthenticatedUser | None, Depends(get_current_user_optional)],
) -> AuthenticatedUser:
    if user is None:
        raise AppError("Sua sessão expirou. Entre novamente.", status_code=401, code="SESSION_EXPIRED")
    return user


async def get_current_active_user(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> AuthenticatedUser:
    if user.must_change_password:
        raise AppError(
            "É necessário alterar sua senha antes de continuar.",
            status_code=403,
            code="MUST_CHANGE_PASSWORD",
        )
    return user


async def get_audit_context(
    request: Request,
    user: Annotated[AuthenticatedUser | None, Depends(get_current_user_optional)],
) -> AuditContext:
    return _audit_context(request, user)


def require_permission(permission: Permission) -> Callable:
    async def _checker(user: Annotated[AuthenticatedUser, Depends(get_current_user)]) -> AuthenticatedUser:
        if permission.value not in user.permissions:
            raise AppError(
                "Você não possui permissão para executar esta ação.",
                status_code=403,
                code="FORBIDDEN",
            )
        return user

    return _checker


def require_password_changed() -> Callable:
    async def _checker(user: Annotated[AuthenticatedUser, Depends(get_current_user)]) -> AuthenticatedUser:
        if user.must_change_password:
            raise AppError(
                "É necessário alterar sua senha antes de continuar.",
                status_code=403,
                code="MUST_CHANGE_PASSWORD",
            )
        return user

    return _checker


async def get_optional_station_id(
    x_station_id: Annotated[str | None, Header(alias="X-Station-Id")] = None,
) -> uuid.UUID | None:
    if not x_station_id:
        return None
    try:
        return uuid.UUID(x_station_id)
    except ValueError as exc:
        raise AppError("Posto inválido.", status_code=400, code="VALIDATION_ERROR") from exc
