"""APIs Sprint 10 — correlação, defasagem e repasse."""

from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_audit_context, get_current_active_user
from app.core.exceptions import AppError
from app.core.permissions import Permission
from app.schemas.market_analysis import (
    MarketParametersUpsert,
    MarketRunCreate,
    MarketRunReprocess,
    MarketRunResponse,
    params_to_response,
)
from app.services.audit_service import AuditContext
from app.services.auth_service import AuthenticatedUser
from app.services.market_analysis_service import MarketAnalysisService

runs_router = APIRouter(prefix="/market-analysis", tags=["market-analysis"])
analytics_router = APIRouter(
    prefix="/analytics/market-correlation", tags=["market-correlation-analytics"]
)


def _ensure(user: AuthenticatedUser, permission: Permission) -> None:
    if permission.value not in user.permissions:
        raise AppError(
            "Você não possui permissão para executar esta ação.",
            status_code=403,
            code="FORBIDDEN",
        )


@runs_router.get("/parameters")
async def get_parameters(
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.MARKET_ANALYSIS_READ)
    p = await MarketAnalysisService(db).get_or_create_parameters(user.organization_id, user.id)
    return params_to_response(p)


@runs_router.put("/parameters")
async def put_parameters(
    payload: MarketParametersUpsert,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
    audit_ctx: AuditContext = Depends(get_audit_context),
):
    _ensure(user, Permission.MARKET_ANALYSIS_MANAGE_PARAMETERS)
    p = await MarketAnalysisService(db).upsert_parameters(
        organization_id=user.organization_id,
        user_id=user.id,
        data=payload.model_dump(exclude_none=True),
        audit_ctx=audit_ctx,
    )
    return params_to_response(p)


@runs_router.post("/runs", response_model=MarketRunResponse, status_code=201)
async def create_run(
    payload: MarketRunCreate,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
    audit_ctx: AuditContext = Depends(get_audit_context),
):
    _ensure(user, Permission.MARKET_ANALYSIS_RUN)
    data = payload.model_dump(mode="json")
    run = await MarketAnalysisService(db).run_analysis(
        organization_id=user.organization_id,
        user_id=user.id,
        data=data,
        audit_ctx=audit_ctx,
    )
    return run


@runs_router.get("/runs", response_model=list[MarketRunResponse])
async def list_runs(
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.MARKET_ANALYSIS_READ)
    return await MarketAnalysisService(db).list_runs(user.organization_id)


@runs_router.get("/runs/{run_id}", response_model=MarketRunResponse)
async def get_run(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.MARKET_ANALYSIS_READ)
    return await MarketAnalysisService(db).get_run(run_id, user.organization_id)


@runs_router.post("/runs/{run_id}/reprocess", response_model=MarketRunResponse)
async def reprocess_run(
    run_id: uuid.UUID,
    payload: MarketRunReprocess,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
    audit_ctx: AuditContext = Depends(get_audit_context),
):
    _ensure(user, Permission.MARKET_ANALYSIS_REPROCESS)
    return await MarketAnalysisService(db).reprocess(
        run_id=run_id,
        organization_id=user.organization_id,
        user_id=user.id,
        reason=payload.reason,
        audit_ctx=audit_ctx,
    )


@runs_router.get("/runs/{run_id}/results")
async def run_results(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.MARKET_ANALYSIS_VIEW_STATISTICS)
    rows = await MarketAnalysisService(db).list_results(run_id, user.organization_id)
    return [
        {
            "id": str(r.id),
            "metric_type": r.metric_type,
            "coefficient": str(r.coefficient) if r.coefficient is not None else None,
            "lag_value": r.lag_value,
            "sample_size": r.sample_size,
            "coverage_percentage": str(r.coverage_percentage)
            if r.coverage_percentage is not None
            else None,
            "pass_through_ratio": str(r.pass_through_ratio)
            if r.pass_through_ratio is not None
            else None,
            "quality_status": r.quality_status,
            "warnings": r.warnings,
            "details": r.details,
        }
        for r in rows
    ]


@runs_router.get("/runs/{run_id}/aligned-observations")
async def run_aligned(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.MARKET_ANALYSIS_VIEW_RAW_PAIRS)
    rows = await MarketAnalysisService(db).list_aligned(run_id, user.organization_id)
    return [
        {
            "period_datetime": r.period_datetime.isoformat(),
            "external_value": str(r.external_value),
            "internal_value": str(r.internal_value),
            "external_change": str(r.external_change) if r.external_change is not None else None,
            "internal_change": str(r.internal_change) if r.internal_change is not None else None,
            "lag_applied": r.lag_applied,
            "carry_forward": r.carry_forward,
            "included": r.included,
            "exclusion_reason": r.exclusion_reason,
        }
        for r in rows
    ]


@runs_router.get("/runs/{run_id}/pass-through-events")
async def run_pass_through(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.MARKET_ANALYSIS_VIEW_STATISTICS)
    rows = await MarketAnalysisService(db).list_pass_through(run_id, user.organization_id)
    return [
        {
            "event_direction": r.event_direction,
            "lag_value": r.lag_value,
            "reference_change": str(r.reference_change),
            "target_change": str(r.target_change),
            "pass_through_ratio": str(r.pass_through_ratio)
            if r.pass_through_ratio is not None
            else None,
            "pass_through_elasticity": str(r.pass_through_elasticity)
            if r.pass_through_elasticity is not None
            else None,
            "quality_status": r.quality_status,
        }
        for r in rows
    ]


@analytics_router.get("/summary")
async def analytics_summary(
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.MARKET_ANALYSIS_READ)
    return await MarketAnalysisService(db).analytics_summary(user.organization_id)


@analytics_router.get("/lags")
async def analytics_lags(
    run_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.MARKET_ANALYSIS_VIEW_STATISTICS)
    run = await MarketAnalysisService(db).get_run(run_id, user.organization_id)
    return (run.output_snapshot or {}).get("lags", [])


@analytics_router.get("/pass-through")
async def analytics_pass_through(
    run_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.MARKET_ANALYSIS_VIEW_STATISTICS)
    run = await MarketAnalysisService(db).get_run(run_id, user.organization_id)
    return (run.output_snapshot or {}).get("pass_through", {})


@analytics_router.get("/asymmetry")
async def analytics_asymmetry(
    run_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.MARKET_ANALYSIS_VIEW_STATISTICS)
    run = await MarketAnalysisService(db).get_run(run_id, user.organization_id)
    pt = (run.output_snapshot or {}).get("pass_through") or {}
    return {
        "upward_average_ratio": pt.get("upward_average_ratio"),
        "downward_average_ratio": pt.get("downward_average_ratio"),
        "asymmetry": pt.get("asymmetry"),
        "disclaimer": run.interpretive_disclaimer,
    }


@analytics_router.get("/data-quality")
async def analytics_quality(
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.MARKET_ANALYSIS_READ)
    runs = await MarketAnalysisService(db).list_runs(user.organization_id)
    return [
        {
            "run_id": str(r.id),
            "status": r.status,
            "sample_size": r.sample_size,
            "warning_count": r.warning_count,
            "quality_status": (r.output_snapshot or {}).get("quality_status"),
            "disclaimer": r.interpretive_disclaimer,
        }
        for r in runs
    ]


@analytics_router.get("/export/csv")
async def export_csv(
    run_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.MARKET_ANALYSIS_EXPORT)
    run = await MarketAnalysisService(db).get_run(run_id, user.organization_id)
    # exporta do snapshot — imutável
    snap = run.output_snapshot or {}
    lines = ["metric,value,note"]
    lines.append(f"disclaimer,\"{run.interpretive_disclaimer}\",")
    lines.append(f"status,{run.status},")
    lines.append(f"sample_size,{run.sample_size},")
    lines.append(f"selected_lag,{run.selected_lag},defasagem estimada")
    pear = snap.get("pearson") or {}
    lines.append(f"pearson,{pear.get('coefficient')},associacao observada")
    spear = snap.get("spearman") or {}
    lines.append(f"spearman,{spear.get('coefficient')},associacao observada")
    pt = snap.get("pass_through") or {}
    lines.append(f"upward_pass_through,{pt.get('upward_average_ratio')},repasse observado")
    lines.append(f"downward_pass_through,{pt.get('downward_average_ratio')},repasse observado")
    return Response(
        content="\n".join(lines) + "\n",
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="market-analysis-{run_id}.csv"'},
    )


@analytics_router.get("/export/pdf")
async def export_pdf_placeholder(
    run_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.MARKET_ANALYSIS_EXPORT)
    run = await MarketAnalysisService(db).get_run(run_id, user.organization_id)
    body = {
        "title": "Relatório de correlação e repasse",
        "disclaimer": run.interpretive_disclaimer,
        "snapshot_hash": run.snapshot_hash,
        "output": run.output_snapshot,
        "note": "Exportação baseada em snapshot imutável. Sem previsão ou recomendação.",
    }
    return Response(
        content=json.dumps(body, ensure_ascii=False, indent=2, default=str).encode("utf-8"),
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="market-analysis-report.json"'},
    )
