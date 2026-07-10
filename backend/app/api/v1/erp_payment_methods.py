from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.core.exceptions import AppError
from app.core.fuel_sales_enums import PaymentMethodGroup
from app.core.permissions import Permission
from app.models.fuel_sales import ErpPaymentMethod
from app.services.auth_service import AuthService, AuthenticatedUser

router = APIRouter(prefix="/erp-payment-methods", tags=["erp-payment-methods"])


class ErpPaymentMethodResponse(BaseModel):
    id: uuid.UUID
    station_id: uuid.UUID | None
    source_payment_method_id: str
    source_code: str | None
    source_name: str
    normalized_group: str
    mapping_status: str
    source_active: bool | None


class ErpPaymentMethodMapRequest(BaseModel):
    normalized_group: PaymentMethodGroup


class ErpPaymentMethodBulkMapItem(BaseModel):
    id: uuid.UUID
    normalized_group: PaymentMethodGroup


class ErpPaymentMethodBulkMapRequest(BaseModel):
    items: list[ErpPaymentMethodBulkMapItem] = Field(default_factory=list)


def _ensure(user: AuthenticatedUser, permission: Permission) -> None:
    if permission.value not in user.permissions:
        raise AppError("Você não possui permissão para executar esta ação.", status_code=403, code="FORBIDDEN")


@router.get("", response_model=list[ErpPaymentMethodResponse])
async def list_payment_methods(
    station_id: uuid.UUID | None = Query(default=None),
    mapping_status: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
) -> list[ErpPaymentMethodResponse]:
    _ensure(user, Permission.ERP_PAYMENT_METHODS_READ)
    auth = AuthService(db)
    query = select(ErpPaymentMethod).where(ErpPaymentMethod.organization_id == user.organization_id)
    if station_id is not None:
        await auth.ensure_station_access(user, station_id)
        query = query.where(ErpPaymentMethod.station_id == station_id)
    elif not user.has_all_stations_access:
        allowed = await auth.allowed_stations(user)
        query = query.where(ErpPaymentMethod.station_id.in_([s.id for s in allowed]))
    if mapping_status:
        query = query.where(ErpPaymentMethod.mapping_status == mapping_status)
    result = await db.execute(query.order_by(ErpPaymentMethod.source_name))
    return [
        ErpPaymentMethodResponse(
            id=row.id,
            station_id=row.station_id,
            source_payment_method_id=row.source_payment_method_id,
            source_code=row.source_code,
            source_name=row.source_name,
            normalized_group=row.normalized_group,
            mapping_status=row.mapping_status,
            source_active=row.source_active,
        )
        for row in result.scalars().all()
    ]


@router.patch("/{payment_method_id}/mapping", response_model=ErpPaymentMethodResponse)
async def map_payment_method(
    payment_method_id: uuid.UUID,
    payload: ErpPaymentMethodMapRequest,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
) -> ErpPaymentMethodResponse:
    _ensure(user, Permission.ERP_PAYMENT_METHODS_MAP)
    auth = AuthService(db)
    entity = await db.get(ErpPaymentMethod, payment_method_id)
    if entity is None or entity.organization_id != user.organization_id:
        raise AppError("Forma de pagamento não encontrada.", status_code=404, code="NOT_FOUND")
    if entity.station_id is not None:
        await auth.ensure_station_access(user, entity.station_id)
    entity.normalized_group = payload.normalized_group.value
    entity.mapping_status = "MAPPED"
    await db.flush()
    return ErpPaymentMethodResponse(
        id=entity.id,
        station_id=entity.station_id,
        source_payment_method_id=entity.source_payment_method_id,
        source_code=entity.source_code,
        source_name=entity.source_name,
        normalized_group=entity.normalized_group,
        mapping_status=entity.mapping_status,
        source_active=entity.source_active,
    )


@router.post("/bulk-map")
async def bulk_map_payment_methods(
    payload: ErpPaymentMethodBulkMapRequest,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
) -> dict:
    _ensure(user, Permission.ERP_PAYMENT_METHODS_MAP)
    auth = AuthService(db)
    updated = 0
    for item in payload.items:
        entity = await db.get(ErpPaymentMethod, item.id)
        if entity is None or entity.organization_id != user.organization_id:
            continue
        if entity.station_id is not None:
            await auth.ensure_station_access(user, entity.station_id)
        entity.normalized_group = item.normalized_group.value
        entity.mapping_status = "MAPPED"
        updated += 1
    await db.flush()
    return {"updated": updated}
