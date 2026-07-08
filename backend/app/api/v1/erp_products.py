import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_audit_context, get_current_active_user
from app.core.exceptions import AppError
from app.core.permissions import Permission
from app.models.erp_product import ErpProduct
from app.schemas.master_data import (
    ErpProductBulkMapRequest,
    ErpProductBulkMapResponse,
    ErpProductBulkMapFailure,
    ErpProductIgnoreRequest,
    ErpProductListResponse,
    ErpProductMapRequest,
    ErpProductResponse,
    ProductMappingHistoryListResponse,
    ProductMappingHistoryResponse,
    ReasonRequest,
)
from app.services.audit_service import AuditContext
from app.services.auth_service import AuthService, AuthenticatedUser
from app.services.erp_product_service import ErpProductService

router = APIRouter(prefix="/erp-products", tags=["erp-products"])


def _ensure_read(user: AuthenticatedUser) -> None:
    if Permission.ERP_PRODUCTS_READ.value not in user.permissions:
        raise AppError(
            "Você não possui permissão para executar esta ação.",
            status_code=403,
            code="FORBIDDEN",
        )


def _ensure_map(user: AuthenticatedUser) -> None:
    if Permission.ERP_PRODUCTS_MAP.value not in user.permissions:
        raise AppError(
            "Você não possui permissão para executar esta ação.",
            status_code=403,
            code="FORBIDDEN",
        )


def _ensure_ignore(user: AuthenticatedUser) -> None:
    if Permission.ERP_PRODUCTS_IGNORE.value not in user.permissions:
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
        "Informe o posto para filtrar os produtos do ERP.",
        status_code=400,
        code="VALIDATION_ERROR",
    )


async def _ensure_erp_product_station_access(
    auth: AuthService, user: AuthenticatedUser, erp_product: ErpProduct
) -> None:
    await auth.ensure_station_access(user, erp_product.station_id)


@router.get("", response_model=ErpProductListResponse)
async def list_erp_products(
    station_id: uuid.UUID | None = None,
    mapping_status: str | None = None,
    canonical_product_id: uuid.UUID | None = None,
    search: str | None = None,
    source: str | None = None,
    active: bool | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> ErpProductListResponse:
    _ensure_read(user)
    auth = AuthService(db)
    resolved_station_id = await _resolve_station_id(auth, user, station_id)
    service = ErpProductService(db)
    items, total = await service.list_erp_products(
        organization_id=user.organization_id,
        station_id=resolved_station_id,
        mapping_status=mapping_status,
        canonical_product_id=canonical_product_id,
        search=search,
        source=source,
        active=active,
        page=page,
        page_size=page_size,
    )
    return ErpProductListResponse(
        items=[ErpProductResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{erp_product_id}", response_model=ErpProductResponse)
async def get_erp_product(
    erp_product_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> ErpProduct:
    _ensure_read(user)
    auth = AuthService(db)
    service = ErpProductService(db)
    erp_product = await service.get_by_id(erp_product_id, user.organization_id)
    await _ensure_erp_product_station_access(auth, user, erp_product)
    return erp_product


@router.post("/bulk-map", response_model=ErpProductBulkMapResponse)
async def bulk_map_erp_products(
    payload: ErpProductBulkMapRequest,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    audit_ctx: AuditContext = Depends(get_audit_context),
) -> ErpProductBulkMapResponse:
    _ensure_map(user)
    auth = AuthService(db)
    service = ErpProductService(db)
    for erp_id in payload.erp_product_ids:
        erp_product = await service.get_by_id(erp_id, user.organization_id)
        await _ensure_erp_product_station_access(auth, user, erp_product)
    mapped, failures = await service.bulk_map(
        organization_id=user.organization_id,
        erp_product_ids=payload.erp_product_ids,
        canonical_product_id=payload.canonical_product_id,
        user_id=user.id,
        reason=payload.reason,
        audit_ctx=audit_ctx,
    )
    await db.commit()
    return ErpProductBulkMapResponse(
        mapped=[ErpProductResponse.model_validate(i) for i in mapped],
        failures=[ErpProductBulkMapFailure(**f) for f in failures],
    )


@router.post("/{erp_product_id}/map", response_model=ErpProductResponse)
async def map_erp_product(
    erp_product_id: uuid.UUID,
    payload: ErpProductMapRequest,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    audit_ctx: AuditContext = Depends(get_audit_context),
) -> ErpProduct:
    _ensure_map(user)
    auth = AuthService(db)
    service = ErpProductService(db)
    erp_product = await service.get_by_id(erp_product_id, user.organization_id)
    await _ensure_erp_product_station_access(auth, user, erp_product)
    updated = await service.map_product(
        erp_product=erp_product,
        canonical_product_id=payload.canonical_product_id,
        user_id=user.id,
        reason=payload.reason,
        audit_ctx=audit_ctx,
    )
    await db.commit()
    return updated


@router.post("/{erp_product_id}/ignore", response_model=ErpProductResponse)
async def ignore_erp_product(
    erp_product_id: uuid.UUID,
    payload: ErpProductIgnoreRequest,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    audit_ctx: AuditContext = Depends(get_audit_context),
) -> ErpProduct:
    _ensure_ignore(user)
    auth = AuthService(db)
    service = ErpProductService(db)
    erp_product = await service.get_by_id(erp_product_id, user.organization_id)
    await _ensure_erp_product_station_access(auth, user, erp_product)
    updated = await service.ignore_product(
        erp_product=erp_product,
        user_id=user.id,
        reason=payload.reason,
        audit_ctx=audit_ctx,
    )
    await db.commit()
    return updated


@router.post("/{erp_product_id}/reopen", response_model=ErpProductResponse)
async def reopen_erp_product(
    erp_product_id: uuid.UUID,
    payload: ReasonRequest,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    audit_ctx: AuditContext = Depends(get_audit_context),
) -> ErpProduct:
    _ensure_map(user)
    auth = AuthService(db)
    service = ErpProductService(db)
    erp_product = await service.get_by_id(erp_product_id, user.organization_id)
    await _ensure_erp_product_station_access(auth, user, erp_product)
    updated = await service.reopen_product(
        erp_product=erp_product,
        user_id=user.id,
        reason=payload.reason,
        audit_ctx=audit_ctx,
    )
    await db.commit()
    return updated


@router.get("/{erp_product_id}/history", response_model=ProductMappingHistoryListResponse)
async def get_erp_product_history(
    erp_product_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> ProductMappingHistoryListResponse:
    _ensure_read(user)
    auth = AuthService(db)
    service = ErpProductService(db)
    erp_product = await service.get_by_id(erp_product_id, user.organization_id)
    await _ensure_erp_product_station_access(auth, user, erp_product)
    history = await service.get_history(erp_product=erp_product, organization_id=user.organization_id)
    return ProductMappingHistoryListResponse(
        items=[ProductMappingHistoryResponse.model_validate(h) for h in history],
    )
