import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_audit_context, get_current_active_user
from app.core.exceptions import AppError
from app.core.permissions import Permission
from app.models.distributor import ErpSupplier
from app.schemas.master_data import (
    ErpSupplierIgnoreRequest,
    ErpSupplierListResponse,
    ErpSupplierMapRequest,
    ErpSupplierResponse,
    ReasonRequest,
)
from app.services.audit_service import AuditContext
from app.services.auth_service import AuthService, AuthenticatedUser
from app.services.distributor_service import DistributorService

router = APIRouter(prefix="/erp-suppliers", tags=["erp-suppliers"])


def _ensure_read(user: AuthenticatedUser) -> None:
    if Permission.DISTRIBUTORS_READ.value not in user.permissions:
        raise AppError(
            "Você não possui permissão para executar esta ação.",
            status_code=403,
            code="FORBIDDEN",
        )


def _ensure_map(user: AuthenticatedUser) -> None:
    if Permission.DISTRIBUTORS_WRITE.value not in user.permissions:
        raise AppError(
            "Você não possui permissão para executar esta ação.",
            status_code=403,
            code="FORBIDDEN",
        )


async def _resolve_station_id(
    auth: AuthService,
    user: AuthenticatedUser,
    station_id: uuid.UUID | None,
) -> uuid.UUID | None:
    if station_id is not None:
        await auth.ensure_station_access(user, station_id)
        return station_id
    if user.has_all_stations_access:
        return None
    allowed = await auth.allowed_stations(user)
    if not allowed:
        return None
    if len(allowed) == 1:
        return allowed[0].id
    raise AppError(
        "Informe o posto para filtrar os fornecedores do ERP.",
        status_code=400,
        code="VALIDATION_ERROR",
    )


async def _ensure_erp_supplier_station_access(
    auth: AuthService, user: AuthenticatedUser, erp_supplier: ErpSupplier
) -> None:
    await auth.ensure_station_access(user, erp_supplier.station_id)


@router.get("", response_model=ErpSupplierListResponse)
async def list_erp_suppliers(
    station_id: uuid.UUID | None = None,
    mapping_status: str | None = None,
    distributor_id: uuid.UUID | None = None,
    search: str | None = None,
    active: bool | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> ErpSupplierListResponse:
    _ensure_read(user)
    auth = AuthService(db)
    resolved_station_id = await _resolve_station_id(auth, user, station_id)
    service = DistributorService(db)
    items, total = await service.list_erp_suppliers(
        organization_id=user.organization_id,
        station_id=resolved_station_id,
        mapping_status=mapping_status,
        distributor_id=distributor_id,
        search=search,
        active=active,
        page=page,
        page_size=page_size,
    )
    return ErpSupplierListResponse(
        items=[ErpSupplierResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{erp_supplier_id}", response_model=ErpSupplierResponse)
async def get_erp_supplier(
    erp_supplier_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> ErpSupplier:
    _ensure_read(user)
    auth = AuthService(db)
    service = DistributorService(db)
    erp_supplier = await service.get_erp_supplier_by_id(erp_supplier_id, user.organization_id)
    await _ensure_erp_supplier_station_access(auth, user, erp_supplier)
    return erp_supplier


@router.post("/{erp_supplier_id}/map", response_model=ErpSupplierResponse)
async def map_erp_supplier(
    erp_supplier_id: uuid.UUID,
    payload: ErpSupplierMapRequest,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    audit_ctx: AuditContext = Depends(get_audit_context),
) -> ErpSupplier:
    _ensure_map(user)
    auth = AuthService(db)
    service = DistributorService(db)
    erp_supplier = await service.get_erp_supplier_by_id(erp_supplier_id, user.organization_id)
    await _ensure_erp_supplier_station_access(auth, user, erp_supplier)
    updated = await service.map_erp_supplier(
        erp_supplier=erp_supplier,
        distributor_id=payload.distributor_id,
        user_id=user.id,
        reason=payload.reason,
        audit_ctx=audit_ctx,
    )
    await db.commit()
    return updated


@router.post("/{erp_supplier_id}/ignore", response_model=ErpSupplierResponse)
async def ignore_erp_supplier(
    erp_supplier_id: uuid.UUID,
    payload: ErpSupplierIgnoreRequest,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    audit_ctx: AuditContext = Depends(get_audit_context),
) -> ErpSupplier:
    _ensure_map(user)
    auth = AuthService(db)
    service = DistributorService(db)
    erp_supplier = await service.get_erp_supplier_by_id(erp_supplier_id, user.organization_id)
    await _ensure_erp_supplier_station_access(auth, user, erp_supplier)
    updated = await service.ignore_erp_supplier(
        erp_supplier=erp_supplier,
        user_id=user.id,
        reason=payload.reason,
        audit_ctx=audit_ctx,
    )
    await db.commit()
    return updated


@router.post("/{erp_supplier_id}/reopen", response_model=ErpSupplierResponse)
async def reopen_erp_supplier(
    erp_supplier_id: uuid.UUID,
    payload: ReasonRequest,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    audit_ctx: AuditContext = Depends(get_audit_context),
) -> ErpSupplier:
    _ensure_map(user)
    auth = AuthService(db)
    service = DistributorService(db)
    erp_supplier = await service.get_erp_supplier_by_id(erp_supplier_id, user.organization_id)
    await _ensure_erp_supplier_station_access(auth, user, erp_supplier)
    updated = await service.reopen_erp_supplier(
        erp_supplier=erp_supplier,
        user_id=user.id,
        reason=payload.reason,
        audit_ctx=audit_ctx,
    )
    await db.commit()
    return updated
