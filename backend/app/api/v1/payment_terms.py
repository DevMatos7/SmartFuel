import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_audit_context, get_current_active_user
from app.core.exceptions import AppError
from app.core.permissions import Permission
from app.models.payment_term import PaymentTerm
from app.schemas.master_data import (
    DeactivateRequest,
    PaymentTermCreate,
    PaymentTermListResponse,
    PaymentTermResponse,
    PaymentTermUpdate,
)
from app.services.audit_service import AuditContext
from app.services.auth_service import AuthenticatedUser
from app.services.payment_term_service import PaymentTermService

router = APIRouter(prefix="/payment-terms", tags=["payment-terms"])


def _ensure_read(user: AuthenticatedUser) -> None:
    if Permission.PAYMENT_TERMS_READ.value not in user.permissions:
        raise AppError(
            "Você não possui permissão para executar esta ação.",
            status_code=403,
            code="FORBIDDEN",
        )


def _ensure_write(user: AuthenticatedUser) -> None:
    if Permission.PAYMENT_TERMS_WRITE.value not in user.permissions:
        raise AppError(
            "Você não possui permissão para executar esta ação.",
            status_code=403,
            code="FORBIDDEN",
        )


@router.get("", response_model=PaymentTermListResponse)
async def list_payment_terms(
    payment_type: str | None = None,
    active: bool | None = None,
    search: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> PaymentTermListResponse:
    _ensure_read(user)
    service = PaymentTermService(db)
    items, total = await service.list_payment_terms(
        organization_id=user.organization_id,
        payment_type=payment_type,
        active=active,
        search=search,
        page=page,
        page_size=page_size,
    )
    return PaymentTermListResponse(
        items=[PaymentTermResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{term_id}", response_model=PaymentTermResponse)
async def get_payment_term(
    term_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> PaymentTerm:
    _ensure_read(user)
    service = PaymentTermService(db)
    return await service.get_by_id(term_id, user.organization_id)


@router.post("", response_model=PaymentTermResponse, status_code=201)
async def create_payment_term(
    payload: PaymentTermCreate,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    audit_ctx: AuditContext = Depends(get_audit_context),
) -> PaymentTerm:
    _ensure_write(user)
    service = PaymentTermService(db)
    term = await service.create(
        organization_id=user.organization_id,
        data=payload.model_dump(),
        audit_ctx=audit_ctx,
    )
    await db.commit()
    return term


@router.patch("/{term_id}", response_model=PaymentTermResponse)
async def update_payment_term(
    term_id: uuid.UUID,
    payload: PaymentTermUpdate,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    audit_ctx: AuditContext = Depends(get_audit_context),
) -> PaymentTerm:
    _ensure_write(user)
    service = PaymentTermService(db)
    term = await service.get_by_id(term_id, user.organization_id)
    updated = await service.update(
        term=term,
        data={k: v for k, v in payload.model_dump().items() if v is not None},
        audit_ctx=audit_ctx,
    )
    await db.commit()
    return updated


@router.post("/{term_id}/deactivate", response_model=PaymentTermResponse)
async def deactivate_payment_term(
    term_id: uuid.UUID,
    payload: DeactivateRequest,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    audit_ctx: AuditContext = Depends(get_audit_context),
) -> PaymentTerm:
    _ensure_write(user)
    service = PaymentTermService(db)
    term = await service.get_by_id(term_id, user.organization_id)
    updated = await service.deactivate(term=term, reason=payload.reason, audit_ctx=audit_ctx)
    await db.commit()
    return updated


@router.post("/{term_id}/reactivate", response_model=PaymentTermResponse)
async def reactivate_payment_term(
    term_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    audit_ctx: AuditContext = Depends(get_audit_context),
) -> PaymentTerm:
    _ensure_write(user)
    service = PaymentTermService(db)
    term = await service.get_by_id(term_id, user.organization_id)
    updated = await service.reactivate(term=term, audit_ctx=audit_ctx)
    await db.commit()
    return updated
