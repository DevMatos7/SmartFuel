from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.fuel_sales_enums import FuelSalesFreshnessStatus, MetricEligibilityStatus, MetricExclusionReason
from app.core.fuel_sales_enums import MarginStatus
from app.models.erp_integration import ErpDataset, ErpSource, ErpSyncRun
from app.models.erp_product import ErpProduct
from app.models.fuel_sales import ErpPaymentMethod, FuelRetailPriceSnapshot, FuelSalesDailyMetric, FuelSalesFact
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
        pending_cfop = [
            f
            for f in facts
            if MetricExclusionReason.PENDING_CFOP_CLASSIFICATION.value in (f.metric_exclusion_reasons or [])
        ]

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
            "pending_cfop_item_count": len(pending_cfop),
            "pending_cfop_volume_liters": sum((f.volume_liters or Decimal("0") for f in pending_cfop), Decimal("0")),
            "pending_payment_methods": int(pm_pending.scalar_one()),
        }

    async def list_unmapped(
        self,
        *,
        organization_id: uuid.UUID,
        station_ids: list[uuid.UUID],
        date_from: date,
        date_to: date,
        limit: int = 100,
    ) -> list[dict]:
        facts = await self._load_quality_facts(
            organization_id=organization_id,
            station_ids=station_ids,
            date_from=date_from,
            date_to=date_to,
        )
        unmapped = [
            f
            for f in facts
            if MetricExclusionReason.UNMAPPED_PRODUCT.value in (f.metric_exclusion_reasons or [])
        ]
        grouped: dict[uuid.UUID, list[FuelSalesFact]] = {}
        for fact in unmapped:
            grouped.setdefault(fact.erp_product_id, []).append(fact)

        erp_ids = set(grouped.keys())
        erp_products = await self._load_erp_products(erp_ids)
        rows: list[dict] = []
        for erp_product_id, items in grouped.items():
            erp_product = erp_products.get(erp_product_id)
            volume = sum((i.volume_liters or Decimal("0") for i in items), Decimal("0"))
            rows.append(
                {
                    "erp_product_id": str(erp_product_id),
                    "erp_product_code": erp_product.erp_product_code if erp_product else None,
                    "erp_description": erp_product.erp_description if erp_product else str(erp_product_id),
                    "item_count": len(items),
                    "volume_liters": volume,
                    "net_amount": sum((i.net_amount for i in items), Decimal("0")),
                }
            )
        return sorted(rows, key=lambda r: r["volume_liters"], reverse=True)[:limit]

    async def list_missing_cost(
        self,
        *,
        organization_id: uuid.UUID,
        station_ids: list[uuid.UUID],
        date_from: date,
        date_to: date,
        limit: int = 100,
    ) -> list[dict]:
        facts = await self._load_quality_facts(
            organization_id=organization_id,
            station_ids=station_ids,
            date_from=date_from,
            date_to=date_to,
        )
        missing = [
            f
            for f in facts
            if f.margin_status == MarginStatus.UNAVAILABLE
            and f.metric_eligibility_status != MetricEligibilityStatus.EXCLUDED
        ]
        grouped: dict[uuid.UUID | None, list[FuelSalesFact]] = {}
        for fact in missing:
            grouped.setdefault(fact.canonical_product_id, []).append(fact)

        product_names = await self._load_product_names({pid for pid in grouped if pid is not None})
        rows: list[dict] = []
        for product_id, items in grouped.items():
            volume = sum((i.volume_liters or Decimal("0") for i in items), Decimal("0"))
            rows.append(
                {
                    "product_id": str(product_id) if product_id else None,
                    "product_name": product_names.get(product_id, "Sem produto canônico") if product_id else "Sem produto canônico",
                    "item_count": len(items),
                    "volume_liters": volume,
                    "net_amount": sum((i.net_amount for i in items), Decimal("0")),
                }
            )
        return sorted(rows, key=lambda r: r["volume_liters"], reverse=True)[:limit]

    async def list_quarantined(
        self,
        *,
        organization_id: uuid.UUID,
        station_ids: list[uuid.UUID],
        date_from: date,
        date_to: date,
        limit: int = 100,
    ) -> list[dict]:
        facts = await self._load_quality_facts(
            organization_id=organization_id,
            station_ids=station_ids,
            date_from=date_from,
            date_to=date_to,
        )
        quarantined = [f for f in facts if f.metric_eligibility_status == MetricEligibilityStatus.EXCLUDED]
        reason_counts: dict[str, int] = {}
        for fact in quarantined:
            for reason in fact.metric_exclusion_reasons or ["UNKNOWN"]:
                reason_counts[reason] = reason_counts.get(reason, 0) + 1
        rows = [
            {"reason": reason, "item_count": count}
            for reason, count in sorted(reason_counts.items(), key=lambda item: item[1], reverse=True)
        ]
        return rows[:limit]

    async def price_variance(
        self,
        *,
        organization_id: uuid.UUID,
        station_ids: list[uuid.UUID],
        date_from: date,
        date_to: date,
    ) -> list[dict]:
        metrics = await self._load_metrics(
            organization_id=organization_id,
            station_ids=station_ids,
            product_ids=None,
            date_from=date_from,
            date_to=date_to,
            payment_method_groups=None,
        )
        grouped: dict[tuple[uuid.UUID, str | None], list[FuelSalesDailyMetric]] = {}
        for metric in metrics:
            if metric.net_volume_liters <= 0:
                continue
            key = (metric.canonical_product_id, metric.payment_method_group)
            grouped.setdefault(key, []).append(metric)

        product_ids = {key[0] for key in grouped}
        product_names = await self._load_product_names(product_ids)
        prices = await self._load_current_retail_prices(organization_id, station_ids, product_ids)
        rows: list[dict] = []
        for (product_id, payment_group), items in grouped.items():
            net_volume = sum((m.net_volume_liters for m in items), Decimal("0"))
            net_sales = sum((m.net_sales_amount for m in items), Decimal("0"))
            realized = compute_realized_price_per_liter(net_sales, net_volume)
            registered = prices.get((product_id, payment_group))
            variance = None
            variance_percent = None
            if realized is not None and registered is not None:
                variance = realized - registered
                variance_percent = (variance / registered * Decimal("100")) if registered != 0 else None
            rows.append(
                {
                    "product_id": str(product_id),
                    "product_name": product_names.get(product_id, str(product_id)),
                    "payment_method_group": payment_group,
                    "net_volume_liters": net_volume,
                    "realized_price_per_liter": realized,
                    "registered_price_per_liter": registered,
                    "variance_per_liter": variance,
                    "variance_percent": variance_percent,
                }
            )
        return sorted(
            rows,
            key=lambda r: abs(r["variance_per_liter"] or Decimal("0")),
            reverse=True,
        )

    async def current_retail_prices(
        self,
        *,
        organization_id: uuid.UUID,
        station_ids: list[uuid.UUID],
        product_ids: list[uuid.UUID] | None,
    ) -> list[dict]:
        query = select(FuelRetailPriceSnapshot).where(
            FuelRetailPriceSnapshot.organization_id == organization_id,
            FuelRetailPriceSnapshot.station_id.in_(station_ids),
            FuelRetailPriceSnapshot.source_active.is_(True),
        )
        if product_ids:
            query = query.where(FuelRetailPriceSnapshot.canonical_product_id.in_(product_ids))
        result = await self.db.execute(query.order_by(FuelRetailPriceSnapshot.observed_at.desc()))
        snapshots = list(result.scalars().all())

        station_names = await self._load_station_names({s.station_id for s in snapshots})
        product_names = await self._load_product_names(
            {s.canonical_product_id for s in snapshots if s.canonical_product_id}
        )
        pm_ids = {s.erp_payment_method_id for s in snapshots}
        pm_names = await self._load_payment_method_names(pm_ids)

        rows: list[dict] = []
        seen: set[tuple] = set()
        for snapshot in snapshots:
            key = (snapshot.station_id, snapshot.erp_product_id, snapshot.erp_payment_method_id)
            if key in seen:
                continue
            seen.add(key)
            rows.append(
                {
                    "station_id": str(snapshot.station_id),
                    "station_name": station_names.get(snapshot.station_id, str(snapshot.station_id)),
                    "product_id": str(snapshot.canonical_product_id) if snapshot.canonical_product_id else None,
                    "product_name": (
                        product_names.get(snapshot.canonical_product_id, "Sem mapeamento")
                        if snapshot.canonical_product_id
                        else "Sem mapeamento"
                    ),
                    "payment_method_group": snapshot.payment_method_group,
                    "payment_method_name": pm_names.get(snapshot.erp_payment_method_id),
                    "price_per_liter": snapshot.price_per_liter,
                    "observed_at": snapshot.observed_at.isoformat(),
                }
            )
        return rows

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

    async def _load_quality_facts(
        self,
        *,
        organization_id: uuid.UUID,
        station_ids: list[uuid.UUID],
        date_from: date,
        date_to: date,
    ) -> list[FuelSalesFact]:
        result = await self.db.execute(
            select(FuelSalesFact).where(
                FuelSalesFact.organization_id == organization_id,
                FuelSalesFact.station_id.in_(station_ids),
                FuelSalesFact.business_date >= date_from,
                FuelSalesFact.business_date <= date_to,
                FuelSalesFact.is_cancelled.is_(False),
            )
        )
        return list(result.scalars().all())

    async def _load_erp_products(self, erp_product_ids: set[uuid.UUID]) -> dict[uuid.UUID, ErpProduct]:
        if not erp_product_ids:
            return {}
        result = await self.db.execute(select(ErpProduct).where(ErpProduct.id.in_(erp_product_ids)))
        return {p.id: p for p in result.scalars().all()}

    async def _load_payment_method_names(self, pm_ids: set[uuid.UUID]) -> dict[uuid.UUID, str]:
        if not pm_ids:
            return {}
        result = await self.db.execute(select(ErpPaymentMethod).where(ErpPaymentMethod.id.in_(pm_ids)))
        return {p.id: p.source_name for p in result.scalars().all()}

    async def _load_current_retail_prices(
        self,
        organization_id: uuid.UUID,
        station_ids: list[uuid.UUID],
        product_ids: set[uuid.UUID],
    ) -> dict[tuple[uuid.UUID, str | None], Decimal]:
        if not product_ids:
            return {}
        result = await self.db.execute(
            select(FuelRetailPriceSnapshot).where(
                FuelRetailPriceSnapshot.organization_id == organization_id,
                FuelRetailPriceSnapshot.station_id.in_(station_ids),
                FuelRetailPriceSnapshot.canonical_product_id.in_(product_ids),
                FuelRetailPriceSnapshot.source_active.is_(True),
            )
        )
        prices: dict[tuple[uuid.UUID, str | None], Decimal] = {}
        for snapshot in result.scalars().all():
            key = (snapshot.canonical_product_id, snapshot.payment_method_group)
            if key not in prices:
                prices[key] = snapshot.price_per_liter
        return prices

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
