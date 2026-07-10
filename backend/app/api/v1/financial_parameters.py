from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_audit_context, get_current_active_user
from app.core.exceptions import AppError
from app.core.permissions import Permission
from app.schemas.financial_parameters import (
    FinancialParameterCloseValidity,
    FinancialParameterCreate,
    FinancialParameterListResponse,
    FinancialParameterResponse,
)
from app.services.audit_service import AuditContext
from app.services.auth_service import AuthenticatedUser
from app.services.financial_parameter_service import FinancialParameterService

router = APIRouter(prefix="/financial-parameters", tags=["financial-parameters"])


def _ensure(user: AuthenticatedUser, permission: Permission) -> None:
    if permission.value not in user.permissions:
        raise AppError(
            "Você não possui permissão para executar esta ação.",
            status_code=403,
            code="FORBIDDEN",
        )


@router.get("", response_model=FinancialParameterListResponse)
async def list_financial_parameters(
    active: bool | None = Query(default=None),
    valid_on: datetime | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> FinancialParameterListResponse:
    _ensure(user, Permission.FINANCIAL_PARAMETERS_READ)
    service = FinancialParameterService(db)
    items, total = await service.list_parameters(
        organization_id=user.organization_id,
        active=active,
        valid_on=valid_on,
        page=page,
        page_size=page_size,
    )
    return FinancialParameterListResponse(
        items=[FinancialParameterResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{parameter_id}", response_model=FinancialParameterResponse)
async def get_financial_parameter(
    parameter_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> FinancialParameterResponse:
    _ensure(user, Permission.FINANCIAL_PARAMETERS_READ)
    service = FinancialParameterService(db)
    row = await service.get_by_id(parameter_id, user.organization_id)
    return FinancialParameterResponse.model_validate(row)


@router.post("", response_model=FinancialParameterResponse, status_code=201)
async def create_financial_parameter(
    payload: FinancialParameterCreate,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    audit: AuditContext = Depends(get_audit_context),
) -> FinancialParameterResponse:
    _ensure(user, Permission.FINANCIAL_PARAMETERS_WRITE)
    service = FinancialParameterService(db)
    row = await service.create(
        organization_id=user.organization_id,
        annual_effective_rate=payload.annual_effective_rate,
        day_count_basis=payload.day_count_basis,
        valid_from=payload.valid_from,
        valid_until=payload.valid_until,
        notes=payload.notes,
        actor_id=user.id,
        audit=audit,
    )
    await db.commit()
    return FinancialParameterResponse.model_validate(row)


@router.post("/{parameter_id}/close-validity", response_model=FinancialParameterResponse)
async def close_financial_parameter_validity(
    parameter_id: uuid.UUID,
    payload: FinancialParameterCloseValidity,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    audit: AuditContext = Depends(get_audit_context),
) -> FinancialParameterResponse:
    _ensure(user, Permission.FINANCIAL_PARAMETERS_WRITE)
    service = FinancialParameterService(db)
    row = await service.close_validity(
        parameter_id=parameter_id,
        organization_id=user.organization_id,
        valid_until=payload.valid_until,
        reason=payload.reason,
        actor_id=user.id,
        audit=audit,
    )
    await db.commit()
    return FinancialParameterResponse.model_validate(row)


@router.post("/{parameter_id}/deactivate", response_model=FinancialParameterResponse)
async def deactivate_financial_parameter(
    parameter_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    audit: AuditContext = Depends(get_audit_context),
) -> FinancialParameterResponse:
    _ensure(user, Permission.FINANCIAL_PARAMETERS_DEACTIVATE)
    service = FinancialParameterService(db)
    row = await service.deactivate(
        parameter_id=parameter_id,
        organization_id=user.organization_id,
        actor_id=user.id,
        audit=audit,
    )
    await db.commit()
    return FinancialParameterResponse.model_validate(row)
