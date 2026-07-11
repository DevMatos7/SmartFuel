"""Serviços de referência temporal e agrupamento — Sprint 8."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, time
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.purchase_benchmark_enums import (
    BenchmarkOverrideType,
    PurchaseReferenceConfidence,
    PurchaseReferenceSource,
)
from app.models.fuel_purchases import FuelPurchaseInvoice, FuelPurchaseItem
from app.models.purchase_benchmarks import PurchaseBenchmarkOverride


@dataclass
class ReferenceResolution:
    reference_datetime: datetime | None
    source: str
    confidence: str
    warnings: list[str] = field(default_factory=list)


@dataclass
class PurchaseProductGroup:
    group_key: str
    canonical_product_id: uuid.UUID | None
    item_ids: list[uuid.UUID]
    volume_liters: Decimal
    commercial_delivered_cost: Decimal
    source_product_ids: list[str]
    unmapped: bool
    ignored: bool = False


class PurchaseBenchmarkReferenceService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def resolve(
        self,
        *,
        invoice: FuelPurchaseInvoice,
        organization_id: uuid.UUID,
    ) -> ReferenceResolution:
        overrides = await self._active_overrides(organization_id, invoice.id)
        manual = next(
            (o for o in overrides if o.override_type == BenchmarkOverrideType.REFERENCE_DATETIME),
            None,
        )
        if manual is not None:
            raw = (manual.new_value or {}).get("reference_datetime")
            if raw:
                dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=UTC)
                return ReferenceResolution(
                    reference_datetime=dt,
                    source=PurchaseReferenceSource.MANUAL_DECISION_DATETIME,
                    confidence=PurchaseReferenceConfidence.HIGH,
                )

        # Pedido de compra ainda não modelado no PG — reservado.
        if invoice.issue_date is not None:
            dt = datetime.combine(invoice.issue_date, time.min, tzinfo=UTC)
            return ReferenceResolution(
                reference_datetime=dt,
                source=PurchaseReferenceSource.INVOICE_ISSUE_DATETIME,
                confidence=PurchaseReferenceConfidence.MEDIUM,
            )

        if invoice.entry_date is not None:
            dt = datetime.combine(invoice.entry_date, time.min, tzinfo=UTC)
            return ReferenceResolution(
                reference_datetime=dt,
                source=PurchaseReferenceSource.ENTRY_DATETIME_FALLBACK,
                confidence=PurchaseReferenceConfidence.LOW,
                warnings=["Referência temporal de baixa confiança (entrada no estoque)."],
            )

        return ReferenceResolution(
            reference_datetime=None,
            source=PurchaseReferenceSource.UNKNOWN,
            confidence=PurchaseReferenceConfidence.UNAVAILABLE,
            warnings=["Sem referência temporal confiável."],
        )

    async def _active_overrides(
        self, organization_id: uuid.UUID, invoice_id: uuid.UUID
    ) -> list[PurchaseBenchmarkOverride]:
        rows = (
            await self.db.execute(
                select(PurchaseBenchmarkOverride)
                .where(
                    PurchaseBenchmarkOverride.organization_id == organization_id,
                    PurchaseBenchmarkOverride.purchase_invoice_id == invoice_id,
                    PurchaseBenchmarkOverride.deactivated_at.is_(None),
                )
                .order_by(PurchaseBenchmarkOverride.created_at.desc())
            )
        ).scalars().all()
        return list(rows)


class PurchaseItemGroupingService:
    def group(self, items: list[FuelPurchaseItem]) -> list[PurchaseProductGroup]:
        buckets: dict[str, list[FuelPurchaseItem]] = {}
        for item in items:
            if item.is_cancelled:
                continue
            if item.canonical_product_id is not None:
                key = f"product:{item.canonical_product_id}"
            else:
                key = f"unmapped:{item.source_product_id}"
            buckets.setdefault(key, []).append(item)

        groups: list[PurchaseProductGroup] = []
        for key, group_items in buckets.items():
            volume = sum((i.volume_liters or Decimal("0") for i in group_items), Decimal("0"))
            cost = sum((i.commercial_delivered_cost or Decimal("0") for i in group_items), Decimal("0"))
            canonical = group_items[0].canonical_product_id
            groups.append(
                PurchaseProductGroup(
                    group_key=key,
                    canonical_product_id=canonical,
                    item_ids=[i.id for i in group_items],
                    volume_liters=volume,
                    commercial_delivered_cost=cost,
                    source_product_ids=sorted({i.source_product_id for i in group_items}),
                    unmapped=canonical is None,
                )
            )
        return groups


class ActualPurchaseCostService:
    @staticmethod
    def cost_per_liter(*, total_cost: Decimal, volume_liters: Decimal) -> Decimal | None:
        if volume_liters is None or volume_liters <= 0:
            return None
        if total_cost is None:
            return None
        return (total_cost / volume_liters).quantize(Decimal("0.00000001"))
