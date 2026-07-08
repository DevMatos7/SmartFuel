import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_audit_context, get_current_active_user
from app.core.exceptions import AppError
from app.core.permissions import Permission
from app.models.distribution_base import DistributionBase
from app.schemas.master_data import (
    DeactivateRequest,
    DistributionBaseCreate,
    DistributionBaseListResponse,
    DistributionBaseResponse,
    DistributionBaseUpdate,
)
from app.services.audit_service import AuditContext
from app.services.auth_service import AuthenticatedUser
from app.services.distribution_base_service import DistributionBaseService

router = APIRouter(prefix="/distribution-bases", tags=["distribution-bases"])


def _ensure_read(user: AuthenticatedUser) -> None:
    if Permission.DISTRIBUTION_BASES_READ.value not in user.permissions:
        raise AppError(
            "Você não possui permissão para executar esta ação.",
            status_code=403,
            code="FORBIDDEN",
        )


def _ensure_write(user: AuthenticatedUser) -> None:
    if Permission.DISTRIBUTION_BASES_WRITE.value not in user.permissions:
        raise AppError(
            "Você não possui permissão para executar esta ação.",
            status_code=403,
            code="FORBIDDEN",
        )


@router.get("", response_model=DistributionBaseListResponse)
async def list_distribution_bases(
    distributor_id: uuid.UUID | None = None,
    search: str | None = None,
    state: str | None = None,
    active: bool | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> DistributionBaseListResponse:
    _ensure_read(user)
    service = DistributionBaseService(db)
    items, total = await service.list_bases(
        organization_id=user.organization_id,
        distributor_id=distributor_id,
        search=search,
        state=state,
        active=active,
        page=page,
        page_size=page_size,
    )
    return DistributionBaseListResponse(
        items=[DistributionBaseResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{base_id}", response_model=DistributionBaseResponse)
async def get_distribution_base(
    base_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> DistributionBase:
    _ensure_read(user)
    service = DistributionBaseService(db)
    return await service.get_by_id(base_id, user.organization_id)


@router.post("", response_model=DistributionBaseResponse, status_code=201)
async def create_distribution_base(
    payload: DistributionBaseCreate,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    audit_ctx: AuditContext = Depends(get_audit_context),
) -> DistributionBase:
    _ensure_write(user)
    service = DistributionBaseService(db)
    base = await service.create(
        organization_id=user.organization_id,
        data=payload.model_dump(),
        audit_ctx=audit_ctx,
    )
    await db.commit()
    return base


@router.patch("/{base_id}", response_model=DistributionBaseResponse)
async def update_distribution_base(
    base_id: uuid.UUID,
    payload: DistributionBaseUpdate,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    audit_ctx: AuditContext = Depends(get_audit_context),
) -> DistributionBase:
    _ensure_write(user)
    service = DistributionBaseService(db)
    base = await service.get_by_id(base_id, user.organization_id)
    updated = await service.update(
        base=base,
        data={k: v for k, v in payload.model_dump().items() if v is not None},
        audit_ctx=audit_ctx,
    )
    await db.commit()
    return updated


@router.post("/{base_id}/deactivate", response_model=DistributionBaseResponse)
async def deactivate_distribution_base(
    base_id: uuid.UUID,
    payload: DeactivateRequest,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    audit_ctx: AuditContext = Depends(get_audit_context),
) -> DistributionBase:
    _ensure_write(user)
    service = DistributionBaseService(db)
    base = await service.get_by_id(base_id, user.organization_id)
    updated = await service.deactivate(base=base, reason=payload.reason, audit_ctx=audit_ctx)
    await db.commit()
    return updated


@router.post("/{base_id}/reactivate", response_model=DistributionBaseResponse)
async def reactivate_distribution_base(
    base_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    audit_ctx: AuditContext = Depends(get_audit_context),
) -> DistributionBase:
    _ensure_write(user)
    service = DistributionBaseService(db)
    base = await service.get_by_id(base_id, user.organization_id)
    updated = await service.reactivate(base=base, audit_ctx=audit_ctx)
    await db.commit()
    return updated
