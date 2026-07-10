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
from app.core.quote_comparison_enums import ComparisonRunStatus
from app.schemas.quote_comparisons import (
    ComparisonCostsResponse,
    ComparisonResultResponse,
    ComparisonRunListItem,
    ComparisonRunListResponse,
    ComparisonRunResponse,
    ComparisonScenarioInput,
    ComparisonScenarioResponse,
    ComparisonSummaryResponse,
    DistributorBrief,
    EligibilityReasonResponse,
    ReprocessComparisonRequest,
)
from app.services.auth_service import AuthService, AuthenticatedUser
from app.services.quote_comparison_service import QuoteComparisonService
from app.utils.comparison_export import build_comparison_csv, build_comparison_pdf

router = APIRouter(prefix="/quote-comparisons", tags=["quote-comparisons"])


def _ensure(user: AuthenticatedUser, permission: Permission) -> None:
    if permission.value not in user.permissions:
        raise AppError(
            "Você não possui permissão para executar esta ação.",
            status_code=403,
            code="FORBIDDEN",
        )


def _to_run_response(run, distributors: dict) -> ComparisonRunResponse:
    results: list[ComparisonResultResponse] = []
    for result in run.results:
        distributor_name = QuoteComparisonService.distributor_name_from_snapshot(result)
        if not distributor_name:
            distributor = distributors.get(result.distributor_id)
            distributor_name = (
                distributor.trade_name or distributor.corporate_name if distributor else str(result.distributor_id)
            )
        quote_number = None
        payment_term_name = None
        if isinstance(result.input_snapshot, dict):
            quote_number = result.input_snapshot.get("quote_number")
            payment_term_name = result.input_snapshot.get("payment_term_name_snapshot")
        results.append(
            ComparisonResultResponse(
                quote_id=result.quote_id,
                quote_item_id=result.quote_item_id,
                quote_number=quote_number,
                distributor=DistributorBrief(id=result.distributor_id, name=distributor_name),
                eligibility_status=result.eligibility_status,
                eligibility_reasons=[
                    EligibilityReasonResponse.model_validate(reason) for reason in result.eligibility_reasons
                ],
                costs=ComparisonCostsResponse(
                    raw_price_per_liter=result.raw_price_per_liter,
                    discount_per_liter=result.discount_per_liter,
                    rebate_per_liter=result.rebate_per_liter,
                    freight_per_liter=result.freight_per_liter,
                    other_cost_per_liter=result.other_cost_per_liter,
                    delivered_cost_per_liter=result.delivered_cost_per_liter,
                    delivered_total=result.delivered_total,
                    financial_days=result.financial_days,
                    annual_effective_rate=result.annual_effective_rate,
                    daily_rate=result.daily_rate,
                    financial_equivalent_cost_per_liter=result.financial_equivalent_cost_per_liter,
                    financial_equivalent_total=result.financial_equivalent_total,
                ),
                rank_position=result.rank_position,
                difference_per_liter=result.difference_per_liter,
                difference_total=result.difference_total,
                is_best_for_distributor=result.is_best_for_distributor,
                is_best_overall=result.is_best_overall,
                payment_term_name=payment_term_name,
                delivery_expected_at=result.delivery_expected_at,
                effective_valid_until=result.effective_valid_until,
                calculation_snapshot=result.calculation_snapshot or {},
            )
        )

    return ComparisonRunResponse(
        id=run.id,
        status=run.status,
        methodology_version=run.methodology_version,
        scenario=ComparisonScenarioResponse(
            station_id=run.station_id,
            product_id=run.product_id,
            requested_volume_liters=run.requested_volume_liters,
            comparison_datetime=run.comparison_datetime,
            required_delivery_at=run.required_delivery_at,
            ranking_mode=run.ranking_mode,
            ranking_scope=run.ranking_scope,
        ),
        summary=ComparisonSummaryResponse(
            eligible_count=run.eligible_count,
            warning_count=run.warning_count,
            ineligible_count=run.ineligible_count,
            distributor_count=run.distributor_count,
            best_cost_per_liter=run.best_cost_per_liter,
            highest_cost_per_liter=run.highest_cost_per_liter,
            average_cost_per_liter=run.average_cost_per_liter,
            spread_absolute=run.spread_absolute,
            spread_percent=run.spread_percent,
        ),
        results=results,
        calculation_hash=run.calculation_hash,
        processing_duration_ms=run.processing_duration_ms,
        reprocessed_from_run_id=run.reprocessed_from_run_id,
        input_snapshot=run.input_snapshot or {},
        created_at=run.created_at,
        created_by=run.created_by,
    )


@router.get("/methodology")
async def get_methodology(
    user: AuthenticatedUser = Depends(get_current_active_user),
) -> dict:
    _ensure(user, Permission.QUOTE_COMPARISONS_READ)
    return QuoteComparisonService.methodology()


@router.post("", response_model=ComparisonRunResponse, status_code=201)
async def run_quote_comparison(
    payload: ComparisonScenarioInput,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> ComparisonRunResponse:
    _ensure(user, Permission.QUOTE_COMPARISONS_RUN)
    auth = AuthService(db)
    try:
        await auth.ensure_station_access(user, payload.station_id)
    except AppError as exc:
        if exc.code == "STATION_ACCESS_DENIED":
            raise AppError(
                "Você não possui acesso ao posto informado.",
                status_code=403,
                code="COMPARISON_STATION_ACCESS_DENIED",
            ) from exc
        raise
    service = QuoteComparisonService(db)
    run = await service.run_comparison(
        organization_id=user.organization_id,
        station_id=payload.station_id,
        product_id=payload.product_id,
        requested_volume_liters=payload.requested_volume_liters,
        comparison_datetime=payload.comparison_datetime,
        required_delivery_at=payload.required_delivery_at,
        ranking_mode=payload.ranking_mode,
        ranking_scope=payload.ranking_scope,
        created_by=user.id,
    )
    await db.commit()
    distributors = await service.build_distributor_map(run)
    return _to_run_response(run, distributors)


@router.get("", response_model=ComparisonRunListResponse)
async def list_quote_comparisons(
    station_id: uuid.UUID | None = Query(default=None),
    product_id: uuid.UUID | None = Query(default=None),
    created_by: uuid.UUID | None = Query(default=None),
    ranking_mode: str | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> ComparisonRunListResponse:
    _ensure(user, Permission.QUOTE_COMPARISONS_READ)
    auth = AuthService(db)
    if station_id:
        await auth.ensure_station_access(user, station_id)
    allowed_station_ids = None
    if not user.has_all_stations_access:
        allowed_station_ids = [station.id for station in await auth.allowed_stations(user)]
    service = QuoteComparisonService(db)
    items, total = await service.list_runs(
        organization_id=user.organization_id,
        station_id=station_id,
        product_id=product_id,
        created_by=created_by,
        ranking_mode=ranking_mode,
        date_from=date_from,
        date_to=date_to,
        allowed_station_ids=allowed_station_ids,
        page=page,
        page_size=page_size,
    )
    return ComparisonRunListResponse(
        items=[ComparisonRunListItem.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{run_id}", response_model=ComparisonRunResponse)
async def get_quote_comparison(
    run_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> ComparisonRunResponse:
    _ensure(user, Permission.QUOTE_COMPARISONS_READ)
    service = QuoteComparisonService(db)
    run = await service.get_run(run_id, user.organization_id)
    auth = AuthService(db)
    await auth.ensure_station_access(user, run.station_id)
    if run.status != ComparisonRunStatus.COMPLETED:
        raise AppError(
            "A comparação ainda não foi concluída.",
            status_code=409,
            code="COMPARISON_NOT_COMPLETED",
        )
    distributors = await service.build_distributor_map(run)
    return _to_run_response(run, distributors)


@router.post("/{run_id}/reprocess", response_model=ComparisonRunResponse, status_code=201)
async def reprocess_quote_comparison(
    run_id: uuid.UUID,
    payload: ReprocessComparisonRequest,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> ComparisonRunResponse:
    _ensure(user, Permission.QUOTE_COMPARISONS_REPROCESS)
    service = QuoteComparisonService(db)
    original = await service.get_run(run_id, user.organization_id)
    auth = AuthService(db)
    await auth.ensure_station_access(user, original.station_id)
    run = await service.reprocess(
        run_id=run_id,
        organization_id=user.organization_id,
        created_by=user.id,
        comparison_datetime=payload.comparison_datetime,
        ranking_mode=payload.ranking_mode,
        ranking_scope=payload.ranking_scope,
        required_delivery_at=payload.required_delivery_at,
        requested_volume_liters=payload.requested_volume_liters,
    )
    await db.commit()
    distributors = await service.build_distributor_map(run)
    return _to_run_response(run, distributors)


@router.get("/{run_id}/export/pdf")
async def export_quote_comparison_pdf(
    run_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    _ensure(user, Permission.QUOTE_COMPARISONS_EXPORT)
    service = QuoteComparisonService(db)
    run = await service.get_run(run_id, user.organization_id)
    auth = AuthService(db)
    await auth.ensure_station_access(user, run.station_id)
    content = build_comparison_pdf(run, generated_by=user.email)
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="comparacao-{run_id}.pdf"'},
    )


@router.get("/{run_id}/export/csv")
async def export_quote_comparison_csv(
    run_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    _ensure(user, Permission.QUOTE_COMPARISONS_EXPORT)
    service = QuoteComparisonService(db)
    run = await service.get_run(run_id, user.organization_id)
    auth = AuthService(db)
    await auth.ensure_station_access(user, run.station_id)
    content = build_comparison_csv(run)
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="comparacao-{run_id}.csv"'},
    )
