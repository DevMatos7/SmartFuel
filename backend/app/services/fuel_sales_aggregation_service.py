from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.fuel_sales_enums import FuelOperationType, MetricEligibilityStatus, MetricExclusionReason
from app.models.fuel_sales import FuelSalesDailyMetric, FuelSalesFact
from app.services.fuel_sales_apply_service import AffectedAggregationKey
from app.services.fuel_sales_calculation_service import compute_realized_price_per_liter


class FuelSalesAggregationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def rebuild_keys(
        self,
        *,
        organization_id: uuid.UUID,
        keys: list[AffectedAggregationKey],
        sync_run_id: uuid.UUID | None = None,
    ) -> int:
        rebuilt = 0
        for key in keys:
            if key.canonical_product_id is None:
                continue
            await self._rebuild_one(
                organization_id=organization_id,
                key=key,
                sync_run_id=sync_run_id,
            )
            rebuilt += 1
        return rebuilt

    async def _rebuild_one(
        self,
        *,
        organization_id: uuid.UUID,
        key: AffectedAggregationKey,
        sync_run_id: uuid.UUID | None,
    ) -> None:
        now = datetime.now(UTC)
        delete_query = delete(FuelSalesDailyMetric).where(
            FuelSalesDailyMetric.organization_id == organization_id,
            FuelSalesDailyMetric.station_id == key.station_id,
            FuelSalesDailyMetric.business_date == key.business_date,
            FuelSalesDailyMetric.canonical_product_id == key.canonical_product_id,
        )
        if key.payment_method_group is None:
            delete_query = delete_query.where(FuelSalesDailyMetric.payment_method_group.is_(None))
        else:
            delete_query = delete_query.where(
                FuelSalesDailyMetric.payment_method_group == key.payment_method_group
            )
        await self.db.execute(delete_query)

        query = select(FuelSalesFact).where(
            FuelSalesFact.organization_id == organization_id,
            FuelSalesFact.station_id == key.station_id,
            FuelSalesFact.business_date == key.business_date,
            FuelSalesFact.canonical_product_id == key.canonical_product_id,
            FuelSalesFact.is_cancelled.is_(False),
            FuelSalesFact.metric_eligibility_status.in_(
                (MetricEligibilityStatus.ELIGIBLE, MetricEligibilityStatus.ELIGIBLE_WITH_WARNINGS)
            ),
        )
        if key.payment_method_group is None:
            query = query.where(FuelSalesFact.payment_method_group.is_(None))
        else:
            query = query.where(FuelSalesFact.payment_method_group == key.payment_method_group)

        result = await self.db.execute(query)
        facts = list(result.scalars().all())
        if not facts:
            return

        net_volume = Decimal("0")
        gross_sales = Decimal("0")
        discount_total = Decimal("0")
        net_sales = Decimal("0")
        total_cost = Decimal("0")
        cost_volume = Decimal("0")
        negative_margin_count = 0
        unmapped_count = 0
        unmapped_volume = Decimal("0")

        for fact in facts:
            sign = Decimal("-1") if fact.operation_type == FuelOperationType.RETURN else Decimal("1")
            vol = fact.volume_liters or Decimal("0")
            net_volume += sign * vol
            gross_sales += sign * fact.gross_amount
            discount_total += sign * fact.discount_amount
            net_sales += sign * fact.net_amount
            if fact.total_cost_amount is not None:
                total_cost += sign * fact.total_cost_amount
                cost_volume += sign * vol
            if fact.gross_margin_amount is not None and fact.gross_margin_amount < 0:
                negative_margin_count += 1

        unmapped_result = await self.db.execute(
            select(FuelSalesFact).where(
                FuelSalesFact.organization_id == organization_id,
                FuelSalesFact.station_id == key.station_id,
                FuelSalesFact.business_date == key.business_date,
                FuelSalesFact.is_cancelled.is_(False),
                FuelSalesFact.metric_eligibility_status == MetricEligibilityStatus.EXCLUDED,
            )
        )
        unmapped_facts = [
            f
            for f in unmapped_result.scalars().all()
            if f.metric_exclusion_reasons and MetricExclusionReason.UNMAPPED_PRODUCT.value in f.metric_exclusion_reasons
        ]
        unmapped_count = len(unmapped_facts)
        unmapped_volume = sum((f.volume_liters or Decimal("0")) for f in unmapped_facts)

        realized_price = compute_realized_price_per_liter(net_sales, net_volume)
        gross_margin = net_sales - total_cost if cost_volume > 0 else None
        margin_per_liter = gross_margin / cost_volume if gross_margin is not None and cost_volume > 0 else None
        margin_percent = (gross_margin / net_sales * Decimal("100")) if gross_margin is not None and net_sales != 0 else None

        metric = FuelSalesDailyMetric(
            organization_id=organization_id,
            station_id=key.station_id,
            business_date=key.business_date,
            canonical_product_id=key.canonical_product_id,
            payment_method_group=key.payment_method_group,
            sales_item_count=len(facts),
            net_volume_liters=net_volume,
            gross_sales_amount=gross_sales,
            discount_amount=discount_total,
            net_sales_amount=net_sales,
            total_cost_amount=total_cost if cost_volume > 0 else None,
            cost_available_volume_liters=cost_volume,
            realized_price_per_liter=realized_price,
            gross_margin_amount=gross_margin,
            gross_margin_per_liter=margin_per_liter,
            gross_margin_percent=margin_percent,
            negative_margin_item_count=negative_margin_count,
            unmapped_item_count=unmapped_count,
            unmapped_volume_liters=unmapped_volume,
            last_rebuilt_at=now,
            last_sync_run_id=sync_run_id,
        )
        self.db.add(metric)
