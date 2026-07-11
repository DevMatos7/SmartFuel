"""APIs Sprint 13 — ingestão inteligente de cotações por IA."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, File, Form, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_audit_context, get_current_active_user
from app.core.exceptions import AppError
from app.core.permissions import Permission
from app.core.quote_ai_enums import QuoteIngestionSourceChannel
from app.services.audit_service import AuditContext
from app.services.auth_service import AuthenticatedUser
from app.services.operations_service import OperationsService
from app.services.quote_ingestion_service import QuoteIngestionPipelineService

router = APIRouter(prefix="/quote-ingestion", tags=["quote-ingestion"])
analytics_router = APIRouter(prefix="/analytics/quote-ingestion", tags=["quote-ingestion-analytics"])


def _ensure(user: AuthenticatedUser, permission: Permission) -> None:
    if permission.value not in user.permissions:
        raise AppError(
            "Você não possui permissão para executar esta ação.",
            status_code=403,
            code="FORBIDDEN",
        )


class BatchCreateBody(BaseModel):
    source_channel: str = QuoteIngestionSourceChannel.UPLOAD
    station_id: uuid.UUID | None = None
    notes: str | None = None


class TextIngestBody(BaseModel):
    text: str = Field(min_length=1)
    station_id: uuid.UUID | None = None
    source_channel: str = QuoteIngestionSourceChannel.TEXT_PASTE
    source_sender: str | None = None
    source_message_datetime: datetime | None = None
    process_now: bool = True


class ReviewSaveBody(BaseModel):
    corrections: dict[str, Any] = Field(default_factory=dict)
    review_notes: str | None = None


class ApproveBody(BaseModel):
    with_corrections: bool = False


class RejectBody(BaseModel):
    note: str | None = None


class CreateDraftBody(BaseModel):
    distributor_id: uuid.UUID | None = None
    station_id: uuid.UUID | None = None
    payment_term_id: uuid.UUID | None = None
    product_bindings: dict[str, str] | None = None
    quoted_at: datetime | None = None
    valid_until: datetime | None = None


class ProviderConfigBody(BaseModel):
    provider: str = "mock"
    model: str = "mock-extractor-v1"
    secret_ref: str | None = None
    prompt_version: str = "v1"
    schema_version: str = "v1"
    enabled: bool = False
    daily_cost_limit: str | None = None
    monthly_cost_limit: str | None = None
    per_document_cost_limit: str | None = None


def _svc(db: AsyncSession) -> QuoteIngestionPipelineService:
    return QuoteIngestionPipelineService(db)


@router.post("/batches")
async def create_batch(
    body: BatchCreateBody,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
    audit_ctx: AuditContext = Depends(get_audit_context),
):
    _ensure(user, Permission.QUOTE_INGESTION_UPLOAD)
    svc = _svc(db)
    # piloto: habilitar flag sob demanda apenas se admin já tiver ligado
    batch = await svc.create_batch(
        organization_id=user.organization_id,
        user_id=user.id,
        source_channel=body.source_channel,
        station_id=body.station_id,
        notes=body.notes,
        audit_ctx=audit_ctx,
    )
    await db.commit()
    return svc.serialize_batch(batch)


@router.post("/text")
async def ingest_text(
    body: TextIngestBody,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
    audit_ctx: AuditContext = Depends(get_audit_context),
):
    _ensure(user, Permission.QUOTE_INGESTION_UPLOAD)
    svc = _svc(db)
    result = await svc.ingest_text(
        organization_id=user.organization_id,
        user_id=user.id,
        text=body.text,
        station_id=body.station_id,
        source_channel=body.source_channel,
        source_sender=body.source_sender,
        source_message_datetime=body.source_message_datetime,
        process_now=body.process_now,
        audit_ctx=audit_ctx,
    )
    await db.commit()
    return {
        "batch": svc.serialize_batch(result["batch"]),
        "document": svc.serialize_document(result["document"], include_raw=True),
        "disclaimer": "Revisão humana obrigatória. Ativação automática proibida.",
    }


@router.post("/batches/{batch_id}/documents")
async def upload_document(
    batch_id: uuid.UUID,
    file: UploadFile = File(...),
    station_id: uuid.UUID | None = Form(default=None),
    source_channel: str = Form(default=QuoteIngestionSourceChannel.UPLOAD),
    process_now: bool = Form(default=True),
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
    audit_ctx: AuditContext = Depends(get_audit_context),
):
    _ensure(user, Permission.QUOTE_INGESTION_UPLOAD)
    data = await file.read()
    svc = _svc(db)
    # batch_id reservado para upload em lote futuro; cria documento no fluxo padrão
    _ = batch_id
    result = await svc.ingest_file(
        organization_id=user.organization_id,
        user_id=user.id,
        filename=file.filename or "upload.bin",
        content_type=file.content_type or "application/octet-stream",
        data=data,
        station_id=station_id,
        source_channel=source_channel,
        process_now=process_now,
        audit_ctx=audit_ctx,
    )
    await db.commit()
    return {
        "batch": svc.serialize_batch(result["batch"]),
        "document": svc.serialize_document(result["document"]),
    }


@router.get("/batches")
async def list_batches(
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.QUOTE_INGESTION_READ)
    svc = _svc(db)
    batches = await svc.list_batches(user.organization_id)
    return {"items": [svc.serialize_batch(b) for b in batches]}


@router.get("/documents")
async def list_documents(
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.QUOTE_INGESTION_READ)
    svc = _svc(db)
    docs = await svc.list_documents(user.organization_id)
    include_raw = Permission.QUOTE_INGESTION_VIEW_RAW_TEXT.value in user.permissions
    return {"items": [svc.serialize_document(d, include_raw=include_raw) for d in docs]}


@router.get("/documents/{document_id}")
async def get_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.QUOTE_INGESTION_READ)
    svc = _svc(db)
    details = await svc.document_details(document_id, user.organization_id)
    include_raw = Permission.QUOTE_INGESTION_VIEW_RAW_TEXT.value in user.permissions
    include_payload = Permission.QUOTE_INGESTION_VIEW_AI_PAYLOAD.value in user.permissions
    extraction = details["extraction"]
    return {
        "document": svc.serialize_document(details["document"], include_raw=include_raw),
        "extraction": None
        if extraction is None
        else {
            "id": str(extraction.id),
            "provider": extraction.provider,
            "model": extraction.model,
            "prompt_version": extraction.prompt_version,
            "schema_version": extraction.schema_version,
            "document_confidence": str(extraction.document_confidence)
            if extraction.document_confidence is not None
            else None,
            "warnings": extraction.warnings or [],
            "structured_output": extraction.structured_output if include_payload else None,
            "input_tokens": extraction.input_tokens,
            "output_tokens": extraction.output_tokens,
            "provider_cost": str(extraction.provider_cost) if extraction.provider_cost is not None else None,
        },
        "fields": [
            {
                "field_path": f.field_path,
                "raw_value": f.raw_value,
                "normalized_value": f.normalized_value,
                "confidence": str(f.confidence) if f.confidence is not None else None,
                "value_origin": f.value_origin,
                "evidence_text": f.evidence_text,
                "validation_status": f.validation_status,
            }
            for f in details["fields"]
        ],
        "matches": [
            {
                "entity_type": m.entity_type,
                "raw_value": m.raw_value,
                "status": m.status,
                "matched_entity_id": str(m.matched_entity_id) if m.matched_entity_id else None,
                "candidates": m.candidate_entities,
            }
            for m in details["matches"]
        ],
        "review": None
        if details["review"] is None
        else {
            "id": str(details["review"].id),
            "status": details["review"].status,
            "corrections": details["review"].corrections,
            "review_notes": details["review"].review_notes,
        },
        "draft_link": None
        if details["draft_link"] is None
        else {
            "quote_id": str(details["draft_link"].quote_id),
            "creation_status": details["draft_link"].creation_status,
        },
        "human_review_required": True,
        "auto_activation": False,
    }


@router.post("/documents/{document_id}/retry")
async def retry_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.QUOTE_INGESTION_RETRY)
    svc = _svc(db)
    doc = await svc.process_document(document_id=document_id, organization_id=user.organization_id)
    await db.commit()
    return svc.serialize_document(doc)


@router.post("/documents/{document_id}/start-review")
async def start_review(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.QUOTE_INGESTION_REVIEW)
    svc = _svc(db)
    review = await svc.start_review(
        document_id=document_id, organization_id=user.organization_id, user_id=user.id
    )
    await db.commit()
    return {"id": str(review.id), "status": review.status}


@router.put("/documents/{document_id}/review")
async def save_review(
    document_id: uuid.UUID,
    body: ReviewSaveBody,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.QUOTE_INGESTION_REVIEW)
    svc = _svc(db)
    review = await svc.save_review(
        document_id=document_id,
        organization_id=user.organization_id,
        user_id=user.id,
        corrections=body.corrections,
        review_notes=body.review_notes,
    )
    await db.commit()
    return {"id": str(review.id), "status": review.status, "corrections": review.corrections}


@router.post("/documents/{document_id}/approve")
async def approve_document(
    document_id: uuid.UUID,
    body: ApproveBody,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.QUOTE_INGESTION_APPROVE)
    svc = _svc(db)
    review = await svc.approve_review(
        document_id=document_id,
        organization_id=user.organization_id,
        user_id=user.id,
        with_corrections=body.with_corrections,
    )
    await db.commit()
    return {"id": str(review.id), "status": review.status}


@router.post("/documents/{document_id}/reject")
async def reject_document(
    document_id: uuid.UUID,
    body: RejectBody,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.QUOTE_INGESTION_APPROVE)
    svc = _svc(db)
    review = await svc.reject_review(
        document_id=document_id,
        organization_id=user.organization_id,
        user_id=user.id,
        note=body.note,
    )
    await db.commit()
    return {"id": str(review.id), "status": review.status}


@router.post("/documents/{document_id}/create-draft")
async def create_draft(
    document_id: uuid.UUID,
    body: CreateDraftBody,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
    audit_ctx: AuditContext = Depends(get_audit_context),
):
    _ensure(user, Permission.QUOTE_INGESTION_CREATE_DRAFT)
    svc = _svc(db)
    result = await svc.create_draft_from_review(
        document_id=document_id,
        organization_id=user.organization_id,
        user_id=user.id,
        audit_ctx=audit_ctx,
        distributor_id=body.distributor_id,
        station_id=body.station_id,
        product_bindings=body.product_bindings,
        payment_term_id=body.payment_term_id,
        quoted_at=body.quoted_at,
        valid_until=body.valid_until,
    )
    await db.commit()
    return {
        "quote_id": str(result["quote_id"]),
        "quote_status": result["quote_status"],
        "activated": False,
        "message": "Rascunho criado. Ativação permanece no fluxo manual da Central de Cotações.",
    }


@router.get("/provider-config")
async def get_provider_config(
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.QUOTE_INGESTION_MANAGE_PROVIDER)
    svc = _svc(db)
    cfg = await svc._provider_config(user.organization_id)
    await db.commit()
    return {
        "provider": cfg.provider,
        "model": cfg.model,
        "secret_ref": cfg.secret_ref,
        "prompt_version": cfg.prompt_version,
        "schema_version": cfg.schema_version,
        "enabled": cfg.enabled,
        "allow_training_usage": cfg.allow_training_usage,
        "daily_cost_limit": str(cfg.daily_cost_limit) if cfg.daily_cost_limit else None,
    }


@router.put("/provider-config")
async def put_provider_config(
    body: ProviderConfigBody,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.QUOTE_INGESTION_MANAGE_PROVIDER)
    svc = _svc(db)
    cfg = await svc._provider_config(user.organization_id)
    cfg.provider = body.provider
    cfg.model = body.model
    cfg.secret_ref = body.secret_ref
    cfg.prompt_version = body.prompt_version
    cfg.schema_version = body.schema_version
    cfg.enabled = body.enabled
    await db.commit()
    return {"provider": cfg.provider, "enabled": cfg.enabled, "secret_ref": cfg.secret_ref}


@router.post("/evaluations/runs")
async def run_evaluation(
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.QUOTE_INGESTION_RUN_EVALUATION)
    svc = _svc(db)
    await svc.seed_synthetic_evaluation_cases(user_id=user.id)
    run = await svc.run_evaluation(organization_id=user.organization_id, user_id=user.id)
    await db.commit()
    return {
        "id": str(run.id),
        "status": run.status,
        "case_count": run.case_count,
        "passed_count": run.passed_count,
        "failed_count": run.failed_count,
        "metrics": run.metrics,
    }


@router.post("/flags/enable-pilot")
async def enable_pilot_flag(
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
    audit_ctx: AuditContext = Depends(get_audit_context),
):
    """Ativa quote_ai_ingestion_enabled somente para a organização atual (ADMIN)."""
    _ensure(user, Permission.OPERATIONS_MANAGE_FEATURE_FLAGS)
    ops = OperationsService(db)
    flag = await ops.set_flag(
        organization_id=user.organization_id,
        flag_code="quote_ai_ingestion_enabled",
        enabled=True,
        user_id=user.id,
        audit_ctx=audit_ctx,
    )
    await db.commit()
    return {"flag_code": flag.flag_code, "enabled": flag.enabled}


@analytics_router.get("/summary")
async def analytics_summary(
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.QUOTE_INGESTION_READ)
    svc = _svc(db)
    docs = await svc.list_documents(user.organization_id, limit=200)
    by_status: dict[str, int] = {}
    for d in docs:
        by_status[d.status] = by_status.get(d.status, 0) + 1
    return {
        "total_documents": len(docs),
        "by_status": by_status,
        "auto_activation": False,
        "xpert_write": False,
        "unofficial_whatsapp": False,
    }
