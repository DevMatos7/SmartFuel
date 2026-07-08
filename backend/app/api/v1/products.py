import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_audit_context, get_current_active_user
from app.core.exceptions import AppError
from app.core.permissions import Permission
from app.models.product import Product
from app.schemas.master_data import (
    DeactivateRequest,
    ProductCreate,
    ProductListResponse,
    ProductResponse,
    ProductUpdate,
)
from app.services.audit_service import AuditContext
from app.services.auth_service import AuthenticatedUser
from app.services.product_service import ProductService

router = APIRouter(prefix="/products", tags=["products"])


def _ensure_read(user: AuthenticatedUser) -> None:
    if Permission.PRODUCTS_READ.value not in user.permissions:
        raise AppError(
            "Você não possui permissão para executar esta ação.",
            status_code=403,
            code="FORBIDDEN",
        )


def _ensure_write(user: AuthenticatedUser) -> None:
    if Permission.PRODUCTS_WRITE.value not in user.permissions:
        raise AppError(
            "Você não possui permissão para executar esta ação.",
            status_code=403,
            code="FORBIDDEN",
        )


def _ensure_deactivate(user: AuthenticatedUser) -> None:
    if Permission.PRODUCTS_DEACTIVATE.value not in user.permissions:
        raise AppError(
            "Você não possui permissão para executar esta ação.",
            status_code=403,
            code="FORBIDDEN",
        )


@router.get("", response_model=ProductListResponse)
async def list_products(
    search: str | None = None,
    fuel_family: str | None = None,
    commercial_variant: str | None = None,
    active: bool | None = None,
    purchasable: bool | None = None,
    sellable: bool | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> ProductListResponse:
    _ensure_read(user)
    service = ProductService(db)
    items, total = await service.list_products(
        organization_id=user.organization_id,
        search=search,
        fuel_family=fuel_family,
        commercial_variant=commercial_variant,
        active=active,
        purchasable=purchasable,
        sellable=sellable,
        page=page,
        page_size=page_size,
    )
    return ProductListResponse(
        items=[ProductResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Product:
    _ensure_read(user)
    service = ProductService(db)
    return await service.get_by_id(product_id, user.organization_id)


@router.post("", response_model=ProductResponse, status_code=201)
async def create_product(
    payload: ProductCreate,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    audit_ctx: AuditContext = Depends(get_audit_context),
) -> Product:
    _ensure_write(user)
    service = ProductService(db)
    product = await service.create(
        organization_id=user.organization_id,
        data=payload.model_dump(),
        audit_ctx=audit_ctx,
    )
    await db.commit()
    return product


@router.patch("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: uuid.UUID,
    payload: ProductUpdate,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    audit_ctx: AuditContext = Depends(get_audit_context),
) -> Product:
    _ensure_write(user)
    service = ProductService(db)
    product = await service.get_by_id(product_id, user.organization_id)
    updated = await service.update(
        product=product,
        data={k: v for k, v in payload.model_dump().items() if v is not None},
        audit_ctx=audit_ctx,
    )
    await db.commit()
    return updated


@router.post("/{product_id}/deactivate", response_model=ProductResponse)
async def deactivate_product(
    product_id: uuid.UUID,
    payload: DeactivateRequest,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    audit_ctx: AuditContext = Depends(get_audit_context),
) -> Product:
    _ensure_deactivate(user)
    service = ProductService(db)
    product = await service.get_by_id(product_id, user.organization_id)
    updated = await service.deactivate(product=product, reason=payload.reason, audit_ctx=audit_ctx)
    await db.commit()
    return updated


@router.post("/{product_id}/reactivate", response_model=ProductResponse)
async def reactivate_product(
    product_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    audit_ctx: AuditContext = Depends(get_audit_context),
) -> Product:
    _ensure_write(user)
    service = ProductService(db)
    product = await service.get_by_id(product_id, user.organization_id)
    updated = await service.reactivate(product=product, audit_ctx=audit_ctx)
    await db.commit()
    return updated
