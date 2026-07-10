from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.fuel_sales_enums import (
    CostSource,
    FuelOperationType,
    MarginStatus,
    MetricEligibilityStatus,
    MetricExclusionReason,
    PaymentMethodGroup,
    PriceHistorySource,
)
from app.core.master_data_enums import MappingStatus
from app.core.xpert_sync_enums import ErpDatasetCode, ErpStagingStatus
from app.integrations.xpert.canonical_hash import canonical_record_hash
from app.integrations.xpert.normalizers import hash_payload_for_dataset, parse_source_datetime
from app.models.erp_integration import ErpStagingRecord, ErpSyncRun
from app.models.erp_product import ErpProduct
from app.models.fuel_sales import ErpPaymentMethod, FuelRetailPriceSnapshot, FuelSalesFact
from app.services.fuel_sales_calculation_service import (
    compute_margin,
    compute_net_amount,
    compute_realized_price_per_liter,
    compute_total_cost,
)

LITER_UNITS = {"l", "lt", "litro", "litros", "liter", "liters"}


@dataclass
class AffectedAggregationKey:
    station_id: uuid.UUID
    business_date: date
    canonical_product_id: uuid.UUID | None
    payment_method_group: str | None


@dataclass
class FuelSalesApplyResult:
    outcome: str
    affected_keys: list[AffectedAggregationKey] = field(default_factory=list)


class FuelSalesApplyService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._affected_keys: list[AffectedAggregationKey] = []

    async def apply_staging_record(
        self,
        *,
        run: ErpSyncRun,
        staging: ErpStagingRecord,
        now: datetime,
    ) -> FuelSalesApplyResult:
        if staging.dataset_code == ErpDatasetCode.PAYMENT_METHODS:
            outcome = await self._apply_payment_method(run=run, staging=staging, now=now)
            return FuelSalesApplyResult(outcome=outcome)
        if staging.dataset_code == ErpDatasetCode.FUEL_SALES_ITEMS:
            outcome = await self._apply_sales_item(run=run, staging=staging, now=now)
            return FuelSalesApplyResult(outcome=outcome, affected_keys=list(self._affected_keys))
        if staging.dataset_code == ErpDatasetCode.FUEL_RETAIL_PRICES:
            outcome = await self._apply_retail_price(run=run, staging=staging, now=now)
            return FuelSalesApplyResult(outcome=outcome)
        staging.processing_status = ErpStagingStatus.SKIPPED_UNCHANGED
        return FuelSalesApplyResult(outcome="skipped")

    async def mark_absent_payment_methods(
        self,
        *,
        run: ErpSyncRun,
        seen_keys: set[str],
        now: datetime,
    ) -> int:
        if run.station_id is None:
            return 0
        result = await self.db.execute(
            select(ErpPaymentMethod).where(
                ErpPaymentMethod.station_id == run.station_id,
                ErpPaymentMethod.source_active.is_(True),
            )
        )
        marked = 0
        for method in result.scalars().all():
            if method.source_payment_method_id not in seen_keys:
                method.source_active = False
                method.source_last_seen_at = now
                method.last_sync_run_id = run.id
                marked += 1
        return marked

    async def _apply_payment_method(
        self,
        *,
        run: ErpSyncRun,
        staging: ErpStagingRecord,
        now: datetime,
    ) -> str:
        normalized = staging.normalized_payload or {}
        source_id = normalized.get("source_payment_method_id")
        if not source_id:
            staging.processing_status = ErpStagingStatus.ERROR
            return "error"

        record_hash = staging.record_hash or canonical_record_hash(
            hash_payload_for_dataset(ErpDatasetCode.PAYMENT_METHODS, normalized)
        )
        existing = await self._load_payment_method(run.station_id, source_id)
        if existing is None:
            entity = ErpPaymentMethod(
                organization_id=run.organization_id,
                station_id=run.station_id,
                source_payment_method_id=source_id,
                source_code=normalized.get("source_payment_method_code"),
                source_name=normalized.get("source_payment_method_name") or source_id,
                normalized_group=PaymentMethodGroup.UNMAPPED,
                mapping_status=MappingStatus.PENDING,
                source_active=staging.source_active if staging.source_active is not None else True,
                source_record_hash=record_hash,
                source_updated_at=staging.source_updated_at,
                source_last_seen_at=now,
                last_sync_run_id=run.id,
            )
            self.db.add(entity)
            await self.db.flush()
            staging.applied_entity_type = "erp_payment_method"
            staging.applied_entity_id = entity.id
            staging.processing_status = ErpStagingStatus.APPLIED
            staging.applied_at = now
            return "inserted"

        if existing.source_record_hash == record_hash:
            existing.source_last_seen_at = now
            existing.last_sync_run_id = run.id
            staging.applied_entity_type = "erp_payment_method"
            staging.applied_entity_id = existing.id
            staging.processing_status = ErpStagingStatus.SKIPPED_UNCHANGED
            staging.applied_at = now
            return "unchanged"

        existing.source_code = normalized.get("source_payment_method_code")
        existing.source_name = normalized.get("source_payment_method_name") or existing.source_name
        if staging.source_active is not None:
            existing.source_active = staging.source_active
        existing.source_record_hash = record_hash
        existing.source_updated_at = staging.source_updated_at
        existing.source_last_seen_at = now
        existing.last_sync_run_id = run.id
        existing.updated_at = now
        staging.applied_entity_type = "erp_payment_method"
        staging.applied_entity_id = existing.id
        staging.processing_status = ErpStagingStatus.APPLIED
        staging.applied_at = now
        return "updated"

    async def _apply_sales_item(
        self,
        *,
        run: ErpSyncRun,
        staging: ErpStagingRecord,
        now: datetime,
    ) -> str:
        if run.station_id is None:
            staging.processing_status = ErpStagingStatus.ERROR
            return "error"

        normalized = staging.normalized_payload or {}
        source_sale_id = normalized.get("source_sale_id")
        source_sale_item_id = normalized.get("source_sale_item_id")
        source_product_id = normalized.get("source_product_id")
        if not source_sale_id or not source_sale_item_id or not source_product_id:
            staging.processing_status = ErpStagingStatus.ERROR
            return "error"

        erp_product = await self._load_erp_product(run.station_id, source_product_id)
        if erp_product is None:
            staging.processing_status = ErpStagingStatus.ERROR
            return "error"

        record_hash = staging.record_hash or canonical_record_hash(
            hash_payload_for_dataset(ErpDatasetCode.FUEL_SALES_ITEMS, normalized)
        )
        existing = await self._load_sales_fact(
            run.organization_id,
            run.station_id,
            source_sale_id,
            source_sale_item_id,
        )
        old_business_date = existing.business_date if existing else None
        old_canonical_id = existing.canonical_product_id if existing else None
        old_payment_group = existing.payment_method_group if existing else None

        if existing is not None and existing.source_record_hash == record_hash:
            existing.source_updated_at = staging.source_updated_at
            existing.last_sync_run_id = run.id
            staging.applied_entity_type = "fuel_sales_fact"
            staging.applied_entity_id = existing.id
            staging.processing_status = ErpStagingStatus.SKIPPED_UNCHANGED
            staging.applied_at = now
            return "unchanged"

        payment_method_group: str | None = None
        erp_payment_method_id: uuid.UUID | None = None
        source_pm_id = normalized.get("source_payment_method_id")
        if source_pm_id:
            pm = await self._load_payment_method(run.station_id, source_pm_id)
            if pm:
                erp_payment_method_id = pm.id
                payment_method_group = pm.normalized_group if pm.mapping_status == MappingStatus.MAPPED else None

        fact_fields = self._build_sales_fact_fields(
            run=run,
            normalized=normalized,
            erp_product=erp_product,
            staging=staging,
            record_hash=record_hash,
            now=now,
            erp_payment_method_id=erp_payment_method_id,
            payment_method_group=payment_method_group,
        )

        if existing is None:
            entity = FuelSalesFact(**fact_fields)
            self.db.add(entity)
            await self.db.flush()
            staging.applied_entity_type = "fuel_sales_fact"
            staging.applied_entity_id = entity.id
            staging.processing_status = ErpStagingStatus.APPLIED
            staging.applied_at = now
            outcome = "inserted"
        else:
            for key, value in fact_fields.items():
                setattr(existing, key, value)
            existing.updated_at = now
            staging.applied_entity_type = "fuel_sales_fact"
            staging.applied_entity_id = existing.id
            staging.processing_status = ErpStagingStatus.APPLIED
            staging.applied_at = now
            outcome = "updated"

        self._track_aggregation_key(
            station_id=run.station_id,
            business_date=fact_fields["business_date"],
            canonical_product_id=fact_fields["canonical_product_id"],
            payment_method_group=fact_fields["payment_method_group"],
        )
        if old_business_date and old_business_date != fact_fields["business_date"]:
            self._track_aggregation_key(
                station_id=run.station_id,
                business_date=old_business_date,
                canonical_product_id=old_canonical_id,
                payment_method_group=old_payment_group,
            )
        elif old_canonical_id != fact_fields["canonical_product_id"] or old_payment_group != fact_fields["payment_method_group"]:
            self._track_aggregation_key(
                station_id=run.station_id,
                business_date=fact_fields["business_date"],
                canonical_product_id=old_canonical_id,
                payment_method_group=old_payment_group,
            )
        return outcome

    def _build_sales_fact_fields(
        self,
        *,
        run: ErpSyncRun,
        normalized: dict,
        erp_product: ErpProduct,
        staging: ErpStagingRecord,
        record_hash: str,
        now: datetime,
        erp_payment_method_id: uuid.UUID | None,
        payment_method_group: str | None,
    ) -> dict:
        is_cancelled = bool(normalized.get("source_cancelled"))
        operation_type = normalized.get("source_operation_type") or FuelOperationType.SALE
        sold_at = parse_source_datetime(normalized.get("source_sale_datetime")) or now
        business_date = _parse_business_date(normalized.get("source_business_date")) or sold_at.date()

        quantity = _to_decimal(normalized.get("source_quantity"))
        unit = (normalized.get("source_unit") or "").strip().lower() or None
        volume_liters, volume_reason = _resolve_volume_liters(quantity, unit)

        gross = _to_decimal(normalized.get("source_gross_amount"))
        discount = _to_decimal(normalized.get("source_discount_amount"))
        surcharge = _to_decimal(normalized.get("source_surcharge_amount"))
        net_amount, _net_source = compute_net_amount(
            source_net=_to_decimal(normalized.get("source_net_amount")),
            gross=gross,
            discount=discount,
            surcharge=surcharge,
        )

        cost_per_unit = _to_decimal(normalized.get("source_cost_per_unit"))
        total_cost, cost_source, cost_mismatch = compute_total_cost(
            source_total_cost=_to_decimal(normalized.get("source_total_cost")),
            cost_per_liter=cost_per_unit,
            volume_liters=volume_liters,
        )

        realized_price = compute_realized_price_per_liter(net_amount, volume_liters)
        margin = compute_margin(
            net_amount=net_amount,
            total_cost=total_cost,
            volume_liters=volume_liters,
        )

        source_pm_id = normalized.get("source_payment_method_id")

        eligibility, reasons = _compute_eligibility(
            is_cancelled=is_cancelled,
            erp_product=erp_product,
            volume_liters=volume_liters,
            volume_reason=volume_reason,
            net_amount=net_amount,
            cost_mismatch=cost_mismatch,
            payment_method_group=payment_method_group,
            source_payment_method_id=source_pm_id,
            margin_status=margin["margin_status"],
            gross_margin_amount=margin.get("gross_margin_amount"),
        )

        if (
            margin["margin_status"] == MarginStatus.AVAILABLE
            and margin.get("gross_margin_amount") is not None
            and margin["gross_margin_amount"] < 0
            and MetricExclusionReason.NEGATIVE_GROSS_MARGIN not in reasons
        ):
            if eligibility == MetricEligibilityStatus.ELIGIBLE:
                eligibility = MetricEligibilityStatus.ELIGIBLE_WITH_WARNINGS
            reasons.append(MetricExclusionReason.NEGATIVE_GROSS_MARGIN)

        canonical_product_id = None
        if erp_product.mapping_status == MappingStatus.MAPPED:
            canonical_product_id = erp_product.canonical_product_id

        return {
            "organization_id": run.organization_id,
            "station_id": run.station_id,
            "source_sale_id": normalized["source_sale_id"],
            "source_sale_item_id": normalized["source_sale_item_id"],
            "source_document_number": normalized.get("source_document_number"),
            "sold_at_utc": sold_at,
            "business_date": business_date,
            "erp_product_id": erp_product.id,
            "canonical_product_id": canonical_product_id,
            "erp_payment_method_id": erp_payment_method_id,
            "payment_method_group": payment_method_group,
            "operation_type": operation_type,
            "is_cancelled": is_cancelled,
            "source_unit": normalized.get("source_unit"),
            "quantity_source": quantity,
            "volume_liters": volume_liters,
            "unit_price": _to_decimal(normalized.get("source_unit_price")),
            "gross_amount": gross or Decimal("0"),
            "discount_amount": discount or Decimal("0"),
            "surcharge_amount": surcharge or Decimal("0"),
            "net_amount": net_amount or Decimal("0"),
            "cost_per_liter": cost_per_unit,
            "total_cost_amount": total_cost,
            "cost_source": cost_source,
            "margin_status": margin["margin_status"],
            "realized_price_per_liter": realized_price,
            "gross_margin_amount": margin.get("gross_margin_amount"),
            "gross_margin_per_liter": margin.get("gross_margin_per_liter"),
            "gross_margin_percent": margin.get("gross_margin_percent"),
            "metric_eligibility_status": eligibility,
            "metric_exclusion_reasons": [r.value if hasattr(r, "value") else r for r in reasons] or None,
            "source_record_hash": record_hash,
            "source_updated_at": staging.source_updated_at,
            "last_sync_run_id": run.id,
        }

    async def _apply_retail_price(
        self,
        *,
        run: ErpSyncRun,
        staging: ErpStagingRecord,
        now: datetime,
    ) -> str:
        if run.station_id is None:
            staging.processing_status = ErpStagingStatus.ERROR
            return "error"

        normalized = staging.normalized_payload or {}
        source_product_id = normalized.get("source_product_id")
        source_pm_id = normalized.get("source_payment_method_id")
        price = _to_decimal(normalized.get("source_price_per_liter"))
        if not source_product_id or not source_pm_id or price is None:
            staging.processing_status = ErpStagingStatus.ERROR
            return "error"

        erp_product = await self._load_erp_product(run.station_id, source_product_id)
        pm = await self._load_payment_method(run.station_id, source_pm_id)
        if erp_product is None or pm is None:
            staging.processing_status = ErpStagingStatus.ERROR
            return "error"

        record_hash = staging.record_hash or canonical_record_hash(
            hash_payload_for_dataset(ErpDatasetCode.FUEL_RETAIL_PRICES, normalized)
        )
        effective_from = parse_source_datetime(normalized.get("source_effective_from")) or now
        history_source = (
            PriceHistorySource.SOURCE_EFFECTIVE_DATE
            if normalized.get("source_effective_from")
            else PriceHistorySource.OBSERVED_BY_SYNC
        )

        current = await self._load_current_price_snapshot(
            run.station_id,
            erp_product.id,
            pm.id,
        )
        if current is not None and current.source_record_hash == record_hash:
            current.source_updated_at = staging.source_updated_at
            current.last_sync_run_id = run.id
            staging.applied_entity_type = "fuel_retail_price_snapshot"
            staging.applied_entity_id = current.id
            staging.processing_status = ErpStagingStatus.SKIPPED_UNCHANGED
            staging.applied_at = now
            return "unchanged"

        if current is not None and current.price_per_liter == price and current.source_active:
            current.observed_at = now
            current.source_updated_at = staging.source_updated_at
            current.last_sync_run_id = run.id
            staging.applied_entity_type = "fuel_retail_price_snapshot"
            staging.applied_entity_id = current.id
            staging.processing_status = ErpStagingStatus.SKIPPED_UNCHANGED
            staging.applied_at = now
            return "unchanged"

        if current is not None and current.source_active:
            current.effective_until = now
            current.source_active = False

        canonical_product_id = erp_product.canonical_product_id if erp_product.mapping_status == MappingStatus.MAPPED else None
        payment_group = pm.normalized_group if pm.mapping_status == MappingStatus.MAPPED else None
        entity = FuelRetailPriceSnapshot(
            organization_id=run.organization_id,
            station_id=run.station_id,
            erp_product_id=erp_product.id,
            canonical_product_id=canonical_product_id,
            erp_payment_method_id=pm.id,
            payment_method_group=payment_group,
            price_per_liter=price,
            history_source=history_source,
            effective_from=effective_from,
            effective_until=None,
            observed_at=now,
            source_active=bool(normalized.get("source_active", True)),
            source_record_hash=record_hash,
            source_updated_at=staging.source_updated_at,
            last_sync_run_id=run.id,
            created_at=now,
        )
        self.db.add(entity)
        await self.db.flush()
        staging.applied_entity_type = "fuel_retail_price_snapshot"
        staging.applied_entity_id = entity.id
        staging.processing_status = ErpStagingStatus.APPLIED
        staging.applied_at = now
        return "inserted"

    def _track_aggregation_key(
        self,
        *,
        station_id: uuid.UUID,
        business_date: date,
        canonical_product_id: uuid.UUID | None,
        payment_method_group: str | None,
    ) -> None:
        if canonical_product_id is None:
            return
        key = AffectedAggregationKey(
            station_id=station_id,
            business_date=business_date,
            canonical_product_id=canonical_product_id,
            payment_method_group=payment_method_group,
        )
        if key not in self._affected_keys:
            self._affected_keys.append(key)

    async def _load_payment_method(self, station_id: uuid.UUID | None, source_id: str) -> ErpPaymentMethod | None:
        if station_id is None:
            return None
        result = await self.db.execute(
            select(ErpPaymentMethod).where(
                ErpPaymentMethod.station_id == station_id,
                ErpPaymentMethod.source_payment_method_id == source_id,
            )
        )
        return result.scalar_one_or_none()

    async def _load_erp_product(self, station_id: uuid.UUID, source_product_id: str) -> ErpProduct | None:
        result = await self.db.execute(
            select(ErpProduct).where(
                ErpProduct.station_id == station_id,
                ErpProduct.erp_product_id == source_product_id,
            )
        )
        return result.scalar_one_or_none()

    async def _load_sales_fact(
        self,
        organization_id: uuid.UUID,
        station_id: uuid.UUID,
        source_sale_id: str,
        source_sale_item_id: str,
    ) -> FuelSalesFact | None:
        result = await self.db.execute(
            select(FuelSalesFact).where(
                FuelSalesFact.organization_id == organization_id,
                FuelSalesFact.station_id == station_id,
                FuelSalesFact.source_sale_id == source_sale_id,
                FuelSalesFact.source_sale_item_id == source_sale_item_id,
            )
        )
        return result.scalar_one_or_none()

    async def _load_current_price_snapshot(
        self,
        station_id: uuid.UUID,
        erp_product_id: uuid.UUID,
        erp_payment_method_id: uuid.UUID,
    ) -> FuelRetailPriceSnapshot | None:
        result = await self.db.execute(
            select(FuelRetailPriceSnapshot)
            .where(
                FuelRetailPriceSnapshot.station_id == station_id,
                FuelRetailPriceSnapshot.erp_product_id == erp_product_id,
                FuelRetailPriceSnapshot.erp_payment_method_id == erp_payment_method_id,
                FuelRetailPriceSnapshot.source_active.is_(True),
            )
            .order_by(FuelRetailPriceSnapshot.effective_from.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()


def _to_decimal(value) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _parse_business_date(value) -> date | None:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    text = str(value).strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _resolve_volume_liters(quantity: Decimal | None, unit: str | None) -> tuple[Decimal | None, str | None]:
    if quantity is None:
        return None, MetricExclusionReason.INVALID_VOLUME
    if unit is None or unit in LITER_UNITS:
        return quantity, None
    return None, MetricExclusionReason.UNIT_CONVERSION_REQUIRED


def _compute_eligibility(
    *,
    is_cancelled: bool,
    erp_product: ErpProduct,
    volume_liters: Decimal | None,
    volume_reason: str | None,
    net_amount: Decimal | None,
    cost_mismatch: bool,
    payment_method_group: str | None,
    source_payment_method_id: str | None,
    margin_status: str,
    gross_margin_amount: Decimal | None,
) -> tuple[str, list]:
    reasons: list = []
    if is_cancelled:
        return MetricEligibilityStatus.EXCLUDED, [MetricExclusionReason.CANCELLED_SALE]
    if erp_product.mapping_status == MappingStatus.IGNORED:
        return MetricEligibilityStatus.EXCLUDED, [MetricExclusionReason.IGNORED_PRODUCT]
    if erp_product.mapping_status != MappingStatus.MAPPED:
        return MetricEligibilityStatus.EXCLUDED, [MetricExclusionReason.UNMAPPED_PRODUCT]
    if volume_reason == MetricExclusionReason.UNIT_CONVERSION_REQUIRED:
        return MetricEligibilityStatus.EXCLUDED, [MetricExclusionReason.UNIT_CONVERSION_REQUIRED]
    if volume_liters is None or volume_liters <= 0:
        return MetricEligibilityStatus.EXCLUDED, [MetricExclusionReason.INVALID_VOLUME]
    if net_amount is None:
        return MetricEligibilityStatus.EXCLUDED, [MetricExclusionReason.MISSING_NET_AMOUNT]
    if source_payment_method_id and payment_method_group is None:
        reasons.append(MetricExclusionReason.MIXED_OR_UNALLOCATED_PAYMENT)
    if cost_mismatch:
        reasons.append(MetricExclusionReason.COST_COMPONENT_MISMATCH)
    if margin_status == MarginStatus.UNAVAILABLE:
        reasons.append(MetricExclusionReason.MISSING_COST)
    if reasons:
        return MetricEligibilityStatus.ELIGIBLE_WITH_WARNINGS, reasons
    return MetricEligibilityStatus.ELIGIBLE, []
