import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_audit_context, get_current_active_user
from app.core.exceptions import AppError
from app.core.permissions import Permission
from app.models.station_supplier_rule import StationSupplierRule
from app.schemas.master_data import (
    CloseValidityRequest,
    DeactivateRequest,
    EffectiveRuleResponse,
    SupplierRuleCreate,
    SupplierRuleListResponse,
    SupplierRuleResponse,
    SupplierRuleUpdate,
)
from app.services.audit_service import AuditContext
from app.services.auth_service import AuthService, AuthenticatedUser
from app.services.supplier_rule_service import SupplierRuleService

router = APIRouter(prefix="/station-supplier-rules", tags=["supplier-rules"])


def _ensure_read(user: AuthenticatedUser) -> None:
    if Permission.SUPPLIER_RULES_READ.value not in user.permissions:
        raise AppError(
            "Você não possui permissão para executar esta ação.",
            status_code=403,
            code="FORBIDDEN",
        )


def _ensure_write(user: AuthenticatedUser) -> None:
    if Permission.SUPPLIER_RULES_WRITE.value not in user.permissions:
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
        "Informe o posto para filtrar as regras de fornecimento.",
        status_code=400,
        code="VALIDATION_ERROR",
    )


@router.get("/effective", response_model=EffectiveRuleResponse)
async def get_effective_rule(
    station_id: uuid.UUID,
    distributor_id: uuid.UUID,
    product_id: uuid.UUID,
    reference_date: date | None = None,
    distribution_base_id: uuid.UUID | None = None,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> EffectiveRuleResponse:
    _ensure_read(user)
    auth = AuthService(db)
    await auth.ensure_station_access(user, station_id)
    service = SupplierRuleService(db)
    result = await service.resolve_effective_rule(
        organization_id=user.organization_id,
        station_id=station_id,
        distributor_id=distributor_id,
        product_id=product_id,
        reference_date=reference_date,
        distribution_base_id=distribution_base_id,
    )
    return EffectiveRuleResponse(
        allowed=result.allowed,
        minimum_volume_liters=result.minimum_volume_liters,
        rule_source=result.rule_source,
        rule_id=result.rule_id,
        distribution_base_id=result.distribution_base_id,
        valid_from=result.valid_from,
        valid_until=result.valid_until,
        reason=result.reason,
    )


@router.get("", response_model=SupplierRuleListResponse)
async def list_supplier_rules(
    station_id: uuid.UUID | None = None,
    distributor_id: uuid.UUID | None = None,
    product_id: uuid.UUID | None = None,
    allowed: bool | None = None,
    valid_on: date | None = None,
    active: bool | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> SupplierRuleListResponse:
    _ensure_read(user)
    auth = AuthService(db)
    resolved_station_id = await _resolve_station_id(auth, user, station_id)
    service = SupplierRuleService(db)
    items, total = await service.list_rules(
        organization_id=user.organization_id,
        station_id=resolved_station_id,
        distributor_id=distributor_id,
        product_id=product_id,
        allowed=allowed,
        valid_on=valid_on,
        active=active,
        page=page,
        page_size=page_size,
    )
    return SupplierRuleListResponse(
        items=[SupplierRuleResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{rule_id}", response_model=SupplierRuleResponse)
async def get_supplier_rule(
    rule_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> StationSupplierRule:
    _ensure_read(user)
    auth = AuthService(db)
    service = SupplierRuleService(db)
    rule = await service.get_by_id(rule_id, user.organization_id)
    await auth.ensure_station_access(user, rule.station_id)
    return rule


@router.post("", response_model=SupplierRuleResponse, status_code=201)
async def create_supplier_rule(
    payload: SupplierRuleCreate,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    audit_ctx: AuditContext = Depends(get_audit_context),
) -> StationSupplierRule:
    _ensure_write(user)
    auth = AuthService(db)
    await auth.ensure_station_access(user, payload.station_id)
    service = SupplierRuleService(db)
    rule = await service.create(
        organization_id=user.organization_id,
        data=payload.model_dump(),
        created_by=user.id,
        audit_ctx=audit_ctx,
    )
    await db.commit()
    return rule


@router.patch("/{rule_id}", response_model=SupplierRuleResponse)
async def update_supplier_rule(
    rule_id: uuid.UUID,
    payload: SupplierRuleUpdate,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    audit_ctx: AuditContext = Depends(get_audit_context),
) -> StationSupplierRule:
    _ensure_write(user)
    auth = AuthService(db)
    service = SupplierRuleService(db)
    rule = await service.get_by_id(rule_id, user.organization_id)
    await auth.ensure_station_access(user, rule.station_id)
    if payload.station_id is not None:
        await auth.ensure_station_access(user, payload.station_id)
    updated = await service.update(
        rule=rule,
        data={k: v for k, v in payload.model_dump().items() if v is not None},
        audit_ctx=audit_ctx,
    )
    await db.commit()
    return updated


@router.post("/{rule_id}/deactivate", response_model=SupplierRuleResponse)
async def deactivate_supplier_rule(
    rule_id: uuid.UUID,
    payload: DeactivateRequest,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    audit_ctx: AuditContext = Depends(get_audit_context),
) -> StationSupplierRule:
    _ensure_write(user)
    auth = AuthService(db)
    service = SupplierRuleService(db)
    rule = await service.get_by_id(rule_id, user.organization_id)
    await auth.ensure_station_access(user, rule.station_id)
    updated = await service.deactivate(rule=rule, reason=payload.reason, audit_ctx=audit_ctx)
    await db.commit()
    return updated


@router.post("/{rule_id}/reactivate", response_model=SupplierRuleResponse)
async def reactivate_supplier_rule(
    rule_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    audit_ctx: AuditContext = Depends(get_audit_context),
) -> StationSupplierRule:
    _ensure_write(user)
    auth = AuthService(db)
    service = SupplierRuleService(db)
    rule = await service.get_by_id(rule_id, user.organization_id)
    await auth.ensure_station_access(user, rule.station_id)
    updated = await service.reactivate(rule=rule, audit_ctx=audit_ctx)
    await db.commit()
    return updated


@router.post("/{rule_id}/close-validity", response_model=SupplierRuleResponse)
async def close_supplier_rule_validity(
    rule_id: uuid.UUID,
    payload: CloseValidityRequest,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    audit_ctx: AuditContext = Depends(get_audit_context),
) -> StationSupplierRule:
    _ensure_write(user)
    auth = AuthService(db)
    service = SupplierRuleService(db)
    rule = await service.get_by_id(rule_id, user.organization_id)
    await auth.ensure_station_access(user, rule.station_id)
    updated = await service.close_validity(
        rule=rule,
        valid_until=payload.valid_until,
        reason=payload.reason,
        audit_ctx=audit_ctx,
    )
    await db.commit()
    return updated
