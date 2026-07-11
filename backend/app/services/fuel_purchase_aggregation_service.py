from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.fuel_purchases_enums import PurchaseMetricEligibilityStatus, PurchaseOperationType
from app.core.fuel_purchases_normalization import cost_per_liter, money
from app.models.fuel_purchases import FuelPurchaseDailyMetric, FuelPurchaseInvoice, FuelPurchaseItem
from app.services.fuel_purchases_apply_service import PurchaseAggregationKey

_ZERO = Decimal("0")


class FuelPurchaseAggregationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def rebuild_keys(
        self,
        *,
        organization_id: uuid.UUID,
        keys: list[PurchaseAggregationKey],
        sync_run_id: uuid.UUID | None = None,
    ) -> int:
        # Deduplicar chaves
        unique: dict[tuple, PurchaseAggregationKey] = {}
        for key in keys:
            unique[(key.station_id, key.business_date, key.canonical_product_id, key.distributor_id)] = key
        rebuilt = 0
        for key in unique.values():
            await self._rebuild_one(organization_id=organization_id, key=key, sync_run_id=sync_run_id)
            rebuilt += 1
        return rebuilt

    async def _rebuild_one(
        self,
        *,
        organization_id: uuid.UUID,
        key: PurchaseAggregationKey,
        sync_run_id: uuid.UUID | None,
    ) -> None:
        now = datetime.now(UTC)
        delete_q = delete(FuelPurchaseDailyMetric).where(
            FuelPurchaseDailyMetric.organization_id == organization_id,
            FuelPurchaseDailyMetric.station_id == key.station_id,
            FuelPurchaseDailyMetric.business_date == key.business_date,
        )
        if key.canonical_product_id is None:
            delete_q = delete_q.where(FuelPurchaseDailyMetric.canonical_product_id.is_(None))
        else:
            delete_q = delete_q.where(
                FuelPurchaseDailyMetric.canonical_product_id == key.canonical_product_id
            )
        if key.distributor_id is None:
            delete_q = delete_q.where(FuelPurchaseDailyMetric.distributor_id.is_(None))
        else:
            delete_q = delete_q.where(FuelPurchaseDailyMetric.distributor_id == key.distributor_id)
        await self.db.execute(delete_q)

        items_q = (
            select(FuelPurchaseItem, FuelPurchaseInvoice)
            .join(FuelPurchaseInvoice, FuelPurchaseItem.purchase_invoice_id == FuelPurchaseInvoice.id)
            .where(
                FuelPurchaseItem.organization_id == organization_id,
                FuelPurchaseItem.station_id == key.station_id,
                FuelPurchaseInvoice.entry_date == key.business_date,
                FuelPurchaseItem.is_cancelled.is_(False),
            )
        )
        if key.canonical_product_id is None:
            items_q = items_q.where(FuelPurchaseItem.canonical_product_id.is_(None))
        else:
            items_q = items_q.where(FuelPurchaseItem.canonical_product_id == key.canonical_product_id)
        if key.distributor_id is None:
            items_q = items_q.where(FuelPurchaseInvoice.distributor_id.is_(None))
        else:
            items_q = items_q.where(FuelPurchaseInvoice.distributor_id == key.distributor_id)

        rows = (await self.db.execute(items_q)).all()
        if not rows:
            return

        invoice_ids: set[uuid.UUID] = set()
        item_count = 0
        volume = _ZERO
        gross = _ZERO
        discount = _ZERO
        freight = _ZERO
        other = _ZERO
        delivered = _ZERO
        erp_cost = _ZERO
        erp_cost_seen = False
        unmapped_count = 0
        unmapped_volume = _ZERO
        missing_cost = 0

        for item, invoice in rows:
            if item.metric_eligibility_status == PurchaseMetricEligibilityStatus.EXCLUDED.value:
                if item.canonical_product_id is None:
                    unmapped_count += 1
                    unmapped_volume += item.volume_liters or _ZERO
                continue
            sign = (
                Decimal("-1")
                if item.operation_type == PurchaseOperationType.PURCHASE_RETURN.value
                else Decimal("1")
            )
            item_count += 1
            invoice_ids.add(invoice.id)
            vol = item.volume_liters or _ZERO
            volume += sign * vol
            gross += sign * (item.gross_item_amount or _ZERO)
            discount += sign * (item.discount_amount or _ZERO)
            freight += sign * (item.allocated_freight_amount or _ZERO)
            other += sign * (item.allocated_other_expenses or _ZERO)
            delivered += sign * (item.commercial_delivered_cost or _ZERO)
            if item.erp_recorded_cost is not None:
                erp_cost += sign * item.erp_recorded_cost
                erp_cost_seen = True
            else:
                missing_cost += 1
            if item.canonical_product_id is None:
                unmapped_count += 1
                unmapped_volume += vol

        avg = cost_per_liter(delivered / volume) if volume > 0 else None
        self.db.add(
            FuelPurchaseDailyMetric(
                id=uuid.uuid4(),
                organization_id=organization_id,
                station_id=key.station_id,
                business_date=key.business_date,
                canonical_product_id=key.canonical_product_id,
                distributor_id=key.distributor_id,
                invoice_count=len(invoice_ids),
                item_count=item_count,
                purchased_volume_liters=volume,
                gross_purchase_amount=money(gross) or _ZERO,
                discount_amount=money(discount) or _ZERO,
                freight_amount=money(freight) or _ZERO,
                other_expenses_amount=money(other) or _ZERO,
                commercial_delivered_cost=money(delivered) or _ZERO,
                average_delivered_cost_per_liter=avg,
                erp_recorded_cost=money(erp_cost) if erp_cost_seen else None,
                unmapped_item_count=unmapped_count,
                unmapped_volume_liters=unmapped_volume,
                missing_cost_item_count=missing_cost,
                last_rebuilt_at=now,
                last_sync_run_id=sync_run_id,
            )
        )
