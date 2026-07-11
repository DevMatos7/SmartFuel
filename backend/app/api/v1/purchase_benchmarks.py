"""APIs — Sprint 8 purchase benchmarks."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import AppError
from app.core.permissions import Permission
from app.schemas.purchase_benchmarks import (
    BenchmarkCoverageResponse,
    BenchmarkDataQualityResponse,
    BenchmarkDistributorOverrideRequest,
    BenchmarkItemResponse,
    BenchmarkOpportunityRow,
    BenchmarkParametersResponse,
    BenchmarkParametersUpsert,
    BenchmarkReferenceOverrideRequest,
    BenchmarkReprocessRequest,
    BenchmarkRunCreate,
    BenchmarkRunDetailResponse,
    BenchmarkRunListItem,
    BenchmarkRunListResponse,
    BenchmarkRunDetailResponse as _Detail,
    BenchmarkSummaryResponse,
)
from app.services.auth_service import AuthService, AuthenticatedUser
from app.core.dependencies import get_current_active_user
from app.services.purchase_benchmark_analytics_service import PurchaseBenchmarkAnalyticsService
from app.services.purchase_quote_benchmark_service import PurchaseQuoteBenchmarkService

runs_router = APIRouter(prefix="/purchase-benchmarks", tags=["purchase-benchmarks"])
analytics_router = APIRouter(prefix="/analytics/purchase-benchmarks", tags=["purchase-benchmarks-analytics"])
invoice_bench_router = APIRouter(prefix="/fuel-purchase-invoices", tags=["purchase-invoice-benchmarks"])


def _ensure(user: AuthenticatedUser, permission: Permission) -> None:
    if permission.value not in user.permissions:
        raise AppError(
            "Você não possui permissão para executar esta ação.",
            status_code=403,
            code="FORBIDDEN",
        )


async def _stations(
    auth: AuthService, user: AuthenticatedUser, station_ids: list[uuid.UUID] | None
) -> list[uuid.UUID]:
    stations = await auth.allowed_stations(user)
    allowed = [s.id for s in stations]
    if station_ids:
        bad = [s for s in station_ids if s not in allowed]
        if bad:
            raise AppError("Posto fora do escopo.", status_code=403, code="FORBIDDEN")
        return station_ids
    return allowed


def _dec(v) -> str | None:
    if v is None:
        return None
    return format(v, "f")


def _run_list_item(run, include_opportunity: bool) -> BenchmarkRunListItem:
    return BenchmarkRunListItem(
        id=run.id,
        purchase_invoice_id=run.purchase_invoice_id,
        station_id=run.station_id,
        status=run.status,
        comparison_mode=run.comparison_mode,
        reference_datetime=run.reference_datetime,
        reference_source=run.reference_source,
        reference_confidence=run.reference_confidence,
        item_count=run.item_count,
        benchmarked_item_count=run.benchmarked_item_count,
        opportunity_amount=_dec(run.opportunity_amount) if include_opportunity else None,
        cost_variance_amount=_dec(run.cost_variance_amount),
        created_at=run.created_at,
        finished_at=run.finished_at,
        snapshot_hash=run.snapshot_hash,
    )


def _item_resp(item, include_opportunity: bool) -> BenchmarkItemResponse:
    return BenchmarkItemResponse(
        id=item.id,
        group_key=item.group_key,
        canonical_product_id=item.canonical_product_id,
        actual_distributor_id=item.actual_distributor_id,
        volume_liters=_dec(item.volume_liters) or "0",
        actual_delivered_cost=_dec(item.actual_delivered_cost) or "0",
        actual_delivered_cost_per_liter=_dec(item.actual_delivered_cost_per_liter),
        benchmark_status=item.benchmark_status,
        decision_result=item.decision_result,
        best_quote_id=item.best_quote_id,
        best_distributor_id=item.best_distributor_id,
        benchmark_cost_per_liter=_dec(item.benchmark_cost_per_liter),
        cost_variance_per_liter=_dec(item.cost_variance_per_liter),
        cost_variance_amount=_dec(item.cost_variance_amount),
        opportunity_amount=_dec(item.opportunity_amount) if include_opportunity else None,
        actual_advantage_amount=_dec(item.actual_advantage_amount),
        actual_distributor_rank=item.actual_distributor_rank,
        candidate_count=item.candidate_count,
        eligible_candidate_count=item.eligible_candidate_count,
        exclusion_reasons=item.exclusion_reasons,
        warnings=item.warnings,
    )


@runs_router.post("/runs", response_model=BenchmarkRunDetailResponse)
async def create_run(
    payload: BenchmarkRunCreate,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
) -> BenchmarkRunDetailResponse:
    _ensure(user, Permission.PURCHASE_BENCHMARKS_RUN)
    stations = await _stations(AuthService(db), user, None)
    try:
        run = await PurchaseQuoteBenchmarkService(db).run_for_invoice(
            organization_id=user.organization_id,
            invoice_id=payload.purchase_invoice_id,
            station_ids=stations,
            requested_by=user.id,
            comparison_mode=payload.comparison_mode,
        )
        await db.commit()
    except ValueError as exc:
        if str(exc) == "NOT_FOUND":
            raise AppError("Nota não encontrada.", status_code=404, code="NOT_FOUND") from exc
        raise
    return await _detail(db, user, run.id, stations)


@runs_router.get("/runs", response_model=BenchmarkRunListResponse)
async def list_runs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    purchase_invoice_id: uuid.UUID | None = None,
    station_ids: list[uuid.UUID] | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
) -> BenchmarkRunListResponse:
    _ensure(user, Permission.PURCHASE_BENCHMARKS_READ)
    stations = await _stations(AuthService(db), user, station_ids)
    include_opp = Permission.PURCHASE_BENCHMARKS_VIEW_OPPORTUNITY.value in user.permissions
    rows, total = await PurchaseBenchmarkAnalyticsService(db).list_runs(
        organization_id=user.organization_id,
        station_ids=stations,
        invoice_id=purchase_invoice_id,
        page=page,
        page_size=page_size,
    )
    return BenchmarkRunListResponse(
        items=[_run_list_item(r, include_opp) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@runs_router.get("/runs/{run_id}", response_model=BenchmarkRunDetailResponse)
async def get_run(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
) -> BenchmarkRunDetailResponse:
    _ensure(user, Permission.PURCHASE_BENCHMARKS_READ)
    stations = await _stations(AuthService(db), user, None)
    return await _detail(db, user, run_id, stations)


@runs_router.post("/runs/{run_id}/reprocess", response_model=BenchmarkRunDetailResponse)
async def reprocess_run(
    run_id: uuid.UUID,
    payload: BenchmarkReprocessRequest,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
) -> BenchmarkRunDetailResponse:
    _ensure(user, Permission.PURCHASE_BENCHMARKS_REPROCESS)
    stations = await _stations(AuthService(db), user, None)
    try:
        run = await PurchaseQuoteBenchmarkService(db).reprocess(
            organization_id=user.organization_id,
            run_id=run_id,
            station_ids=stations,
            requested_by=user.id,
            reason=payload.reason,
        )
        await db.commit()
    except ValueError as exc:
        if str(exc) == "NOT_FOUND":
            raise AppError("Run não encontrada.", status_code=404, code="NOT_FOUND") from exc
        raise
    return await _detail(db, user, run.id, stations)


@runs_router.get("/parameters", response_model=BenchmarkParametersResponse | None)
async def get_parameters(
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.PURCHASE_BENCHMARKS_READ)
    from datetime import UTC, datetime
    from sqlalchemy import select
    from app.models.purchase_benchmarks import PurchaseBenchmarkParameter

    row = (
        await db.execute(
            select(PurchaseBenchmarkParameter)
            .where(
                PurchaseBenchmarkParameter.organization_id == user.organization_id,
                PurchaseBenchmarkParameter.valid_until.is_(None),
            )
            .order_by(PurchaseBenchmarkParameter.valid_from.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if row is None:
        return None
    return BenchmarkParametersResponse(
        id=row.id,
        absolute_tolerance_per_liter=_dec(row.absolute_tolerance_per_liter) or "0",
        percentage_tolerance=_dec(row.percentage_tolerance) or "0",
        allow_low_confidence_reference=row.allow_low_confidence_reference,
        default_comparison_mode=row.default_comparison_mode,
        valid_from=row.valid_from,
        valid_until=row.valid_until,
        active=row.active,
    )


@runs_router.put("/parameters", response_model=BenchmarkParametersResponse)
async def put_parameters(
    payload: BenchmarkParametersUpsert,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
) -> BenchmarkParametersResponse:
    _ensure(user, Permission.PURCHASE_BENCHMARKS_MANAGE_PARAMETERS)
    row = await PurchaseBenchmarkAnalyticsService(db).upsert_parameters(
        organization_id=user.organization_id,
        absolute_tolerance_per_liter=Decimal(payload.absolute_tolerance_per_liter),
        percentage_tolerance=Decimal(payload.percentage_tolerance),
        allow_low_confidence_reference=payload.allow_low_confidence_reference,
        default_comparison_mode=payload.default_comparison_mode,
        created_by=user.id,
    )
    await db.commit()
    return BenchmarkParametersResponse(
        id=row.id,
        absolute_tolerance_per_liter=_dec(row.absolute_tolerance_per_liter) or "0",
        percentage_tolerance=_dec(row.percentage_tolerance) or "0",
        allow_low_confidence_reference=row.allow_low_confidence_reference,
        default_comparison_mode=row.default_comparison_mode,
        valid_from=row.valid_from,
        valid_until=row.valid_until,
        active=row.active,
    )


async def _detail(
    db: AsyncSession, user: AuthenticatedUser, run_id: uuid.UUID, stations: list[uuid.UUID]
) -> BenchmarkRunDetailResponse:
    svc = PurchaseBenchmarkAnalyticsService(db)
    run = await svc.get_run(organization_id=user.organization_id, run_id=run_id, station_ids=stations)
    if run is None:
        raise AppError("Run não encontrada.", status_code=404, code="NOT_FOUND")
    include_opp = Permission.PURCHASE_BENCHMARKS_VIEW_OPPORTUNITY.value in user.permissions
    items = await svc.list_run_items(run.id)
    return BenchmarkRunDetailResponse(
        id=run.id,
        purchase_invoice_id=run.purchase_invoice_id,
        station_id=run.station_id,
        status=run.status,
        comparison_mode=run.comparison_mode,
        reference_datetime=run.reference_datetime,
        reference_source=run.reference_source,
        reference_confidence=run.reference_confidence,
        trigger_type=run.trigger_type,
        reprocess_of_run_id=run.reprocess_of_run_id,
        reprocess_reason=run.reprocess_reason,
        item_count=run.item_count,
        benchmarked_item_count=run.benchmarked_item_count,
        warning_count=run.warning_count,
        error_count=run.error_count,
        actual_total_cost=_dec(run.actual_total_cost) or "0",
        benchmark_total_cost=_dec(run.benchmark_total_cost),
        cost_variance_amount=_dec(run.cost_variance_amount),
        opportunity_amount=_dec(run.opportunity_amount) if include_opp else None,
        actual_advantage_amount=_dec(run.actual_advantage_amount),
        snapshot_hash=run.snapshot_hash,
        input_snapshot=run.input_snapshot,
        output_snapshot=run.output_snapshot,
        started_at=run.started_at,
        finished_at=run.finished_at,
        created_at=run.created_at,
        items=[_item_resp(i, include_opp) for i in items],
    )


@invoice_bench_router.post("/{invoice_id}/benchmark", response_model=BenchmarkRunDetailResponse)
async def benchmark_invoice(
    invoice_id: uuid.UUID,
    payload: BenchmarkRunCreate | None = None,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
) -> BenchmarkRunDetailResponse:
    _ensure(user, Permission.PURCHASE_BENCHMARKS_RUN)
    stations = await _stations(AuthService(db), user, None)
    mode = payload.comparison_mode if payload else None
    try:
        run = await PurchaseQuoteBenchmarkService(db).run_for_invoice(
            organization_id=user.organization_id,
            invoice_id=invoice_id,
            station_ids=stations,
            requested_by=user.id,
            comparison_mode=mode,
        )
        await db.commit()
    except ValueError as exc:
        if str(exc) == "NOT_FOUND":
            raise AppError("Nota não encontrada.", status_code=404, code="NOT_FOUND") from exc
        raise
    return await _detail(db, user, run.id, stations)


@invoice_bench_router.get("/{invoice_id}/benchmarks", response_model=BenchmarkRunListResponse)
async def list_invoice_benchmarks(
    invoice_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
) -> BenchmarkRunListResponse:
    _ensure(user, Permission.PURCHASE_BENCHMARKS_READ)
    stations = await _stations(AuthService(db), user, None)
    include_opp = Permission.PURCHASE_BENCHMARKS_VIEW_OPPORTUNITY.value in user.permissions
    rows, total = await PurchaseBenchmarkAnalyticsService(db).list_runs(
        organization_id=user.organization_id,
        station_ids=stations,
        invoice_id=invoice_id,
        page=page,
        page_size=page_size,
    )
    return BenchmarkRunListResponse(
        items=[_run_list_item(r, include_opp) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@invoice_bench_router.get("/{invoice_id}/latest-benchmark", response_model=BenchmarkRunDetailResponse)
async def latest_invoice_benchmark(
    invoice_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
) -> BenchmarkRunDetailResponse:
    _ensure(user, Permission.PURCHASE_BENCHMARKS_READ)
    stations = await _stations(AuthService(db), user, None)
    run = await PurchaseBenchmarkAnalyticsService(db).latest_for_invoice(
        organization_id=user.organization_id, invoice_id=invoice_id, station_ids=stations
    )
    if run is None:
        raise AppError("Nenhum benchmark para esta nota.", status_code=404, code="NOT_FOUND")
    return await _detail(db, user, run.id, stations)


@invoice_bench_router.post("/{invoice_id}/benchmark-reference")
async def override_reference(
    invoice_id: uuid.UUID,
    payload: BenchmarkReferenceOverrideRequest,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.PURCHASE_BENCHMARKS_OVERRIDE_REFERENCE)
    from app.core.purchase_benchmark_enums import BenchmarkOverrideType

    await PurchaseBenchmarkAnalyticsService(db).create_override(
        organization_id=user.organization_id,
        invoice_id=invoice_id,
        override_type=BenchmarkOverrideType.REFERENCE_DATETIME,
        new_value={"reference_datetime": payload.reference_datetime.isoformat()},
        reason=payload.reason,
        created_by=user.id,
    )
    await db.commit()
    return {"ok": True}


@invoice_bench_router.post("/{invoice_id}/actual-distributor-override")
async def override_distributor(
    invoice_id: uuid.UUID,
    payload: BenchmarkDistributorOverrideRequest,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.PURCHASE_BENCHMARKS_OVERRIDE_REFERENCE)
    from app.core.purchase_benchmark_enums import BenchmarkOverrideType

    await PurchaseBenchmarkAnalyticsService(db).create_override(
        organization_id=user.organization_id,
        invoice_id=invoice_id,
        override_type=BenchmarkOverrideType.ACTUAL_DISTRIBUTOR,
        new_value={"distributor_id": str(payload.distributor_id)},
        reason=payload.reason,
        created_by=user.id,
    )
    await db.commit()
    return {"ok": True}


@invoice_bench_router.delete("/{invoice_id}/benchmark-overrides/{override_id}")
async def delete_override(
    invoice_id: uuid.UUID,
    override_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.PURCHASE_BENCHMARKS_OVERRIDE_REFERENCE)
    row = await PurchaseBenchmarkAnalyticsService(db).deactivate_override(
        organization_id=user.organization_id, override_id=override_id
    )
    if row is None or row.purchase_invoice_id != invoice_id:
        raise AppError("Override não encontrado.", status_code=404, code="NOT_FOUND")
    await db.commit()
    return {"ok": True}


@analytics_router.get("/summary", response_model=BenchmarkSummaryResponse)
async def summary(
    date_from: date | None = None,
    date_to: date | None = None,
    station_ids: list[uuid.UUID] | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
) -> BenchmarkSummaryResponse:
    _ensure(user, Permission.PURCHASE_BENCHMARKS_READ)
    stations = await _stations(AuthService(db), user, station_ids)
    include_opp = Permission.PURCHASE_BENCHMARKS_VIEW_OPPORTUNITY.value in user.permissions
    data = await PurchaseBenchmarkAnalyticsService(db).summary(
        organization_id=user.organization_id,
        station_ids=stations,
        date_from=date_from,
        date_to=date_to,
        include_opportunity=include_opp,
    )
    return BenchmarkSummaryResponse(
        purchase_group_count=data["purchase_group_count"],
        benchmarked_group_count=data["benchmarked_group_count"],
        purchased_volume_liters=_dec(data["purchased_volume_liters"]) or "0",
        benchmarked_volume_liters=_dec(data["benchmarked_volume_liters"]) or "0",
        coverage_volume_ratio=_dec(data["coverage_volume_ratio"]),
        actual_total_cost=_dec(data["actual_total_cost"]) or "0",
        benchmark_total_cost=_dec(data["benchmark_total_cost"]),
        cost_variance_amount=_dec(data["cost_variance_amount"]),
        opportunity_amount=_dec(data["opportunity_amount"]),
        best_or_tied_count=data["best_or_tied_count"],
    )


@analytics_router.get("/coverage", response_model=BenchmarkCoverageResponse)
async def coverage(
    date_from: date | None = None,
    date_to: date | None = None,
    station_ids: list[uuid.UUID] | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
) -> BenchmarkCoverageResponse:
    _ensure(user, Permission.PURCHASE_BENCHMARKS_READ)
    stations = await _stations(AuthService(db), user, station_ids)
    data = await PurchaseBenchmarkAnalyticsService(db).coverage(
        organization_id=user.organization_id,
        station_ids=stations,
        date_from=date_from,
        date_to=date_to,
    )
    by_status = {
        k: {
            **v,
            "volume_liters": _dec(v["volume_liters"]),
            "value": _dec(v["value"]),
            "count_ratio": _dec(v["count_ratio"]),
            "volume_ratio": _dec(v["volume_ratio"]),
            "value_ratio": _dec(v["value_ratio"]),
        }
        for k, v in data["by_status"].items()
    }
    return BenchmarkCoverageResponse(
        total_groups=data["total_groups"],
        total_volume_liters=_dec(data["total_volume_liters"]) or "0",
        total_value=_dec(data["total_value"]) or "0",
        by_status=by_status,
    )


@analytics_router.get("/data-quality", response_model=BenchmarkDataQualityResponse)
async def data_quality(
    date_from: date | None = None,
    date_to: date | None = None,
    station_ids: list[uuid.UUID] | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
) -> BenchmarkDataQualityResponse:
    _ensure(user, Permission.PURCHASE_BENCHMARKS_READ)
    stations = await _stations(AuthService(db), user, station_ids)
    data = await PurchaseBenchmarkAnalyticsService(db).data_quality(
        organization_id=user.organization_id,
        station_ids=stations,
        date_from=date_from,
        date_to=date_to,
    )
    return BenchmarkDataQualityResponse(**data)


@analytics_router.get("/opportunities", response_model=list[BenchmarkOpportunityRow])
async def opportunities(
    date_from: date | None = None,
    date_to: date | None = None,
    station_ids: list[uuid.UUID] | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
) -> list[BenchmarkOpportunityRow]:
    _ensure(user, Permission.PURCHASE_BENCHMARKS_VIEW_OPPORTUNITY)
    stations = await _stations(AuthService(db), user, station_ids)
    rows = await PurchaseBenchmarkAnalyticsService(db).opportunities(
        organization_id=user.organization_id,
        station_ids=stations,
        date_from=date_from,
        date_to=date_to,
    )
    return [
        BenchmarkOpportunityRow(
            benchmark_item_id=r["benchmark_item_id"],
            purchase_invoice_id=r["purchase_invoice_id"],
            station_id=r["station_id"],
            canonical_product_id=r["canonical_product_id"],
            volume_liters=_dec(r["volume_liters"]) or "0",
            opportunity_amount=_dec(r["opportunity_amount"]),
            cost_variance_per_liter=_dec(r["cost_variance_per_liter"]),
            decision_result=r["decision_result"],
        )
        for r in rows
    ]


@analytics_router.get("/export/csv")
async def export_csv(
    date_from: date | None = None,
    date_to: date | None = None,
    station_ids: list[uuid.UUID] | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.PURCHASE_BENCHMARKS_EXPORT)
    stations = await _stations(AuthService(db), user, station_ids)
    include_opp = Permission.PURCHASE_BENCHMARKS_VIEW_OPPORTUNITY.value in user.permissions
    content = await PurchaseBenchmarkAnalyticsService(db).export_csv(
        organization_id=user.organization_id,
        station_ids=stations,
        date_from=date_from,
        date_to=date_to,
        include_opportunity=include_opp,
    )
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=purchase-benchmarks.csv"},
    )


@analytics_router.get("/export/pdf")
async def export_pdf(
    date_from: date | None = None,
    date_to: date | None = None,
    station_ids: list[uuid.UUID] | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.PURCHASE_BENCHMARKS_EXPORT)
    stations = await _stations(AuthService(db), user, station_ids)
    include_opp = Permission.PURCHASE_BENCHMARKS_VIEW_OPPORTUNITY.value in user.permissions
    summary = await PurchaseBenchmarkAnalyticsService(db).summary(
        organization_id=user.organization_id,
        station_ids=stations,
        date_from=date_from,
        date_to=date_to,
        include_opportunity=include_opp,
    )
    # PDF mínimo textual (sem dependência nova)
    lines = [
        "Purchase Benchmarks",
        f"Groups: {summary['purchase_group_count']}",
        f"Benchmarked: {summary['benchmarked_group_count']}",
        f"Volume: {summary['purchased_volume_liters']}",
        f"Variance: {summary['cost_variance_amount']}",
    ]
    if include_opp:
        lines.append(f"Opportunity: {summary['opportunity_amount']}")
    body = "\n".join(lines).encode("utf-8")
    return Response(
        content=body,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=purchase-benchmarks.pdf"},
    )


@analytics_router.get("/trend")
async def analytics_trend(
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.PURCHASE_BENCHMARKS_READ)
    return {"items": []}


@analytics_router.get("/by-station")
async def analytics_by_station(
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.PURCHASE_BENCHMARKS_READ)
    return {"items": []}


@analytics_router.get("/by-product")
async def analytics_by_product(
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.PURCHASE_BENCHMARKS_READ)
    return {"items": []}


@analytics_router.get("/by-distributor")
async def analytics_by_distributor(
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.PURCHASE_BENCHMARKS_READ)
    return {"items": []}
