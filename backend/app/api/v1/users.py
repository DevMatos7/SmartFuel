import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_audit_context, get_current_active_user
from app.core.exceptions import AppError
from app.core.permissions import Permission
from app.models.user import User
from app.schemas.user import (
    ResetPasswordRequest,
    ResetPasswordResponse,
    UserCreate,
    UserListResponse,
    UserResponse,
    UserRolesUpdate,
    UserStationsUpdate,
    UserUpdate,
)
from app.schemas.station import DeactivateRequest
from app.services.audit_service import AuditContext
from app.services.auth_service import AuthenticatedUser
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


def _to_user_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        organization_id=user.organization_id,
        name=user.name,
        email=user.email,
        active=user.active,
        must_change_password=user.must_change_password,
        has_all_stations_access=user.has_all_stations_access,
        last_login_at=user.last_login_at,
        role_codes=[link.role.code for link in user.role_links],
        station_ids=[link.station_id for link in user.station_links],
    )


def _ensure_read(user: AuthenticatedUser) -> None:
    if Permission.USERS_READ.value not in user.permissions:
        raise AppError(
            "Você não possui permissão para executar esta ação.",
            status_code=403,
            code="FORBIDDEN",
        )


def _ensure_write(user: AuthenticatedUser) -> None:
    if Permission.USERS_WRITE.value not in user.permissions:
        raise AppError(
            "Você não possui permissão para executar esta ação.",
            status_code=403,
            code="FORBIDDEN",
        )


@router.get("", response_model=UserListResponse)
async def list_users(
    search: str | None = None,
    role: str | None = None,
    station_id: uuid.UUID | None = None,
    active: bool | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> UserListResponse:
    _ensure_read(user)
    service = UserService(db)
    items, total = await service.list_users(
        organization_id=user.organization_id,
        search=search,
        role=role,
        station_id=station_id,
        active=active,
        page=page,
        page_size=page_size,
    )
    return UserListResponse(
        items=[_to_user_response(u) for u in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    _ensure_read(user)
    service = UserService(db)
    target = await service._load_user(user_id)
    if target.organization_id != user.organization_id:
        raise AppError(
            "Você não possui permissão para executar esta ação.",
            status_code=403,
            code="FORBIDDEN",
        )
    return _to_user_response(target)


@router.post("", response_model=UserResponse, status_code=201)
async def create_user(
    payload: UserCreate,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    audit_ctx: AuditContext = Depends(get_audit_context),
) -> UserResponse:
    _ensure_write(user)
    service = UserService(db)
    created = await service.create_user(
        organization_id=user.organization_id,
        data=payload.model_dump(),
        actor=user,
        audit_ctx=audit_ctx,
    )
    await db.commit()
    created = await service._load_user(created.id)
    return _to_user_response(created)


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: uuid.UUID,
    payload: UserUpdate,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    audit_ctx: AuditContext = Depends(get_audit_context),
) -> UserResponse:
    _ensure_write(user)
    service = UserService(db)
    target = await service._load_user(user_id)
    if target.organization_id != user.organization_id:
        raise AppError(
            "Você não possui permissão para executar esta ação.",
            status_code=403,
            code="FORBIDDEN",
        )
    updated = await service.update_user(
        user=target,
        data={k: v for k, v in payload.model_dump().items() if v is not None},
        actor=user,
        audit_ctx=audit_ctx,
    )
    await db.commit()
    updated = await service._load_user(updated.id)
    return _to_user_response(updated)


@router.put("/{user_id}/roles", response_model=UserResponse)
async def update_user_roles(
    user_id: uuid.UUID,
    payload: UserRolesUpdate,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    audit_ctx: AuditContext = Depends(get_audit_context),
) -> UserResponse:
    if Permission.USERS_MANAGE_ROLES.value not in user.permissions:
        raise AppError(
            "Você não possui permissão para executar esta ação.",
            status_code=403,
            code="FORBIDDEN",
        )
    service = UserService(db)
    target = await service._load_user(user_id)
    if target.organization_id != user.organization_id:
        raise AppError(
            "Você não possui permissão para executar esta ação.",
            status_code=403,
            code="FORBIDDEN",
        )
    updated = await service.set_roles(
        user=target,
        role_codes=payload.role_codes,
        actor=user,
        audit_ctx=audit_ctx,
    )
    await db.commit()
    updated = await service._load_user(updated.id)
    return _to_user_response(updated)


@router.put("/{user_id}/stations", response_model=UserResponse)
async def update_user_stations(
    user_id: uuid.UUID,
    payload: UserStationsUpdate,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    audit_ctx: AuditContext = Depends(get_audit_context),
) -> UserResponse:
    if Permission.USERS_MANAGE_STATIONS.value not in user.permissions:
        raise AppError(
            "Você não possui permissão para executar esta ação.",
            status_code=403,
            code="FORBIDDEN",
        )
    service = UserService(db)
    target = await service._load_user(user_id)
    if target.organization_id != user.organization_id:
        raise AppError(
            "Você não possui permissão para executar esta ação.",
            status_code=403,
            code="FORBIDDEN",
        )
    updated = await service.set_stations(
        user=target,
        station_ids=payload.station_ids,
        has_all_stations_access=payload.has_all_stations_access,
        actor=user,
        audit_ctx=audit_ctx,
    )
    await db.commit()
    updated = await service._load_user(updated.id)
    return _to_user_response(updated)


@router.post("/{user_id}/reset-password", response_model=ResetPasswordResponse)
async def reset_password(
    user_id: uuid.UUID,
    payload: ResetPasswordRequest,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    audit_ctx: AuditContext = Depends(get_audit_context),
) -> ResetPasswordResponse:
    if Permission.USERS_RESET_PASSWORD.value not in user.permissions:
        raise AppError(
            "Você não possui permissão para executar esta ação.",
            status_code=403,
            code="FORBIDDEN",
        )
    service = UserService(db)
    target = await service._load_user(user_id)
    if target.organization_id != user.organization_id:
        raise AppError(
            "Você não possui permissão para executar esta ação.",
            status_code=403,
            code="FORBIDDEN",
        )
    password = await service.reset_password(
        user=target,
        temporary_password=payload.temporary_password,
        must_change_password=payload.must_change_password,
        audit_ctx=audit_ctx,
    )
    await db.commit()
    return ResetPasswordResponse(temporary_password=password)


@router.post("/{user_id}/deactivate", response_model=UserResponse)
async def deactivate_user(
    user_id: uuid.UUID,
    payload: DeactivateRequest,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    audit_ctx: AuditContext = Depends(get_audit_context),
) -> UserResponse:
    _ensure_write(user)
    service = UserService(db)
    target = await service._load_user(user_id)
    if target.organization_id != user.organization_id:
        raise AppError(
            "Você não possui permissão para executar esta ação.",
            status_code=403,
            code="FORBIDDEN",
        )
    updated = await service.deactivate(user=target, reason=payload.reason, actor=user, audit_ctx=audit_ctx)
    await db.commit()
    updated = await service._load_user(updated.id)
    return _to_user_response(updated)


@router.post("/{user_id}/reactivate", response_model=UserResponse)
async def reactivate_user(
    user_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    audit_ctx: AuditContext = Depends(get_audit_context),
) -> UserResponse:
    _ensure_write(user)
    service = UserService(db)
    target = await service._load_user(user_id)
    if target.organization_id != user.organization_id:
        raise AppError(
            "Você não possui permissão para executar esta ação.",
            status_code=403,
            code="FORBIDDEN",
        )
    updated = await service.reactivate(user=target, audit_ctx=audit_ctx)
    await db.commit()
    updated = await service._load_user(updated.id)
    return _to_user_response(updated)
