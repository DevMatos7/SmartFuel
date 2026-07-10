from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.fuel_sales_enums import FuelSalesFreshnessStatus, MetricEligibilityStatus, MetricExclusionReason
from app.core.fuel_sales_enums import MarginStatus
from app.models.erp_integration import ErpDataset, ErpSource, ErpSyncRun
from app.models.fuel_sales import ErpPaymentMethod, FuelSalesDailyMetric, FuelSalesFact
from app.models.product import Product
from app.models.station import Station
from app.services.fuel_sales_calculation_service import compute_realized_price_per_liter


class FuelSalesAnalyticsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def summary(
        self,
        *,
        organization_id: uuid.UUID,
        station_ids: list[uuid.UUID],
        product_ids: list[uuid.UUID] | None,
        date_from: date,
        date_to: date,
        payment_method_groups: list[str] | None,
        include_margin: bool,
    ) -> dict:
        metrics = await self._load_metrics(
            organization_id=organization_id,
            station_ids=station_ids,
            product_ids=product_ids,
            date_from=date_from,
            date_to=date_to,
            payment_method_groups=payment_method_groups,
        )
        net_volume = sum((m.net_volume_liters for m in metrics), Decimal("0"))
        net_sales = sum((m.net_sales_amount for m in metrics), Decimal("0"))
        total_cost = sum((m.total_cost_amount or Decimal("0") for m in metrics if m.total_cost_amount is not None), Decimal("0"))
        cost_volume = sum((m.cost_available_volume_liters for m in metrics), Decimal("0"))
        realized_price = compute_realized_price_per_liter(net_sales, net_volume)
        gross_margin = net_sales - total_cost if cost_volume > 0 else None
        margin_per_liter = gross_margin / cost_volume if gross_margin is not None and cost_volume > 0 else None
        margin_percent = (gross_margin / net_sales * Decimal("100")) if gross_margin is not None and net_sales != 0 else None
        cost_coverage = (cost_volume / net_volume * Decimal("100")) if net_volume > 0 else None

        payload = {
            "net_volume_liters": net_volume,
            "net_sales_amount": net_sales,
            "realized_price_per_liter": realized_price,
            "cost_coverage_percent": cost_coverage,
            "item_count": sum(m.sales_item_count for m in metrics),
        }
        if include_margin:
            payload.update(
                {
                    "total_cost_amount": total_cost if cost_volume > 0 else None,
                    "gross_margin_amount": gross_margin,
                    "gross_margin_per_liter": margin_per_liter,
                    "gross_margin_percent": margin_percent,
                }
            )
        return payload

    async def trend(
        self,
        *,
        organization_id: uuid.UUID,
        station_ids: list[uuid.UUID],
        product_ids: list[uuid.UUID] | None,
        date_from: date,
        date_to: date,
        payment_method_groups: list[str] | None,
        include_margin: bool,
    ) -> list[dict]:
        metrics = await self._load_metrics(
            organization_id=organization_id,
            station_ids=station_ids,
            product_ids=product_ids,
            date_from=date_from,
            date_to=date_to,
            payment_method_groups=payment_method_groups,
        )
        by_date: dict[date, list[FuelSalesDailyMetric]] = {}
        for metric in metrics:
            by_date.setdefault(metric.business_date, []).append(metric)

        points: list[dict] = []
        for business_date in sorted(by_date):
            rows = by_date[business_date]
            net_volume = sum((r.net_volume_liters for r in rows), Decimal("0"))
            net_sales = sum((r.net_sales_amount for r in rows), Decimal("0"))
            point = {
                "business_date": business_date.isoformat(),
                "net_volume_liters": net_volume,
                "net_sales_amount": net_sales,
                "realized_price_per_liter": compute_realized_price_per_liter(net_sales, net_volume),
            }
            if include_margin:
                total_cost = sum((r.total_cost_amount or Decimal("0") for r in rows if r.total_cost_amount), Decimal("0"))
                cost_volume = sum((r.cost_available_volume_liters for r in rows), Decimal("0"))
                gross_margin = net_sales - total_cost if cost_volume > 0 else None
                point["gross_margin_amount"] = gross_margin
                point["gross_margin_per_liter"] = (
                    gross_margin / cost_volume if gross_margin is not None and cost_volume > 0 else None
                )
            points.append(point)
        return points

    async def by_station(
        self,
        *,
        organization_id: uuid.UUID,
        station_ids: list[uuid.UUID],
        product_ids: list[uuid.UUID] | None,
        date_from: date,
        date_to: date,
        payment_method_groups: list[str] | None,
    ) -> list[dict]:
        metrics = await self._load_metrics(
            organization_id=organization_id,
            station_ids=station_ids,
            product_ids=product_ids,
            date_from=date_from,
            date_to=date_to,
            payment_method_groups=payment_method_groups,
        )
        stations = await self._load_station_names({m.station_id for m in metrics})
        grouped: dict[uuid.UUID, list[FuelSalesDailyMetric]] = {}
        for metric in metrics:
            grouped.setdefault(metric.station_id, []).append(metric)

        total_volume = sum((m.net_volume_liters for m in metrics), Decimal("0"))
        rows: list[dict] = []
        for station_id, items in grouped.items():
            net_volume = sum((i.net_volume_liters for i in items), Decimal("0"))
            net_sales = sum((i.net_sales_amount for i in items), Decimal("0"))
            rows.append(
                {
                    "station_id": str(station_id),
                    "station_name": stations.get(station_id, str(station_id)),
                    "net_volume_liters": net_volume,
                    "net_sales_amount": net_sales,
                    "realized_price_per_liter": compute_realized_price_per_liter(net_sales, net_volume),
                    "participation_percent": (net_volume / total_volume * Decimal("100")) if total_volume > 0 else None,
                }
            )
        return sorted(rows, key=lambda r: r["net_volume_liters"], reverse=True)

    async def by_product(
        self,
        *,
        organization_id: uuid.UUID,
        station_ids: list[uuid.UUID],
        product_ids: list[uuid.UUID] | None,
        date_from: date,
        date_to: date,
        payment_method_groups: list[str] | None,
        include_margin: bool,
    ) -> list[dict]:
        metrics = await self._load_metrics(
            organization_id=organization_id,
            station_ids=station_ids,
            product_ids=product_ids,
            date_from=date_from,
            date_to=date_to,
            payment_method_groups=payment_method_groups,
        )
        products = await self._load_product_names({m.canonical_product_id for m in metrics})
        grouped: dict[uuid.UUID, list[FuelSalesDailyMetric]] = {}
        for metric in metrics:
            grouped.setdefault(metric.canonical_product_id, []).append(metric)

        rows: list[dict] = []
        for product_id, items in grouped.items():
            net_volume = sum((i.net_volume_liters for i in items), Decimal("0"))
            net_sales = sum((i.net_sales_amount for i in items), Decimal("0"))
            total_cost = sum((i.total_cost_amount or Decimal("0") for i in items if i.total_cost_amount), Decimal("0"))
            cost_volume = sum((i.cost_available_volume_liters for i in items), Decimal("0"))
            row = {
                "product_id": str(product_id),
                "product_name": products.get(product_id, str(product_id)),
                "net_volume_liters": net_volume,
                "net_sales_amount": net_sales,
                "realized_price_per_liter": compute_realized_price_per_liter(net_sales, net_volume),
                "cost_coverage_percent": (cost_volume / net_volume * Decimal("100")) if net_volume > 0 else None,
            }
            if include_margin:
                gross_margin = net_sales - total_cost if cost_volume > 0 else None
                row.update(
                    {
                        "total_cost_amount": total_cost if cost_volume > 0 else None,
                        "gross_margin_amount": gross_margin,
                        "gross_margin_per_liter": (
                            gross_margin / cost_volume if gross_margin is not None and cost_volume > 0 else None
                        ),
                        "gross_margin_percent": (
                            gross_margin / net_sales * Decimal("100")
                            if gross_margin is not None and net_sales != 0
                            else None
                        ),
                    }
                )
            rows.append(row)
        return sorted(rows, key=lambda r: r["net_volume_liters"], reverse=True)

    async def data_quality(
        self,
        *,
        organization_id: uuid.UUID,
        station_ids: list[uuid.UUID],
        date_from: date,
        date_to: date,
    ) -> dict:
        facts_query = select(FuelSalesFact).where(
            FuelSalesFact.organization_id == organization_id,
            FuelSalesFact.station_id.in_(station_ids),
            FuelSalesFact.business_date >= date_from,
            FuelSalesFact.business_date <= date_to,
            FuelSalesFact.is_cancelled.is_(False),
        )
        result = await self.db.execute(facts_query)
        facts = list(result.scalars().all())

        unmapped = [f for f in facts if MetricExclusionReason.UNMAPPED_PRODUCT.value in (f.metric_exclusion_reasons or [])]
        missing_cost = [f for f in facts if f.margin_status == MarginStatus.UNAVAILABLE and f.metric_eligibility_status != MetricEligibilityStatus.EXCLUDED]
        quarantined = [f for f in facts if f.metric_eligibility_status == MetricEligibilityStatus.EXCLUDED]

        pm_pending = await self.db.execute(
            select(func.count()).select_from(ErpPaymentMethod).where(
                ErpPaymentMethod.organization_id == organization_id,
                ErpPaymentMethod.station_id.in_(station_ids),
                ErpPaymentMethod.mapping_status == "PENDING",
            )
        )

        return {
            "unmapped_item_count": len(unmapped),
            "unmapped_volume_liters": sum((f.volume_liters or Decimal("0") for f in unmapped), Decimal("0")),
            "missing_cost_item_count": len(missing_cost),
            "missing_cost_volume_liters": sum((f.volume_liters or Decimal("0") for f in missing_cost), Decimal("0")),
            "quarantined_item_count": len(quarantined),
            "pending_payment_methods": int(pm_pending.scalar_one()),
        }

    async def freshness(self, *, organization_id: uuid.UUID, source_id: uuid.UUID | None) -> dict:
        source_query = select(ErpSource).where(ErpSource.organization_id == organization_id)
        if source_id:
            source_query = source_query.where(ErpSource.id == source_id)
        source_result = await self.db.execute(source_query.limit(1))
        source = source_result.scalar_one_or_none()
        if source is None:
            return {"status": FuelSalesFreshnessStatus.UNAVAILABLE}

        run_result = await self.db.execute(
            select(ErpSyncRun)
            .join(ErpDataset, ErpDataset.id == ErpSyncRun.erp_dataset_id)
            .where(
                ErpSyncRun.erp_source_id == source.id,
                ErpSyncRun.status == "COMPLETED",
                ErpDataset.code == "FUEL_SALES_ITEMS",
            )
            .order_by(ErpSyncRun.finished_at.desc())
            .limit(1)
        )
        last_run = run_result.scalar_one_or_none()
        status = FuelSalesFreshnessStatus.UNAVAILABLE
        if source.security_status == "UNSAFE":
            status = FuelSalesFreshnessStatus.UNSAFE_SOURCE
        elif last_run and last_run.finished_at:
            delay_minutes = int((datetime.now(last_run.finished_at.tzinfo) - last_run.finished_at).total_seconds() / 60)
            if delay_minutes <= 120:
                status = FuelSalesFreshnessStatus.UPDATED
            elif delay_minutes <= 720:
                status = FuelSalesFreshnessStatus.DELAYED
            else:
                status = FuelSalesFreshnessStatus.STALE

        return {
            "status": status,
            "security_status": source.security_status,
            "last_completed_run_at": last_run.finished_at.isoformat() if last_run and last_run.finished_at else None,
            "source_upper_bound": last_run.source_upper_bound.isoformat() if last_run and last_run.source_upper_bound else None,
        }

    async def _load_metrics(
        self,
        *,
        organization_id: uuid.UUID,
        station_ids: list[uuid.UUID],
        product_ids: list[uuid.UUID] | None,
        date_from: date,
        date_to: date,
        payment_method_groups: list[str] | None,
    ) -> list[FuelSalesDailyMetric]:
        query = select(FuelSalesDailyMetric).where(
            FuelSalesDailyMetric.organization_id == organization_id,
            FuelSalesDailyMetric.station_id.in_(station_ids),
            FuelSalesDailyMetric.business_date >= date_from,
            FuelSalesDailyMetric.business_date <= date_to,
        )
        if product_ids:
            query = query.where(FuelSalesDailyMetric.canonical_product_id.in_(product_ids))
        if payment_method_groups:
            query = query.where(FuelSalesDailyMetric.payment_method_group.in_(payment_method_groups))
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def _load_station_names(self, station_ids: set[uuid.UUID]) -> dict[uuid.UUID, str]:
        if not station_ids:
            return {}
        result = await self.db.execute(select(Station).where(Station.id.in_(station_ids)))
        return {s.id: s.trade_name or s.corporate_name for s in result.scalars().all()}

    async def _load_product_names(self, product_ids: set[uuid.UUID]) -> dict[uuid.UUID, str]:
        if not product_ids:
            return {}
        result = await self.db.execute(select(Product).where(Product.id.in_(product_ids)))
        return {p.id: p.name for p in result.scalars().all()}
