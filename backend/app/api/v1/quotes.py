from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_audit_context, get_current_active_user
from app.core.exceptions import AppError
from app.core.permissions import Permission
from app.schemas.quotes import (
    CancelQuoteRequest,
    DeactivateEvidenceRequest,
    DuplicateQuoteRequest,
    ExpirationRunResponse,
    ItemPrefillResponse,
    QuoteCreate,
    QuoteEvidenceResponse,
    QuoteHistoryListResponse,
    QuoteItemCreate,
    QuoteItemResponse,
    QuoteItemUpdate,
    QuoteListResponse,
    QuoteResponse,
    QuoteUpdate,
    ReviseQuoteRequest,
    VersionedAction,
)
from app.services.audit_service import AuditContext
from app.services.auth_service import AuthService, AuthenticatedUser
from app.services.quote_evidence_service import QuoteEvidenceService
from app.services.quote_history_service import QuoteHistoryService
from app.services.quote_service import QuoteService
from app.utils.quote_pdf import build_quote_pdf

router = APIRouter(prefix="/quotes", tags=["quotes"])


def _ensure(user: AuthenticatedUser, permission: Permission) -> None:
    if permission.value not in user.permissions:
        raise AppError(
            "Você não possui permissão para executar esta ação.",
            status_code=403,
            code="FORBIDDEN",
        )


def _to_item_response(item, quote, service: QuoteService) -> QuoteItemResponse:
    base = QuoteItemResponse.model_validate(item)
    return base.model_copy(
        update={
            "item_effective_status": service.compute_item_effective_status(item, quote),
            "effective_valid_until": service._item_effective_valid_until(item, quote),
        }
    )


def _to_quote_response(quote, service: QuoteService, warnings: list[str] | None = None) -> QuoteResponse:
    effective = service.compute_effective_status(quote)
    return QuoteResponse(
        id=quote.id,
        organization_id=quote.organization_id,
        station_id=quote.station_id,
        distributor_id=quote.distributor_id,
        distribution_base_id=quote.distribution_base_id,
        quote_number=quote.quote_number,
        quoted_at=quote.quoted_at,
        valid_until=quote.valid_until,
        source_channel=quote.source_channel,
        entry_method=quote.entry_method,
        seller_name=quote.seller_name,
        seller_contact=quote.seller_contact,
        external_reference=quote.external_reference,
        source_description=quote.source_description,
        notes=quote.notes,
        status=quote.status,
        effective_status=effective,
        version=quote.version,
        replaces_quote_id=quote.replaces_quote_id,
        duplicated_from_quote_id=quote.duplicated_from_quote_id,
        activated_at=quote.activated_at,
        activated_by=quote.activated_by,
        cancelled_at=quote.cancelled_at,
        cancelled_by=quote.cancelled_by,
        cancellation_reason=quote.cancellation_reason,
        superseded_at=quote.superseded_at,
        superseded_by_quote_id=quote.superseded_by_quote_id,
        created_by=quote.created_by,
        created_at=quote.created_at,
        updated_at=quote.updated_at,
        items=[_to_item_response(i, quote, service) for i in quote.items],
        evidences=[QuoteEvidenceResponse.model_validate(e) for e in quote.evidences if e.active],
        warnings=warnings or [],
    )


async def _station_scope(
    auth: AuthService,
    user: AuthenticatedUser,
    station_id: uuid.UUID | None,
) -> tuple[uuid.UUID | None, list[uuid.UUID] | None]:
    if station_id is not None:
        await auth.ensure_station_access(user, station_id)
        return station_id, None
    if user.has_all_stations_access:
        return None, None
    allowed = await auth.allowed_stations(user)
    return None, [s.id for s in allowed]


@router.get("", response_model=QuoteListResponse)
async def list_quotes(
    station_id: uuid.UUID | None = None,
    distributor_id: uuid.UUID | None = None,
    product_id: uuid.UUID | None = None,
    status: str | None = None,
    source_channel: str | None = None,
    quoted_from: datetime | None = None,
    quoted_to: datetime | None = None,
    valid_from: datetime | None = None,
    valid_to: datetime | None = None,
    created_by: uuid.UUID | None = None,
    search: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort: str = "-quoted_at",
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> QuoteListResponse:
    _ensure(user, Permission.QUOTES_READ)
    auth = AuthService(db)
    scoped_station, station_ids = await _station_scope(auth, user, station_id)
    service = QuoteService(db)
    quotes, total, summary = await service.list_quotes(
        organization_id=user.organization_id,
        station_ids=station_ids,
        station_id=scoped_station,
        distributor_id=distributor_id,
        product_id=product_id,
        status=status,
        source_channel=source_channel,
        quoted_from=quoted_from,
        quoted_to=quoted_to,
        valid_from=valid_from,
        valid_to=valid_to,
        created_by=created_by,
        search=search,
        page=page,
        page_size=page_size,
        sort=sort,
    )
    items = [
        {
            "id": q.id,
            "quote_number": q.quote_number,
            "station_id": q.station_id,
            "distributor_id": q.distributor_id,
            "quoted_at": q.quoted_at,
            "valid_until": q.valid_until,
            "source_channel": q.source_channel,
            "status": q.status,
            "effective_status": service.compute_effective_status(q),
            "version": q.version,
            "item_count": len(q.items),
        }
        for q in quotes
    ]
    return QuoteListResponse(items=items, total=total, page=page, page_size=page_size, summary=summary)


@router.post("", response_model=QuoteResponse, status_code=201)
async def create_quote(
    payload: QuoteCreate,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    audit_ctx: AuditContext = Depends(get_audit_context),
) -> QuoteResponse:
    _ensure(user, Permission.QUOTES_WRITE)
    auth = AuthService(db)
    await auth.ensure_station_access(user, payload.station_id)
    service = QuoteService(db)
    quote = await service.create(
        organization_id=user.organization_id,
        user_id=user.id,
        data=payload.model_dump(),
        audit_ctx=audit_ctx,
        request_id=uuid.UUID(audit_ctx.request_id) if audit_ctx.request_id else None,
    )
    await db.commit()
    quote = await service.get_quote(quote.id, user.organization_id)
    return _to_quote_response(quote, service)


@router.get("/item-prefill", response_model=ItemPrefillResponse)
async def get_item_prefill(
    station_id: uuid.UUID,
    distributor_id: uuid.UUID,
    product_id: uuid.UUID,
    distribution_base_id: uuid.UUID | None = None,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> ItemPrefillResponse:
    _ensure(user, Permission.QUOTES_WRITE)
    auth = AuthService(db)
    await auth.ensure_station_access(user, station_id)
    service = QuoteService(db)
    data = await service.get_item_prefill(
        organization_id=user.organization_id,
        station_id=station_id,
        distributor_id=distributor_id,
        product_id=product_id,
        distribution_base_id=distribution_base_id,
    )
    return ItemPrefillResponse(**data)


@router.get("/{quote_id}", response_model=QuoteResponse)
async def get_quote(
    quote_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> QuoteResponse:
    _ensure(user, Permission.QUOTES_READ)
    service = QuoteService(db)
    quote = await service.get_quote(quote_id, user.organization_id)
    auth = AuthService(db)
    await auth.ensure_station_access(user, quote.station_id)
    return _to_quote_response(quote, service)


@router.patch("/{quote_id}", response_model=QuoteResponse)
async def update_quote(
    quote_id: uuid.UUID,
    payload: QuoteUpdate,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    audit_ctx: AuditContext = Depends(get_audit_context),
) -> QuoteResponse:
    _ensure(user, Permission.QUOTES_WRITE)
    service = QuoteService(db)
    quote = await service.get_quote(quote_id, user.organization_id)
    auth = AuthService(db)
    await auth.ensure_station_access(user, quote.station_id)
    quote = await service.update(
        quote_id=quote_id,
        organization_id=user.organization_id,
        user_id=user.id,
        data=payload.model_dump(exclude={"expected_version"}, exclude_none=True),
        expected_version=payload.expected_version,
        audit_ctx=audit_ctx,
        request_id=uuid.UUID(audit_ctx.request_id) if audit_ctx.request_id else None,
    )
    await db.commit()
    quote = await service.get_quote(quote.id, user.organization_id)
    return _to_quote_response(quote, service)


@router.post("/{quote_id}/items", response_model=QuoteItemResponse, status_code=201)
async def add_quote_item(
    quote_id: uuid.UUID,
    payload: QuoteItemCreate,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    audit_ctx: AuditContext = Depends(get_audit_context),
) -> QuoteItemResponse:
    _ensure(user, Permission.QUOTE_ITEMS_WRITE)
    service = QuoteService(db)
    quote = await service.get_quote(quote_id, user.organization_id)
    auth = AuthService(db)
    await auth.ensure_station_access(user, quote.station_id)
    item = await service.add_item(
        quote_id=quote_id,
        organization_id=user.organization_id,
        user_id=user.id,
        data=payload.model_dump(exclude={"expected_version"}),
        expected_version=payload.expected_version,
        audit_ctx=audit_ctx,
        request_id=uuid.UUID(audit_ctx.request_id) if audit_ctx.request_id else None,
    )
    await db.commit()
    return QuoteItemResponse.model_validate(item)


@router.patch("/{quote_id}/items/{item_id}", response_model=QuoteItemResponse)
async def update_quote_item(
    quote_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: QuoteItemUpdate,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    audit_ctx: AuditContext = Depends(get_audit_context),
) -> QuoteItemResponse:
    _ensure(user, Permission.QUOTE_ITEMS_WRITE)
    service = QuoteService(db)
    quote = await service.get_quote(quote_id, user.organization_id)
    auth = AuthService(db)
    await auth.ensure_station_access(user, quote.station_id)
    item = await service.update_item(
        quote_id=quote_id,
        item_id=item_id,
        organization_id=user.organization_id,
        user_id=user.id,
        data=payload.model_dump(exclude={"expected_version"}, exclude_none=True),
        expected_version=payload.expected_version,
        audit_ctx=audit_ctx,
        request_id=uuid.UUID(audit_ctx.request_id) if audit_ctx.request_id else None,
    )
    await db.commit()
    return QuoteItemResponse.model_validate(item)


@router.delete("/{quote_id}/items/{item_id}", status_code=204)
async def delete_quote_item(
    quote_id: uuid.UUID,
    item_id: uuid.UUID,
    expected_version: int = Query(...),
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    audit_ctx: AuditContext = Depends(get_audit_context),
) -> Response:
    _ensure(user, Permission.QUOTE_ITEMS_WRITE)
    service = QuoteService(db)
    quote = await service.get_quote(quote_id, user.organization_id)
    auth = AuthService(db)
    await auth.ensure_station_access(user, quote.station_id)
    await service.remove_item(
        quote_id=quote_id,
        item_id=item_id,
        organization_id=user.organization_id,
        user_id=user.id,
        expected_version=expected_version,
        audit_ctx=audit_ctx,
        request_id=uuid.UUID(audit_ctx.request_id) if audit_ctx.request_id else None,
    )
    await db.commit()
    return Response(status_code=204)


@router.post("/{quote_id}/evidences", response_model=QuoteResponse)
async def upload_evidence(
    quote_id: uuid.UUID,
    expected_version: int = Form(...),
    category: str = Form(...),
    is_supplemental: bool = Form(False),
    file: UploadFile = File(...),
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    audit_ctx: AuditContext = Depends(get_audit_context),
) -> QuoteResponse:
    _ensure(user, Permission.QUOTE_EVIDENCES_WRITE)
    service = QuoteService(db)
    quote = await service.get_quote(quote_id, user.organization_id)
    auth = AuthService(db)
    await auth.ensure_station_access(user, quote.station_id)
    content = await file.read()
    evidence_service = QuoteEvidenceService(db)
    await evidence_service.upload(
        quote_id=quote_id,
        organization_id=user.organization_id,
        user_id=user.id,
        file_name=file.filename or "evidence.bin",
        content_type=file.content_type or "application/octet-stream",
        content=content,
        category=category,
        is_supplemental=is_supplemental,
        expected_version=expected_version,
        audit_ctx=audit_ctx,
        request_id=uuid.UUID(audit_ctx.request_id) if audit_ctx.request_id else None,
    )
    await db.commit()
    quote = await service.get_quote(quote_id, user.organization_id)
    return _to_quote_response(quote, service)


@router.get("/{quote_id}/evidences/{evidence_id}")
async def download_evidence(
    quote_id: uuid.UUID,
    evidence_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    _ensure(user, Permission.QUOTE_EVIDENCES_READ)
    service = QuoteService(db)
    quote = await service.get_quote(quote_id, user.organization_id)
    auth = AuthService(db)
    await auth.ensure_station_access(user, quote.station_id)
    evidence_service = QuoteEvidenceService(db)
    content, content_type, file_name = await evidence_service.get_download(
        quote_id=quote_id,
        evidence_id=evidence_id,
        organization_id=user.organization_id,
    )
    return StreamingResponse(
        iter([content]),
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
    )


@router.delete("/{quote_id}/evidences/{evidence_id}", status_code=204)
async def delete_evidence(
    quote_id: uuid.UUID,
    evidence_id: uuid.UUID,
    expected_version: int = Query(...),
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    audit_ctx: AuditContext = Depends(get_audit_context),
) -> Response:
    _ensure(user, Permission.QUOTE_EVIDENCES_WRITE)
    service = QuoteService(db)
    quote = await service.get_quote(quote_id, user.organization_id)
    auth = AuthService(db)
    await auth.ensure_station_access(user, quote.station_id)
    evidence_service = QuoteEvidenceService(db)
    await evidence_service.remove_from_draft(
        quote_id=quote_id,
        evidence_id=evidence_id,
        organization_id=user.organization_id,
        user_id=user.id,
        expected_version=expected_version,
        audit_ctx=audit_ctx,
        request_id=uuid.UUID(audit_ctx.request_id) if audit_ctx.request_id else None,
    )
    await db.commit()
    return Response(status_code=204)


@router.post("/{quote_id}/evidences/{evidence_id}/deactivate")
async def deactivate_evidence(
    quote_id: uuid.UUID,
    evidence_id: uuid.UUID,
    payload: DeactivateEvidenceRequest,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    audit_ctx: AuditContext = Depends(get_audit_context),
) -> QuoteResponse:
    _ensure(user, Permission.QUOTE_EVIDENCES_DEACTIVATE)
    service = QuoteService(db)
    quote = await service.get_quote(quote_id, user.organization_id)
    auth = AuthService(db)
    await auth.ensure_station_access(user, quote.station_id)
    evidence_service = QuoteEvidenceService(db)
    await evidence_service.deactivate(
        quote_id=quote_id,
        evidence_id=evidence_id,
        organization_id=user.organization_id,
        user_id=user.id,
        reason=payload.reason,
        audit_ctx=audit_ctx,
        request_id=uuid.UUID(audit_ctx.request_id) if audit_ctx.request_id else None,
    )
    await db.commit()
    quote = await service.get_quote(quote_id, user.organization_id)
    return _to_quote_response(quote, service)


@router.post("/{quote_id}/activate", response_model=QuoteResponse)
async def activate_quote(
    quote_id: uuid.UUID,
    payload: VersionedAction,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    audit_ctx: AuditContext = Depends(get_audit_context),
) -> QuoteResponse:
    _ensure(user, Permission.QUOTES_ACTIVATE)
    service = QuoteService(db)
    quote = await service.get_quote(quote_id, user.organization_id)
    auth = AuthService(db)
    await auth.ensure_station_access(user, quote.station_id)
    quote = await service.activate(
        quote_id=quote_id,
        organization_id=user.organization_id,
        user_id=user.id,
        expected_version=payload.expected_version,
        audit_ctx=audit_ctx,
        request_id=uuid.UUID(audit_ctx.request_id) if audit_ctx.request_id else None,
    )
    await db.commit()
    quote = await service.get_quote(quote.id, user.organization_id)
    return _to_quote_response(quote, service)


@router.post("/{quote_id}/cancel", response_model=QuoteResponse)
async def cancel_quote(
    quote_id: uuid.UUID,
    payload: CancelQuoteRequest,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    audit_ctx: AuditContext = Depends(get_audit_context),
) -> QuoteResponse:
    _ensure(user, Permission.QUOTES_CANCEL)
    service = QuoteService(db)
    quote = await service.get_quote(quote_id, user.organization_id)
    auth = AuthService(db)
    await auth.ensure_station_access(user, quote.station_id)
    quote = await service.cancel(
        quote_id=quote_id,
        organization_id=user.organization_id,
        user_id=user.id,
        reason=payload.reason,
        expected_version=payload.expected_version,
        audit_ctx=audit_ctx,
        request_id=uuid.UUID(audit_ctx.request_id) if audit_ctx.request_id else None,
    )
    await db.commit()
    quote = await service.get_quote(quote.id, user.organization_id)
    return _to_quote_response(quote, service)


@router.post("/{quote_id}/revise", response_model=QuoteResponse, status_code=201)
async def revise_quote(
    quote_id: uuid.UUID,
    payload: ReviseQuoteRequest,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    audit_ctx: AuditContext = Depends(get_audit_context),
) -> QuoteResponse:
    _ensure(user, Permission.QUOTES_REVISE)
    service = QuoteService(db)
    source = await service.get_quote(quote_id, user.organization_id)
    auth = AuthService(db)
    await auth.ensure_station_access(user, source.station_id)
    draft = await service.revise(
        quote_id=quote_id,
        organization_id=user.organization_id,
        user_id=user.id,
        reason=payload.reason,
        audit_ctx=audit_ctx,
        request_id=uuid.UUID(audit_ctx.request_id) if audit_ctx.request_id else None,
    )
    await db.commit()
    draft = await service.get_quote(draft.id, user.organization_id)
    return _to_quote_response(draft, service)


@router.post("/{quote_id}/duplicate", response_model=QuoteResponse, status_code=201)
async def duplicate_quote(
    quote_id: uuid.UUID,
    payload: DuplicateQuoteRequest,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    audit_ctx: AuditContext = Depends(get_audit_context),
) -> QuoteResponse:
    _ensure(user, Permission.QUOTES_DUPLICATE)
    service = QuoteService(db)
    source = await service.get_quote(quote_id, user.organization_id)
    auth = AuthService(db)
    await auth.ensure_station_access(user, source.station_id)
    await auth.ensure_station_access(user, payload.target_station_id)
    draft = await service.duplicate(
        quote_id=quote_id,
        organization_id=user.organization_id,
        user_id=user.id,
        target_station_id=payload.target_station_id,
        quoted_at=payload.quoted_at,
        valid_until=payload.valid_until,
        copy_evidences=payload.copy_evidences,
        notes=payload.notes,
        audit_ctx=audit_ctx,
        request_id=uuid.UUID(audit_ctx.request_id) if audit_ctx.request_id else None,
    )
    await db.commit()
    draft = await service.get_quote(draft.id, user.organization_id)
    return _to_quote_response(draft, service)


@router.get("/{quote_id}/history")
async def quote_history(
    quote_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    _ensure(user, Permission.QUOTE_HISTORY_READ)
    service = QuoteService(db)
    quote = await service.get_quote(quote_id, user.organization_id)
    auth = AuthService(db)
    await auth.ensure_station_access(user, quote.station_id)
    history_service = QuoteHistoryService(db)
    entries, total = await history_service.list_history(quote_id=quote_id, page=page, page_size=page_size)
    return {
        "items": [
            {
                "id": str(e.id),
                "action": e.action,
                "version": e.version,
                "reason": e.reason,
                "changed_fields": e.changed_fields,
                "metadata": e.metadata_,
                "user_id": str(e.user_id) if e.user_id else None,
                "request_id": str(e.request_id) if e.request_id else None,
                "created_at": e.created_at.isoformat(),
                "quote_item_id": str(e.quote_item_id) if e.quote_item_id else None,
                "quote_evidence_id": str(e.quote_evidence_id) if e.quote_evidence_id else None,
            }
            for e in entries
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{quote_id}/export/pdf")
async def export_quote_pdf(
    quote_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    _ensure(user, Permission.QUOTES_READ)
    service = QuoteService(db)
    quote = await service.get_quote(quote_id, user.organization_id)
    auth = AuthService(db)
    await auth.ensure_station_access(user, quote.station_id)
    pdf_bytes = build_quote_pdf(quote, generated_by=user.email)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="cotacao-{quote.quote_number:06d}.pdf"'},
    )


@router.post("/expiration/run", response_model=ExpirationRunResponse)
async def run_expiration(
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> ExpirationRunResponse:
    _ensure(user, Permission.QUOTE_EXPIRATION_EXECUTE)
    service = QuoteService(db)
    result = await service.run_expiration(organization_id=user.organization_id)
    await db.commit()
    return ExpirationRunResponse(**result)
