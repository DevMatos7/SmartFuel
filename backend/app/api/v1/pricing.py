"""APIs Sprint 11 — formação de preço, margem, aprovação e evidências."""

from __future__ import annotations

import csv
import io
import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_audit_context, get_current_active_user
from app.core.exceptions import AppError
from app.core.permissions import Permission
from app.schemas.pricing import (
    DecisionAction,
    DecisionCreate,
    DecisionResponse,
    ErpPriceCheck,
    EvidenceCreate,
    ImplementationConfirm,
    PricingItemResponse,
    PricingPolicyCreate,
    PricingPolicyResponse,
    PricingRunCreate,
    PricingRunReprocess,
    PricingRunResponse,
    SyntheticHomologationRequest,
)
from app.services.audit_service import AuditContext
from app.services.auth_service import AuthenticatedUser
from app.services.pricing_recommendation_service import PricingRecommendationService

pricing_router = APIRouter(prefix="/pricing", tags=["pricing"])
analytics_router = APIRouter(prefix="/analytics/pricing", tags=["pricing-analytics"])


def _ensure(user: AuthenticatedUser, permission: Permission) -> None:
    if permission.value not in user.permissions:
        raise AppError(
            "Você não possui permissão para executar esta ação.",
            status_code=403,
            code="FORBIDDEN",
        )


def _ensure_station_scope(user: AuthenticatedUser, station_id: uuid.UUID | None) -> None:
    if station_id is None or user.has_all_stations_access:
        return
    if "ADMIN" in user.role_codes:
        return
    # Escopo detalhado por posto é aplicado nos serviços de analytics existentes;
    # na fundação, usuários sem acesso total ainda podem operar se tiverem a permissão.
    return


# ---- policies ----
@pricing_router.get("/policies", response_model=list[PricingPolicyResponse])
async def list_policies(
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.PRICING_READ)
    return await PricingRecommendationService(db).list_policies(user.organization_id)


@pricing_router.post("/policies", response_model=PricingPolicyResponse, status_code=201)
async def create_policy(
    payload: PricingPolicyCreate,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
    audit_ctx: AuditContext = Depends(get_audit_context),
):
    _ensure(user, Permission.PRICING_MANAGE_POLICIES)
    _ensure_station_scope(user, payload.station_id)
    return await PricingRecommendationService(db).create_policy(
        organization_id=user.organization_id,
        user_id=user.id,
        data=payload.model_dump(mode="json"),
        audit_ctx=audit_ctx,
    )


@pricing_router.get("/policies/{policy_id}", response_model=PricingPolicyResponse)
async def get_policy(
    policy_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.PRICING_READ)
    return await PricingRecommendationService(db).get_policy(policy_id, user.organization_id)


@pricing_router.post("/policies/{policy_id}/deactivate", response_model=PricingPolicyResponse)
async def deactivate_policy(
    policy_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
    audit_ctx: AuditContext = Depends(get_audit_context),
):
    _ensure(user, Permission.PRICING_MANAGE_POLICIES)
    return await PricingRecommendationService(db).deactivate_policy(
        policy_id, user.organization_id, audit_ctx=audit_ctx
    )


# ---- recommendations ----
@pricing_router.post("/recommendations/runs", response_model=PricingRunResponse, status_code=201)
async def create_run(
    payload: PricingRunCreate,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
    audit_ctx: AuditContext = Depends(get_audit_context),
):
    _ensure(user, Permission.PRICING_GENERATE_RECOMMENDATION)
    _ensure_station_scope(user, payload.station_id)
    return await PricingRecommendationService(db).run_recommendations(
        organization_id=user.organization_id,
        user_id=user.id,
        data=payload.model_dump(mode="json"),
        audit_ctx=audit_ctx,
    )


@pricing_router.get("/recommendations/runs", response_model=list[PricingRunResponse])
async def list_runs(
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.PRICING_READ)
    return await PricingRecommendationService(db).list_runs(user.organization_id)


@pricing_router.get("/recommendations/runs/{run_id}", response_model=PricingRunResponse)
async def get_run(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.PRICING_READ)
    return await PricingRecommendationService(db).get_run(run_id, user.organization_id)


@pricing_router.post("/recommendations/runs/{run_id}/reprocess", response_model=PricingRunResponse)
async def reprocess_run(
    run_id: uuid.UUID,
    payload: PricingRunReprocess,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
    audit_ctx: AuditContext = Depends(get_audit_context),
):
    _ensure(user, Permission.PRICING_GENERATE_RECOMMENDATION)
    return await PricingRecommendationService(db).reprocess_run(
        run_id=run_id,
        organization_id=user.organization_id,
        user_id=user.id,
        reason=payload.reason,
        audit_ctx=audit_ctx,
    )


@pricing_router.get("/recommendations", response_model=list[PricingItemResponse])
async def list_recommendations(
    station_id: uuid.UUID | None = None,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.PRICING_READ)
    _ensure_station_scope(user, station_id)
    items = await PricingRecommendationService(db).list_items(
        user.organization_id, station_id=station_id, status=status
    )
    if Permission.PRICING_VIEW_COST.value not in user.permissions:
        for i in items:
            i.cost_per_liter = None
            i.current_margin_per_liter = None
            i.current_margin_percentage = None
            i.current_markup_percentage = None
    return items


@pricing_router.get("/recommendations/{item_id}", response_model=PricingItemResponse)
async def get_recommendation(
    item_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.PRICING_READ)
    item = await PricingRecommendationService(db).get_item(item_id, user.organization_id)
    _ensure_station_scope(user, item.station_id)
    if Permission.PRICING_VIEW_COST.value not in user.permissions:
        item.cost_per_liter = None
        item.current_margin_per_liter = None
    return item


@pricing_router.get("/recommendations/{item_id}/scenarios")
async def get_scenarios(
    item_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.PRICING_READ)
    svc = PricingRecommendationService(db)
    item = await svc.get_item(item_id, user.organization_id)
    _ensure_station_scope(user, item.station_id)
    rows = await svc.list_scenarios(item_id)
    return [
        {
            "id": str(s.id),
            "scenario_type": s.scenario_type,
            "cost_per_liter": str(s.cost_per_liter),
            "margin_per_liter": str(s.margin_per_liter),
            "margin_percentage": str(s.margin_percentage) if s.margin_percentage is not None else None,
            "markup_percentage": str(s.markup_percentage) if s.markup_percentage is not None else None,
            "calculated_price": str(s.calculated_price),
            "rounded_price": str(s.rounded_price),
            "details": s.details,
        }
        for s in rows
    ]


# ---- decisions ----
@pricing_router.post(
    "/recommendations/{item_id}/decision", response_model=DecisionResponse, status_code=201
)
async def create_decision(
    item_id: uuid.UUID,
    payload: DecisionCreate,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
    audit_ctx: AuditContext = Depends(get_audit_context),
):
    _ensure(user, Permission.PRICING_REVIEW)
    return await PricingRecommendationService(db).create_decision(
        organization_id=user.organization_id,
        user_id=user.id,
        item_id=item_id,
        data=payload.model_dump(mode="json"),
        audit_ctx=audit_ctx,
    )


@pricing_router.get("/decisions", response_model=list[DecisionResponse])
async def list_decisions(
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.PRICING_READ)
    return await PricingRecommendationService(db).list_decisions(
        user.organization_id, status=status
    )


@pricing_router.get("/decisions/{decision_id}", response_model=DecisionResponse)
async def get_decision(
    decision_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.PRICING_READ)
    return await PricingRecommendationService(db).get_decision(decision_id, user.organization_id)


@pricing_router.post("/decisions/{decision_id}/submit", response_model=DecisionResponse)
async def submit_decision(
    decision_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
    audit_ctx: AuditContext = Depends(get_audit_context),
):
    _ensure(user, Permission.PRICING_REVIEW)
    return await PricingRecommendationService(db).submit_decision(
        decision_id, user.organization_id, audit_ctx=audit_ctx
    )


@pricing_router.post("/decisions/{decision_id}/approve", response_model=DecisionResponse)
async def approve_decision(
    decision_id: uuid.UUID,
    payload: DecisionAction,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
    audit_ctx: AuditContext = Depends(get_audit_context),
):
    _ensure(user, Permission.PRICING_APPROVE)
    return await PricingRecommendationService(db).approve_decision(
        decision_id=decision_id,
        organization_id=user.organization_id,
        user_id=user.id,
        comment=payload.comment,
        approved_price=payload.approved_price,
        allow_self_approval=payload.allow_self_approval,
        audit_ctx=audit_ctx,
    )


@pricing_router.post("/decisions/{decision_id}/reject", response_model=DecisionResponse)
async def reject_decision(
    decision_id: uuid.UUID,
    payload: DecisionAction,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
    audit_ctx: AuditContext = Depends(get_audit_context),
):
    _ensure(user, Permission.PRICING_REJECT)
    return await PricingRecommendationService(db).reject_decision(
        decision_id=decision_id,
        organization_id=user.organization_id,
        user_id=user.id,
        comment=payload.comment,
        audit_ctx=audit_ctx,
    )


@pricing_router.post("/decisions/{decision_id}/cancel", response_model=DecisionResponse)
async def cancel_decision(
    decision_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
    audit_ctx: AuditContext = Depends(get_audit_context),
):
    _ensure(user, Permission.PRICING_REVIEW)
    return await PricingRecommendationService(db).cancel_decision(
        decision_id, user.organization_id, audit_ctx=audit_ctx
    )


@pricing_router.post("/decisions/{decision_id}/evidence", status_code=201)
async def add_evidence(
    decision_id: uuid.UUID,
    payload: EvidenceCreate,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
    audit_ctx: AuditContext = Depends(get_audit_context),
):
    _ensure(user, Permission.PRICING_ADD_EVIDENCE)
    ev = await PricingRecommendationService(db).add_evidence(
        decision_id=decision_id,
        organization_id=user.organization_id,
        user_id=user.id,
        data=payload.model_dump(mode="json"),
        audit_ctx=audit_ctx,
    )
    return {"id": str(ev.id), "evidence_type": ev.evidence_type, "uploaded_at": ev.uploaded_at}


@pricing_router.get("/decisions/{decision_id}/evidence")
async def list_evidence(
    decision_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.PRICING_READ)
    rows = await PricingRecommendationService(db).list_evidence(decision_id, user.organization_id)
    return [
        {
            "id": str(e.id),
            "evidence_type": e.evidence_type,
            "description": e.description,
            "sha256": e.sha256,
            "original_filename": e.original_filename,
            "uploaded_at": e.uploaded_at,
        }
        for e in rows
    ]


@pricing_router.post("/decisions/{decision_id}/confirm-implementation")
async def confirm_implementation(
    decision_id: uuid.UUID,
    payload: ImplementationConfirm,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
    audit_ctx: AuditContext = Depends(get_audit_context),
):
    _ensure(user, Permission.PRICING_CONFIRM_IMPLEMENTATION)
    check = await PricingRecommendationService(db).confirm_implementation(
        decision_id=decision_id,
        organization_id=user.organization_id,
        user_id=user.id,
        implemented_price=payload.implemented_price,
        implemented_at=payload.implemented_at,
        note=payload.note,
        tolerance=payload.tolerance,
        audit_ctx=audit_ctx,
    )
    return {
        "id": str(check.id),
        "status": check.status,
        "approved_price": str(check.approved_price),
        "implemented_price": str(check.implemented_price) if check.implemented_price else None,
        "implementation_variance": str(check.implementation_variance)
        if check.implementation_variance is not None
        else None,
        "xpert_write": False,
    }


@pricing_router.post("/decisions/{decision_id}/check-erp-price")
async def check_erp_price(
    decision_id: uuid.UUID,
    payload: ErpPriceCheck,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
    audit_ctx: AuditContext = Depends(get_audit_context),
):
    _ensure(user, Permission.PRICING_CONFIRM_IMPLEMENTATION)
    check = await PricingRecommendationService(db).check_erp_price(
        decision_id=decision_id,
        organization_id=user.organization_id,
        user_id=user.id,
        implemented_price=payload.implemented_price,
        price_snapshot_id=payload.price_snapshot_id,
        tolerance=payload.tolerance,
        stale=payload.stale,
        audit_ctx=audit_ctx,
    )
    return {
        "id": str(check.id),
        "status": check.status,
        "check_type": check.check_type,
        "xpert_write": False,
    }


@pricing_router.get("/decisions/{decision_id}/implementation-checks")
async def list_impl_checks(
    decision_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.PRICING_READ)
    rows = await PricingRecommendationService(db).list_implementation_checks(
        decision_id, user.organization_id
    )
    return [
        {
            "id": str(c.id),
            "check_type": c.check_type,
            "status": c.status,
            "approved_price": str(c.approved_price),
            "implemented_price": str(c.implemented_price) if c.implemented_price else None,
            "implementation_variance": str(c.implementation_variance)
            if c.implementation_variance is not None
            else None,
            "checked_at": c.checked_at,
        }
        for c in rows
    ]


@pricing_router.post("/homologation/synthetic")
async def synthetic_homologation(
    payload: SyntheticHomologationRequest,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
    audit_ctx: AuditContext = Depends(get_audit_context),
):
    _ensure(user, Permission.PRICING_GENERATE_RECOMMENDATION)
    _ensure_station_scope(user, payload.station_id)
    return await PricingRecommendationService(db).create_synthetic_homologation_pack(
        organization_id=user.organization_id,
        user_id=user.id,
        station_id=payload.station_id,
        product_id=payload.canonical_product_id,
        audit_ctx=audit_ctx,
    )


# ---- analytics ----
@analytics_router.get("/summary")
async def analytics_summary(
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.PRICING_READ)
    return await PricingRecommendationService(db).summary(user.organization_id)


@analytics_router.get("/current-margins")
async def current_margins(
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.PRICING_VIEW_MARGIN)
    items = await PricingRecommendationService(db).list_items(user.organization_id)
    return [
        {
            "id": str(i.id),
            "station_id": str(i.station_id),
            "canonical_product_id": str(i.canonical_product_id),
            "current_price": str(i.current_price) if i.current_price is not None else None,
            "cost_per_liter": str(i.cost_per_liter) if i.cost_per_liter is not None else None,
            "current_margin_per_liter": str(i.current_margin_per_liter)
            if i.current_margin_per_liter is not None
            else None,
            "current_margin_percentage": str(i.current_margin_percentage)
            if i.current_margin_percentage is not None
            else None,
            "commercial_floor_price": str(i.commercial_floor_price)
            if i.commercial_floor_price is not None
            else None,
            "recommendation_status": i.recommendation_status,
            "quality_status": i.quality_status,
        }
        for i in items
    ]


@analytics_router.get("/below-floor")
async def below_floor(
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.PRICING_VIEW_MARGIN)
    items = await PricingRecommendationService(db).list_items(user.organization_id)
    return [
        {
            "id": str(i.id),
            "station_id": str(i.station_id),
            "current_price": str(i.current_price),
            "commercial_floor_price": str(i.commercial_floor_price),
            "gap": str(i.commercial_floor_price - i.current_price)
            if i.commercial_floor_price is not None and i.current_price is not None
            else None,
        }
        for i in items
        if i.commercial_floor_price is not None
        and i.current_price is not None
        and i.current_price < i.commercial_floor_price
    ]


@analytics_router.get("/recommendations")
async def analytics_recommendations(
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.PRICING_READ)
    items = await PricingRecommendationService(db).list_items(user.organization_id)
    return [
        {
            "id": str(i.id),
            "station_id": str(i.station_id),
            "recommendation_status": i.recommendation_status,
            "recommended_price": str(i.recommended_price) if i.recommended_price else None,
            "reasons": i.reasons,
            "quality_status": i.quality_status,
        }
        for i in items
    ]


@analytics_router.get("/approval-queue")
async def approval_queue(
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.PRICING_READ)
    rows = await PricingRecommendationService(db).list_decisions(
        user.organization_id, status="PENDING_APPROVAL"
    )
    return [
        {
            "id": str(d.id),
            "recommended_price": str(d.recommended_price),
            "status": d.status,
            "created_at": d.created_at,
        }
        for d in rows
    ]


@analytics_router.get("/implementation-adherence")
async def implementation_adherence(
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.PRICING_READ)
    decisions = await PricingRecommendationService(db).list_decisions(user.organization_id)
    return {
        "matched": sum(1 for d in decisions if d.status == "IMPLEMENTED_MATCHED"),
        "different": sum(1 for d in decisions if d.status == "IMPLEMENTED_DIFFERENT"),
        "pending": sum(1 for d in decisions if d.status == "APPROVED_PENDING_IMPLEMENTATION"),
    }


@analytics_router.get("/data-quality")
async def data_quality(
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.PRICING_READ)
    items = await PricingRecommendationService(db).list_items(user.organization_id)
    by_q: dict[str, int] = {}
    for i in items:
        by_q[i.quality_status] = by_q.get(i.quality_status, 0) + 1
    return {"by_quality_status": by_q, "total": len(items)}


@analytics_router.get("/export/csv")
async def export_csv(
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.PRICING_EXPORT)
    items = await PricingRecommendationService(db).list_items(user.organization_id)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "id",
            "station_id",
            "product_id",
            "current_price",
            "cost_per_liter",
            "margin_per_liter",
            "floor",
            "target",
            "recommended",
            "status",
            "quality",
            "snapshot_hash",
        ]
    )
    for i in items:
        writer.writerow(
            [
                str(i.id),
                str(i.station_id),
                str(i.canonical_product_id),
                i.current_price,
                i.cost_per_liter if Permission.PRICING_VIEW_COST.value in user.permissions else "",
                i.current_margin_per_liter
                if Permission.PRICING_VIEW_MARGIN.value in user.permissions
                else "",
                i.commercial_floor_price,
                i.target_price,
                i.recommended_price,
                i.recommendation_status,
                i.quality_status,
                i.snapshot_hash,
            ]
        )
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=pricing-export.csv"},
    )


@analytics_router.get("/export/pdf")
async def export_pdf_placeholder(
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.PRICING_EXPORT)
    # Pacote completo PDF usa snapshots persistidos; placeholder textual na fundação.
    body = (
        "Smart Fuel — Exportação de precificação\n"
        "Dados exportados a partir de snapshots persistidos.\n"
        "Margem bruta comercial estimada. Não é lucro líquido.\n"
        "Sem escrita no XPERT.\n"
    )
    return Response(
        content=body,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=pricing-export.pdf"},
    )


@pricing_router.get("/decisions/{decision_id}/evidence-package/pdf")
async def evidence_package_pdf(
    decision_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.PRICING_EXPORT)
    svc = PricingRecommendationService(db)
    d = await svc.get_decision(decision_id, user.organization_id)
    item = await svc.get_item(d.recommendation_item_id, user.organization_id)
    evidence = await svc.list_evidence(decision_id, user.organization_id)
    lines = [
        "PACOTE DE EVIDÊNCIAS — FORMAÇÃO DE PREÇO",
        f"decision_id={d.id}",
        f"status={d.status}",
        f"recommended_price={d.recommended_price}",
        f"approved_price={d.approved_price}",
        f"item_snapshot_hash={item.snapshot_hash}",
        f"current_price={item.current_price}",
        f"cost_per_liter={item.cost_per_liter}",
        f"floor={item.commercial_floor_price}",
        f"target={item.target_price}",
        f"reasons={item.reasons}",
        "disclaimer=Margem bruta comercial estimada. Não é lucro líquido.",
        "xpert_write=false",
        f"evidence_count={len(evidence)}",
    ]
    for e in evidence:
        lines.append(f"evidence={e.id};type={e.evidence_type};sha256={e.sha256}")
    return Response(
        content="\n".join(lines) + "\n",
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=evidence-{decision_id}.pdf"},
    )
