from __future__ import annotations

import csv
import io
import uuid
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.core.exceptions import AppError
from app.core.permissions import Permission
from app.schemas.fuel_sales_analytics import (
    FuelSalesByProductRow,
    FuelSalesByStationRow,
    FuelSalesDataQualityResponse,
    FuelSalesFreshnessResponse,
    FuelSalesSummaryResponse,
    FuelSalesTrendPoint,
)
from app.services.auth_service import AuthService, AuthenticatedUser
from app.services.fuel_sales_analytics_service import FuelSalesAnalyticsService

router = APIRouter(prefix="/analytics/fuel-sales", tags=["fuel-sales-analytics"])


def _ensure(user: AuthenticatedUser, permission: Permission) -> None:
    if permission.value not in user.permissions:
        raise AppError("Você não possui permissão para executar esta ação.", status_code=403, code="FORBIDDEN")


def _dec(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return format(value, "f")


async def _resolve_station_ids(
    auth: AuthService,
    user: AuthenticatedUser,
    station_ids: list[uuid.UUID] | None,
) -> list[uuid.UUID]:
    allowed = await auth.allowed_stations(user)
    allowed_ids = {s.id for s in allowed}
    if user.has_all_stations_access:
        if station_ids:
            return station_ids
        return [s.id for s in allowed]
    if station_ids:
        for sid in station_ids:
            if sid not in allowed_ids:
                raise AppError("Posto fora do escopo.", status_code=403, code="FORBIDDEN")
        return station_ids
    return list(allowed_ids)


@router.get("/summary", response_model=FuelSalesSummaryResponse)
async def fuel_sales_summary(
    date_from: date = Query(...),
    date_to: date = Query(...),
    station_ids: list[uuid.UUID] | None = Query(default=None),
    product_ids: list[uuid.UUID] | None = Query(default=None),
    payment_method_groups: list[str] | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
) -> FuelSalesSummaryResponse:
    _ensure(user, Permission.FUEL_SALES_ANALYTICS_READ)
    auth = AuthService(db)
    include_margin = Permission.FUEL_SALES_ANALYTICS_VIEW_MARGIN.value in user.permissions
    scoped_stations = await _resolve_station_ids(auth, user, station_ids)
    data = await FuelSalesAnalyticsService(db).summary(
        organization_id=user.organization_id,
        station_ids=scoped_stations,
        product_ids=product_ids,
        date_from=date_from,
        date_to=date_to,
        payment_method_groups=payment_method_groups,
        include_margin=include_margin,
    )
    return FuelSalesSummaryResponse(
        net_volume_liters=_dec(data["net_volume_liters"]) or "0",
        net_sales_amount=_dec(data["net_sales_amount"]) or "0",
        realized_price_per_liter=_dec(data["realized_price_per_liter"]),
        cost_coverage_percent=_dec(data["cost_coverage_percent"]),
        item_count=data["item_count"],
        total_cost_amount=_dec(data.get("total_cost_amount")),
        gross_margin_amount=_dec(data.get("gross_margin_amount")),
        gross_margin_per_liter=_dec(data.get("gross_margin_per_liter")),
        gross_margin_percent=_dec(data.get("gross_margin_percent")),
    )


@router.get("/trend", response_model=list[FuelSalesTrendPoint])
async def fuel_sales_trend(
    date_from: date = Query(...),
    date_to: date = Query(...),
    station_ids: list[uuid.UUID] | None = Query(default=None),
    product_ids: list[uuid.UUID] | None = Query(default=None),
    payment_method_groups: list[str] | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
) -> list[FuelSalesTrendPoint]:
    _ensure(user, Permission.FUEL_SALES_ANALYTICS_READ)
    auth = AuthService(db)
    include_margin = Permission.FUEL_SALES_ANALYTICS_VIEW_MARGIN.value in user.permissions
    scoped_stations = await _resolve_station_ids(auth, user, station_ids)
    points = await FuelSalesAnalyticsService(db).trend(
        organization_id=user.organization_id,
        station_ids=scoped_stations,
        product_ids=product_ids,
        date_from=date_from,
        date_to=date_to,
        payment_method_groups=payment_method_groups,
        include_margin=include_margin,
    )
    return [
        FuelSalesTrendPoint(
            business_date=p["business_date"],
            net_volume_liters=_dec(p["net_volume_liters"]) or "0",
            net_sales_amount=_dec(p["net_sales_amount"]) or "0",
            realized_price_per_liter=_dec(p["realized_price_per_liter"]),
            gross_margin_amount=_dec(p.get("gross_margin_amount")),
            gross_margin_per_liter=_dec(p.get("gross_margin_per_liter")),
        )
        for p in points
    ]


@router.get("/by-station", response_model=list[FuelSalesByStationRow])
async def fuel_sales_by_station(
    date_from: date = Query(...),
    date_to: date = Query(...),
    station_ids: list[uuid.UUID] | None = Query(default=None),
    product_ids: list[uuid.UUID] | None = Query(default=None),
    payment_method_groups: list[str] | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
) -> list[FuelSalesByStationRow]:
    _ensure(user, Permission.FUEL_SALES_ANALYTICS_READ)
    auth = AuthService(db)
    scoped_stations = await _resolve_station_ids(auth, user, station_ids)
    rows = await FuelSalesAnalyticsService(db).by_station(
        organization_id=user.organization_id,
        station_ids=scoped_stations,
        product_ids=product_ids,
        date_from=date_from,
        date_to=date_to,
        payment_method_groups=payment_method_groups,
    )
    return [
        FuelSalesByStationRow(
            station_id=r["station_id"],
            station_name=r["station_name"],
            net_volume_liters=_dec(r["net_volume_liters"]) or "0",
            net_sales_amount=_dec(r["net_sales_amount"]) or "0",
            realized_price_per_liter=_dec(r["realized_price_per_liter"]),
            participation_percent=_dec(r["participation_percent"]),
        )
        for r in rows
    ]


@router.get("/by-product", response_model=list[FuelSalesByProductRow])
async def fuel_sales_by_product(
    date_from: date = Query(...),
    date_to: date = Query(...),
    station_ids: list[uuid.UUID] | None = Query(default=None),
    product_ids: list[uuid.UUID] | None = Query(default=None),
    payment_method_groups: list[str] | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
) -> list[FuelSalesByProductRow]:
    _ensure(user, Permission.FUEL_SALES_ANALYTICS_READ)
    auth = AuthService(db)
    include_margin = Permission.FUEL_SALES_ANALYTICS_VIEW_MARGIN.value in user.permissions
    scoped_stations = await _resolve_station_ids(auth, user, station_ids)
    rows = await FuelSalesAnalyticsService(db).by_product(
        organization_id=user.organization_id,
        station_ids=scoped_stations,
        product_ids=product_ids,
        date_from=date_from,
        date_to=date_to,
        payment_method_groups=payment_method_groups,
        include_margin=include_margin,
    )
    return [
        FuelSalesByProductRow(
            product_id=r["product_id"],
            product_name=r["product_name"],
            net_volume_liters=_dec(r["net_volume_liters"]) or "0",
            net_sales_amount=_dec(r["net_sales_amount"]) or "0",
            realized_price_per_liter=_dec(r["realized_price_per_liter"]),
            cost_coverage_percent=_dec(r["cost_coverage_percent"]),
            total_cost_amount=_dec(r.get("total_cost_amount")),
            gross_margin_amount=_dec(r.get("gross_margin_amount")),
            gross_margin_per_liter=_dec(r.get("gross_margin_per_liter")),
            gross_margin_percent=_dec(r.get("gross_margin_percent")),
        )
        for r in rows
    ]


@router.get("/margins")
async def fuel_sales_margins(
    date_from: date = Query(...),
    date_to: date = Query(...),
    station_ids: list[uuid.UUID] | None = Query(default=None),
    product_ids: list[uuid.UUID] | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
) -> dict:
    _ensure(user, Permission.FUEL_SALES_ANALYTICS_VIEW_MARGIN)
    auth = AuthService(db)
    scoped_stations = await _resolve_station_ids(auth, user, station_ids)
    data = await FuelSalesAnalyticsService(db).summary(
        organization_id=user.organization_id,
        station_ids=scoped_stations,
        product_ids=product_ids,
        date_from=date_from,
        date_to=date_to,
        payment_method_groups=None,
        include_margin=True,
    )
    return {
        "total_cost_amount": _dec(data.get("total_cost_amount")),
        "gross_margin_amount": _dec(data.get("gross_margin_amount")),
        "gross_margin_per_liter": _dec(data.get("gross_margin_per_liter")),
        "gross_margin_percent": _dec(data.get("gross_margin_percent")),
        "cost_coverage_percent": _dec(data["cost_coverage_percent"]),
    }


@router.get("/data-quality", response_model=FuelSalesDataQualityResponse)
async def fuel_sales_data_quality(
    date_from: date = Query(...),
    date_to: date = Query(...),
    station_ids: list[uuid.UUID] | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
) -> FuelSalesDataQualityResponse:
    _ensure(user, Permission.FUEL_SALES_DATA_QUALITY_READ)
    auth = AuthService(db)
    scoped_stations = await _resolve_station_ids(auth, user, station_ids)
    data = await FuelSalesAnalyticsService(db).data_quality(
        organization_id=user.organization_id,
        station_ids=scoped_stations,
        date_from=date_from,
        date_to=date_to,
    )
    return FuelSalesDataQualityResponse(
        unmapped_item_count=data["unmapped_item_count"],
        unmapped_volume_liters=_dec(data["unmapped_volume_liters"]) or "0",
        missing_cost_item_count=data["missing_cost_item_count"],
        missing_cost_volume_liters=_dec(data["missing_cost_volume_liters"]) or "0",
        quarantined_item_count=data["quarantined_item_count"],
        pending_payment_methods=data["pending_payment_methods"],
    )


@router.get("/freshness", response_model=FuelSalesFreshnessResponse)
async def fuel_sales_freshness(
    source_id: uuid.UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
) -> FuelSalesFreshnessResponse:
    _ensure(user, Permission.FUEL_SALES_ANALYTICS_READ)
    data = await FuelSalesAnalyticsService(db).freshness(
        organization_id=user.organization_id,
        source_id=source_id,
    )
    return FuelSalesFreshnessResponse(
        status=str(data["status"]),
        security_status=data.get("security_status"),
        last_completed_run_at=data.get("last_completed_run_at"),
        source_upper_bound=data.get("source_upper_bound"),
    )


@router.get("/export/csv")
async def fuel_sales_export_csv(
    date_from: date = Query(...),
    date_to: date = Query(...),
    station_ids: list[uuid.UUID] | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
) -> Response:
    _ensure(user, Permission.FUEL_SALES_ANALYTICS_EXPORT)
    auth = AuthService(db)
    scoped_stations = await _resolve_station_ids(auth, user, station_ids)
    rows = await FuelSalesAnalyticsService(db).by_product(
        organization_id=user.organization_id,
        station_ids=scoped_stations,
        product_ids=None,
        date_from=date_from,
        date_to=date_to,
        payment_method_groups=None,
        include_margin=Permission.FUEL_SALES_ANALYTICS_VIEW_MARGIN.value in user.permissions,
    )
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        ["produto", "volume_l", "receita", "preco_medio", "margem", "margem_por_l", "margem_pct", "cobertura_custo"]
    )
    for row in rows:
        writer.writerow(
            [
                row["product_name"],
                _dec(row["net_volume_liters"]),
                _dec(row["net_sales_amount"]),
                _dec(row["realized_price_per_liter"]),
                _dec(row.get("gross_margin_amount")),
                _dec(row.get("gross_margin_per_liter")),
                _dec(row.get("gross_margin_percent")),
                _dec(row["cost_coverage_percent"]),
            ]
        )
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="fuel-sales-by-product.csv"'},
    )
