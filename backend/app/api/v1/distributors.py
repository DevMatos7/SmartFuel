import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_audit_context, get_current_active_user
from app.core.exceptions import AppError
from app.core.permissions import Permission
from app.models.distributor import Distributor
from app.schemas.master_data import (
    DeactivateRequest,
    DistributionBaseListResponse,
    DistributionBaseResponse,
    DistributorCreate,
    DistributorListResponse,
    DistributorResponse,
    DistributorUpdate,
)
from app.services.audit_service import AuditContext
from app.services.auth_service import AuthenticatedUser
from app.services.distribution_base_service import DistributionBaseService
from app.services.distributor_service import DistributorService

router = APIRouter(prefix="/distributors", tags=["distributors"])


def _ensure_read(user: AuthenticatedUser) -> None:
    if Permission.DISTRIBUTORS_READ.value not in user.permissions:
        raise AppError(
            "Você não possui permissão para executar esta ação.",
            status_code=403,
            code="FORBIDDEN",
        )


def _ensure_write(user: AuthenticatedUser) -> None:
    if Permission.DISTRIBUTORS_WRITE.value not in user.permissions:
        raise AppError(
            "Você não possui permissão para executar esta ação.",
            status_code=403,
            code="FORBIDDEN",
        )


def _ensure_deactivate(user: AuthenticatedUser) -> None:
    if Permission.DISTRIBUTORS_DEACTIVATE.value not in user.permissions:
        raise AppError(
            "Você não possui permissão para executar esta ação.",
            status_code=403,
            code="FORBIDDEN",
        )


@router.get("", response_model=DistributorListResponse)
async def list_distributors(
    search: str | None = None,
    registration_status: str | None = None,
    active: bool | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> DistributorListResponse:
    _ensure_read(user)
    service = DistributorService(db)
    items, total = await service.list_distributors(
        organization_id=user.organization_id,
        search=search,
        registration_status=registration_status,
        active=active,
        page=page,
        page_size=page_size,
    )
    return DistributorListResponse(
        items=[DistributorResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{distributor_id}", response_model=DistributorResponse)
async def get_distributor(
    distributor_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Distributor:
    _ensure_read(user)
    service = DistributorService(db)
    return await service.get_by_id(distributor_id, user.organization_id)


@router.get("/{distributor_id}/bases", response_model=DistributionBaseListResponse)
async def list_distributor_bases(
    distributor_id: uuid.UUID,
    search: str | None = None,
    state: str | None = None,
    active: bool | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> DistributionBaseListResponse:
    _ensure_read(user)
    distributor_service = DistributorService(db)
    await distributor_service.get_by_id(distributor_id, user.organization_id)
    base_service = DistributionBaseService(db)
    items, total = await base_service.list_bases(
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


@router.post("", response_model=DistributorResponse, status_code=201)
async def create_distributor(
    payload: DistributorCreate,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    audit_ctx: AuditContext = Depends(get_audit_context),
) -> Distributor:
    _ensure_write(user)
    service = DistributorService(db)
    distributor = await service.create(
        organization_id=user.organization_id,
        data=payload.model_dump(),
        audit_ctx=audit_ctx,
    )
    await db.commit()
    return distributor


@router.patch("/{distributor_id}", response_model=DistributorResponse)
async def update_distributor(
    distributor_id: uuid.UUID,
    payload: DistributorUpdate,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    audit_ctx: AuditContext = Depends(get_audit_context),
) -> Distributor:
    _ensure_write(user)
    service = DistributorService(db)
    distributor = await service.get_by_id(distributor_id, user.organization_id)
    updated = await service.update(
        distributor=distributor,
        data={k: v for k, v in payload.model_dump().items() if v is not None},
        audit_ctx=audit_ctx,
    )
    await db.commit()
    return updated


@router.post("/{distributor_id}/deactivate", response_model=DistributorResponse)
async def deactivate_distributor(
    distributor_id: uuid.UUID,
    payload: DeactivateRequest,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    audit_ctx: AuditContext = Depends(get_audit_context),
) -> Distributor:
    _ensure_deactivate(user)
    service = DistributorService(db)
    distributor = await service.get_by_id(distributor_id, user.organization_id)
    updated = await service.deactivate(
        distributor=distributor, reason=payload.reason, audit_ctx=audit_ctx
    )
    await db.commit()
    return updated


@router.post("/{distributor_id}/reactivate", response_model=DistributorResponse)
async def reactivate_distributor(
    distributor_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    audit_ctx: AuditContext = Depends(get_audit_context),
) -> Distributor:
    _ensure_write(user)
    service = DistributorService(db)
    distributor = await service.get_by_id(distributor_id, user.organization_id)
    updated = await service.reactivate(distributor=distributor, audit_ctx=audit_ctx)
    await db.commit()
    return updated
