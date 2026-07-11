from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.accounts_payable import normalize_title_status
from app.core.fuel_purchases_enums import (
    InvoiceLinkStatus,
    PurchaseMetricEligibilityStatus,
    PurchaseMetricExclusionReason,
    PurchaseOperationType,
)
from app.core.fuel_purchases_normalization import (
    allocate_header_amounts,
    commercial_delivered_cost,
    delivered_cost_per_liter,
    money,
    quantity,
    resolve_gross_item_amount,
    to_decimal,
)
from app.core.master_data_enums import MappingStatus
from app.core.xpert_sync_enums import ErpDatasetCode, ErpStagingStatus
from app.integrations.xpert.canonical_hash import canonical_record_hash
from app.integrations.xpert.normalizers import hash_payload_for_dataset, parse_source_datetime
from app.models.distributor import ErpSupplier
from app.models.erp_integration import ErpStagingRecord, ErpSyncRun
from app.models.erp_product import ErpProduct
from app.models.fuel_purchases import AccountsPayableTitle, FuelPurchaseInvoice, FuelPurchaseItem
from app.models.station import Station

LITER_UNITS = {"l", "lt", "litro", "litros", "liter", "liters"}
_ZERO = Decimal("0")


@dataclass
class PurchaseAggregationKey:
    station_id: uuid.UUID
    business_date: date
    canonical_product_id: uuid.UUID | None
    distributor_id: uuid.UUID | None


@dataclass
class FuelPurchasesApplyResult:
    outcome: str
    affected_keys: list[PurchaseAggregationKey] = field(default_factory=list)


class FuelPurchasesApplyService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._affected_keys: list[PurchaseAggregationKey] = []

    async def apply_staging_record(
        self,
        *,
        run: ErpSyncRun,
        staging: ErpStagingRecord,
        now: datetime,
    ) -> FuelPurchasesApplyResult:
        if staging.dataset_code == ErpDatasetCode.FUEL_PURCHASE_INVOICES:
            outcome = await self._apply_invoice(run=run, staging=staging, now=now)
            return FuelPurchasesApplyResult(outcome=outcome, affected_keys=list(self._affected_keys))
        if staging.dataset_code == ErpDatasetCode.FUEL_PURCHASE_ITEMS:
            outcome = await self._apply_item(run=run, staging=staging, now=now)
            return FuelPurchasesApplyResult(outcome=outcome, affected_keys=list(self._affected_keys))
        if staging.dataset_code == ErpDatasetCode.ACCOUNTS_PAYABLE_TITLES:
            outcome = await self._apply_title(run=run, staging=staging, now=now)
            return FuelPurchasesApplyResult(outcome=outcome)
        staging.processing_status = ErpStagingStatus.SKIPPED_UNCHANGED
        return FuelPurchasesApplyResult(outcome="skipped")

    async def reprocess_waiting_items(self, *, run: ErpSyncRun, now: datetime) -> int:
        """Reaplica itens WAITING_FOR_INVOICE quando o cabeçalho já existe."""
        if run.station_id is None:
            return 0
        result = await self.db.execute(
            select(ErpStagingRecord).where(
                ErpStagingRecord.organization_id == run.organization_id,
                ErpStagingRecord.station_id == run.station_id,
                ErpStagingRecord.dataset_code == ErpDatasetCode.FUEL_PURCHASE_ITEMS,
                ErpStagingRecord.processing_status == ErpStagingStatus.WAITING_FOR_INVOICE,
            )
        )
        applied = 0
        for staging in result.scalars().all():
            outcome = await self._apply_item(run=run, staging=staging, now=now)
            if outcome in {"inserted", "updated", "unchanged"}:
                applied += 1
        return applied

    async def reconcile_title_links(self, *, run: ErpSyncRun) -> int:
        if run.station_id is None:
            return 0
        result = await self.db.execute(
            select(AccountsPayableTitle).where(
                AccountsPayableTitle.organization_id == run.organization_id,
                AccountsPayableTitle.station_id == run.station_id,
                AccountsPayableTitle.invoice_link_status == InvoiceLinkStatus.PENDING_INVOICE_LINK.value,
            )
        )
        linked = 0
        for title in result.scalars().all():
            invoice = await self._load_invoice(run.organization_id, run.station_id, title.source_invoice_id)
            if invoice is None and title.document_number:
                invoice = await self._load_invoice_by_document(
                    run.organization_id, run.station_id, title.document_number
                )
            if invoice is None:
                continue
            title.purchase_invoice_id = invoice.id
            title.source_invoice_id = invoice.source_invoice_id
            title.invoice_link_status = InvoiceLinkStatus.LINKED.value
            if title.distributor_id is None:
                title.distributor_id = invoice.distributor_id
            if title.erp_supplier_id is None:
                title.erp_supplier_id = invoice.erp_supplier_id
            linked += 1
        return linked

    async def _apply_invoice(self, *, run: ErpSyncRun, staging: ErpStagingRecord, now: datetime) -> str:
        normalized = staging.normalized_payload or {}
        source_invoice_id = normalized.get("source_invoice_id")
        if not source_invoice_id or run.station_id is None:
            staging.processing_status = ErpStagingStatus.ERROR
            return "error"

        branch_err = await self._branch_guard(run, normalized.get("source_branch_id"))
        if branch_err:
            staging.processing_status = ErpStagingStatus.ERROR
            staging.validation_errors = [{"code": "CROSS_STATION_DATA_LEAK", "message": branch_err}]
            return "error"

        record_hash = staging.record_hash or canonical_record_hash(
            hash_payload_for_dataset(ErpDatasetCode.FUEL_PURCHASE_INVOICES, normalized)
        )
        existing = await self._load_invoice(run.organization_id, run.station_id, source_invoice_id)
        supplier = await self._load_erp_supplier(run.station_id, normalized.get("source_supplier_id"))
        distributor_id = supplier.distributor_id if supplier and supplier.mapping_status == MappingStatus.MAPPED else None

        is_cancelled = bool(normalized.get("source_cancelled"))
        operation = normalized.get("source_operation_type") or PurchaseOperationType.PURCHASE.value
        eligibility, reasons = self._invoice_eligibility(is_cancelled=is_cancelled, operation=operation)

        access_key = normalized.get("source_access_key")
        if access_key and (len(str(access_key)) != 44 or not str(access_key).isdigit()):
            reasons = list(reasons or [])
            reasons.append(PurchaseMetricExclusionReason.INVALID_ACCESS_KEY.value)
            eligibility = PurchaseMetricEligibilityStatus.EXCLUDED.value
            access_key = None

        fields = {
            "organization_id": run.organization_id,
            "station_id": run.station_id,
            "source_invoice_id": source_invoice_id,
            "source_document_number": normalized.get("source_document_number") or source_invoice_id,
            "source_series": normalized.get("source_series"),
            "access_key": access_key,
            "xml_imported_in_erp": bool(normalized.get("source_xml_imported_in_erp")),
            "erp_supplier_id": supplier.id if supplier else None,
            "distributor_id": distributor_id,
            "source_supplier_id": normalized.get("source_supplier_id") or "",
            "issue_date": self._as_date(normalized.get("source_issue_date")),
            "entry_date": self._as_date(normalized.get("source_entry_date")),
            "operation_type": operation,
            "source_status": normalized.get("source_status") or "UNKNOWN",
            "is_cancelled": is_cancelled,
            "gross_amount": money(to_decimal(normalized.get("source_total_amount"))) or _ZERO,
            "discount_amount": money(to_decimal(normalized.get("source_discount_amount"))) or _ZERO,
            "freight_amount": money(to_decimal(normalized.get("source_freight_amount"))) or _ZERO,
            "insurance_amount": money(to_decimal(normalized.get("source_insurance_amount"))) or _ZERO,
            "other_expenses_amount": money(to_decimal(normalized.get("source_other_expenses"))) or _ZERO,
            "tax_amount": money(to_decimal(normalized.get("source_tax_amount"))) or _ZERO,
            "total_amount": money(to_decimal(normalized.get("source_total_amount"))) or _ZERO,
            "payment_condition_id": normalized.get("source_payment_condition_id"),
            "source_base_id": normalized.get("source_base_id"),
            "metric_eligibility_status": eligibility,
            "metric_exclusion_reasons": reasons,
            "source_record_hash": record_hash,
            "source_updated_at": parse_source_datetime(normalized.get("source_updated_at")),
            "last_sync_run_id": run.id,
            "updated_at": now,
        }
        if fields["issue_date"] is None or fields["entry_date"] is None:
            staging.processing_status = ErpStagingStatus.ERROR
            return "error"

        if existing is None:
            entity = FuelPurchaseInvoice(created_at=now, **fields)
            self.db.add(entity)
            await self.db.flush()
            staging.processing_status = ErpStagingStatus.APPLIED
            staging.applied_entity_type = "fuel_purchase_invoice"
            staging.applied_entity_id = entity.id
            await self.reprocess_waiting_items(run=run, now=now)
            await self.reconcile_title_links(run=run)
            return "inserted"

        if existing.source_record_hash == record_hash:
            existing.last_sync_run_id = run.id
            staging.processing_status = ErpStagingStatus.SKIPPED_UNCHANGED
            staging.applied_entity_type = "fuel_purchase_invoice"
            staging.applied_entity_id = existing.id
            return "unchanged"

        for key, value in fields.items():
            setattr(existing, key, value)
        staging.processing_status = ErpStagingStatus.APPLIED
        staging.applied_entity_type = "fuel_purchase_invoice"
        staging.applied_entity_id = existing.id
        await self.reprocess_waiting_items(run=run, now=now)
        await self.reconcile_title_links(run=run)
        return "updated"

    async def _apply_item(self, *, run: ErpSyncRun, staging: ErpStagingRecord, now: datetime) -> str:
        normalized = staging.normalized_payload or {}
        source_invoice_id = normalized.get("source_invoice_id")
        source_item_id = normalized.get("source_invoice_item_id")
        if not source_invoice_id or not source_item_id or run.station_id is None:
            staging.processing_status = ErpStagingStatus.ERROR
            return "error"

        branch_err = await self._branch_guard(run, normalized.get("source_branch_id"))
        if branch_err:
            staging.processing_status = ErpStagingStatus.ERROR
            staging.validation_errors = [{"code": "CROSS_STATION_DATA_LEAK", "message": branch_err}]
            return "error"

        invoice = await self._load_invoice(run.organization_id, run.station_id, source_invoice_id)
        if invoice is None:
            staging.processing_status = ErpStagingStatus.WAITING_FOR_INVOICE
            return "waiting_for_invoice"

        record_hash = staging.record_hash or canonical_record_hash(
            hash_payload_for_dataset(ErpDatasetCode.FUEL_PURCHASE_ITEMS, normalized)
        )
        existing = await self._load_item(run.station_id, source_invoice_id, source_item_id)

        erp_product = await self._load_erp_product(run.station_id, normalized.get("source_product_id"))
        missing_product = erp_product is None
        canonical_product_id = (
            erp_product.canonical_product_id
            if erp_product and erp_product.mapping_status == MappingStatus.MAPPED
            else None
        )

        qty = quantity(to_decimal(normalized.get("source_quantity"))) or _ZERO
        unit_price = to_decimal(normalized.get("source_unit_price")) or _ZERO
        gross, gross_source = resolve_gross_item_amount(
            source_item_total=to_decimal(normalized.get("source_item_total")),
            source_quantity=qty,
            source_unit_price=unit_price,
        )
        gross = gross or _ZERO
        discount = money(to_decimal(normalized.get("source_discount_amount"))) or _ZERO
        item_freight = money(to_decimal(normalized.get("source_freight_amount")))
        item_insurance = money(to_decimal(normalized.get("source_insurance_amount")))
        item_other = money(to_decimal(normalized.get("source_other_expenses")))

        # Rateio do cabeçalho somente quando item não traz frete/despesas.
        allocated_freight = item_freight if item_freight is not None else _ZERO
        allocated_insurance = item_insurance if item_insurance is not None else _ZERO
        allocated_other = item_other if item_other is not None else _ZERO
        allocation_method = None
        if item_freight is None and item_insurance is None and item_other is None:
            if invoice.freight_amount or invoice.insurance_amount or invoice.other_expenses_amount:
                # Rateio completo exige todos os itens; aplica proporção provisória do item
                # e o agregador/reprocessamento de nota fecha o resíduo em rebuild dedicado.
                header_gross = invoice.gross_amount or invoice.total_amount or _ZERO
                if header_gross > 0 and gross > 0:
                    ratio = gross / header_gross
                    allocated_freight = money(invoice.freight_amount * ratio) or _ZERO
                    allocated_insurance = money(invoice.insurance_amount * ratio) or _ZERO
                    allocated_other = money(invoice.other_expenses_amount * ratio) or _ZERO
                    allocation_method = "PROPORTIONAL_GROSS_AMOUNT"
                    invoice.allocation_method = allocation_method

        unit = (normalized.get("source_unit") or "").strip().lower()
        volume = None
        exclusion: list[str] = []
        if unit in LITER_UNITS or unit == "":
            # Unidade vazia: não assume litros em compras (diferente de vendas combustível).
            if unit in LITER_UNITS:
                volume = qty
            else:
                exclusion.append(PurchaseMetricExclusionReason.UNIT_CONVERSION_REQUIRED.value)
        else:
            exclusion.append(PurchaseMetricExclusionReason.UNIT_CONVERSION_REQUIRED.value)

        commercial = commercial_delivered_cost(
            gross_item_amount=gross,
            discount_amount=discount,
            allocated_freight=allocated_freight,
            allocated_insurance=allocated_insurance,
            allocated_other_expenses=allocated_other,
        )
        cost_per_l = delivered_cost_per_liter(commercial_cost=commercial, volume_liters=volume)
        erp_cost = money(to_decimal(normalized.get("source_total_cost")))

        is_cancelled = bool(normalized.get("source_cancelled")) or invoice.is_cancelled
        operation = normalized.get("source_operation_type") or invoice.operation_type
        eligibility, reasons = self._item_eligibility(
            erp_product=erp_product,
            missing_product=missing_product,
            is_cancelled=is_cancelled,
            operation=operation,
            volume=volume,
            extra_reasons=exclusion,
        )

        fields = {
            "organization_id": run.organization_id,
            "station_id": run.station_id,
            "purchase_invoice_id": invoice.id,
            "source_invoice_id": source_invoice_id,
            "source_invoice_item_id": source_item_id,
            "source_product_id": normalized.get("source_product_id") or "",
            "erp_product_id": erp_product.id if erp_product else None,
            "canonical_product_id": canonical_product_id,
            "source_description": normalized.get("source_product_description"),
            "source_unit": normalized.get("source_unit"),
            "source_quantity": qty,
            "volume_liters": volume,
            "unit_price": unit_price,
            "gross_item_amount": gross,
            "gross_amount_source": gross_source.value if gross_source else None,
            "discount_amount": discount,
            "rebate_amount": _ZERO,
            "allocated_freight_amount": allocated_freight,
            "allocated_insurance_amount": allocated_insurance,
            "allocated_other_expenses": allocated_other,
            "icms_amount": money(to_decimal(normalized.get("source_icms_amount"))),
            "icms_st_amount": money(to_decimal(normalized.get("source_icms_st_amount"))),
            "fcp_amount": money(to_decimal(normalized.get("source_fcp_amount"))),
            "pis_amount": money(to_decimal(normalized.get("source_pis_amount"))),
            "cofins_amount": money(to_decimal(normalized.get("source_cofins_amount"))),
            "erp_recorded_cost": erp_cost,
            "accounting_cost": None,
            "commercial_delivered_cost": commercial,
            "delivered_cost_per_liter": cost_per_l,
            "cfop": normalized.get("source_cfop"),
            "ncm": normalized.get("source_ncm"),
            "operation_type": operation,
            "is_cancelled": is_cancelled,
            "metric_eligibility_status": eligibility,
            "metric_exclusion_reasons": reasons,
            "source_record_hash": record_hash,
            "source_updated_at": parse_source_datetime(normalized.get("source_updated_at")),
            "last_sync_run_id": run.id,
            "updated_at": now,
        }

        business_date = invoice.entry_date
        self._track_key(
            PurchaseAggregationKey(
                station_id=run.station_id,
                business_date=business_date,
                canonical_product_id=canonical_product_id,
                distributor_id=invoice.distributor_id,
            )
        )

        if existing is None:
            entity = FuelPurchaseItem(created_at=now, **fields)
            self.db.add(entity)
            await self.db.flush()
            staging.processing_status = ErpStagingStatus.APPLIED
            staging.applied_entity_type = "fuel_purchase_item"
            staging.applied_entity_id = entity.id
            return "inserted"

        if existing.source_record_hash == record_hash:
            existing.last_sync_run_id = run.id
            staging.processing_status = ErpStagingStatus.SKIPPED_UNCHANGED
            staging.applied_entity_type = "fuel_purchase_item"
            staging.applied_entity_id = existing.id
            return "unchanged"

        old_key = PurchaseAggregationKey(
            station_id=existing.station_id,
            business_date=invoice.entry_date,
            canonical_product_id=existing.canonical_product_id,
            distributor_id=invoice.distributor_id,
        )
        self._track_key(old_key)
        for key, value in fields.items():
            setattr(existing, key, value)
        staging.processing_status = ErpStagingStatus.APPLIED
        staging.applied_entity_type = "fuel_purchase_item"
        staging.applied_entity_id = existing.id
        return "updated"

    async def _apply_title(self, *, run: ErpSyncRun, staging: ErpStagingRecord, now: datetime) -> str:
        normalized = staging.normalized_payload or {}
        source_title_id = normalized.get("source_title_id")
        if not source_title_id or run.station_id is None:
            staging.processing_status = ErpStagingStatus.ERROR
            return "error"

        branch_err = await self._branch_guard(run, normalized.get("source_branch_id"))
        if branch_err:
            staging.processing_status = ErpStagingStatus.ERROR
            staging.validation_errors = [{"code": "CROSS_STATION_DATA_LEAK", "message": branch_err}]
            return "error"

        record_hash = staging.record_hash or canonical_record_hash(
            hash_payload_for_dataset(ErpDatasetCode.ACCOUNTS_PAYABLE_TITLES, normalized)
        )
        existing = await self._load_title(run.station_id, source_title_id)
        source_invoice_id = normalized.get("source_invoice_id")
        invoice = await self._load_invoice(run.organization_id, run.station_id, source_invoice_id)
        if invoice is None and normalized.get("source_document_number"):
            invoice = await self._load_invoice_by_document(
                run.organization_id, run.station_id, normalized.get("source_document_number")
            )
        link_status = (
            InvoiceLinkStatus.LINKED.value
            if invoice is not None
            else InvoiceLinkStatus.PENDING_INVOICE_LINK.value
        )

        supplier = await self._load_erp_supplier(run.station_id, normalized.get("source_supplier_id"))
        open_amount = to_decimal(normalized.get("source_open_amount"))
        paid_amount = to_decimal(normalized.get("source_paid_amount"))
        original = to_decimal(normalized.get("source_original_amount"))
        due_date = self._as_date(normalized.get("source_due_date"))
        if due_date is None or original is None or open_amount is None:
            staging.processing_status = ErpStagingStatus.ERROR
            return "error"

        is_cancelled = bool(normalized.get("source_cancelled"))
        normalized_status = normalize_title_status(
            source_status=normalized.get("source_status"),
            open_amount=open_amount,
            paid_amount=paid_amount,
            original_amount=original,
            due_date=due_date,
            business_today=date.today(),
            is_cancelled=is_cancelled,
        ).value

        fields = {
            "organization_id": run.organization_id,
            "station_id": run.station_id,
            "source_title_id": source_title_id,
            "source_invoice_id": source_invoice_id or (invoice.source_invoice_id if invoice else None),
            "purchase_invoice_id": invoice.id if invoice else None,
            "invoice_link_status": link_status,
            "source_supplier_id": normalized.get("source_supplier_id") or "",
            "erp_supplier_id": supplier.id if supplier else None,
            "distributor_id": (
                invoice.distributor_id
                if invoice
                else (supplier.distributor_id if supplier and supplier.mapping_status == MappingStatus.MAPPED else None)
            ),
            "installment_number": normalized.get("source_installment_number"),
            "document_number": normalized.get("source_document_number"),
            "issue_date": self._as_date(normalized.get("source_issue_date")),
            "due_date": due_date,
            "payment_date": self._as_date(normalized.get("source_payment_date")),
            "original_amount": money(original) or _ZERO,
            "paid_amount": money(paid_amount),
            "open_amount": money(open_amount) or _ZERO,
            "interest_amount": money(to_decimal(normalized.get("source_interest_amount"))),
            "penalty_amount": money(to_decimal(normalized.get("source_penalty_amount"))),
            "discount_amount": money(to_decimal(normalized.get("source_discount_amount"))),
            "source_status": normalized.get("source_status") or "UNKNOWN",
            "normalized_status": normalized_status,
            "is_cancelled": is_cancelled,
            "payment_method": normalized.get("source_payment_method"),
            "source_record_hash": record_hash,
            "source_updated_at": parse_source_datetime(normalized.get("source_updated_at")),
            "last_sync_run_id": run.id,
            "updated_at": now,
        }

        if existing is None:
            entity = AccountsPayableTitle(created_at=now, **fields)
            self.db.add(entity)
            await self.db.flush()
            staging.processing_status = ErpStagingStatus.APPLIED
            staging.applied_entity_type = "accounts_payable_title"
            staging.applied_entity_id = entity.id
            return "inserted"

        if existing.source_record_hash == record_hash:
            existing.last_sync_run_id = run.id
            staging.processing_status = ErpStagingStatus.SKIPPED_UNCHANGED
            staging.applied_entity_type = "accounts_payable_title"
            staging.applied_entity_id = existing.id
            return "unchanged"

        for key, value in fields.items():
            setattr(existing, key, value)
        staging.processing_status = ErpStagingStatus.APPLIED
        staging.applied_entity_type = "accounts_payable_title"
        staging.applied_entity_id = existing.id
        return "updated"

    def _track_key(self, key: PurchaseAggregationKey) -> None:
        self._affected_keys.append(key)

    async def _branch_guard(self, run: ErpSyncRun, source_branch_id: str | None) -> str | None:
        if run.station_id is None:
            return "station_id ausente na run."
        station = (
            await self.db.execute(select(Station).where(Station.id == run.station_id))
        ).scalar_one_or_none()
        if station is None or not station.erp_branch_id:
            return "Posto sem erp_branch_id."
        if source_branch_id is None:
            return "source_branch_id ausente."
        if str(source_branch_id) != str(station.erp_branch_id):
            return f"Filial {source_branch_id} difere de {station.erp_branch_id}."
        return None

    async def _load_invoice(
        self, organization_id: uuid.UUID, station_id: uuid.UUID, source_invoice_id: str | None
    ) -> FuelPurchaseInvoice | None:
        if not source_invoice_id:
            return None
        return (
            await self.db.execute(
                select(FuelPurchaseInvoice).where(
                    FuelPurchaseInvoice.organization_id == organization_id,
                    FuelPurchaseInvoice.station_id == station_id,
                    FuelPurchaseInvoice.source_invoice_id == source_invoice_id,
                )
            )
        ).scalar_one_or_none()

    async def _load_invoice_by_document(
        self, organization_id: uuid.UUID, station_id: uuid.UUID, document_number: str | None
    ) -> FuelPurchaseInvoice | None:
        if not document_number:
            return None
        return (
            await self.db.execute(
                select(FuelPurchaseInvoice).where(
                    FuelPurchaseInvoice.organization_id == organization_id,
                    FuelPurchaseInvoice.station_id == station_id,
                    FuelPurchaseInvoice.source_document_number == str(document_number),
                ).limit(1)
            )
        ).scalar_one_or_none()

    async def _load_item(
        self, station_id: uuid.UUID, source_invoice_id: str, source_item_id: str
    ) -> FuelPurchaseItem | None:
        return (
            await self.db.execute(
                select(FuelPurchaseItem).where(
                    FuelPurchaseItem.station_id == station_id,
                    FuelPurchaseItem.source_invoice_id == source_invoice_id,
                    FuelPurchaseItem.source_invoice_item_id == source_item_id,
                )
            )
        ).scalar_one_or_none()

    async def _load_title(self, station_id: uuid.UUID, source_title_id: str) -> AccountsPayableTitle | None:
        return (
            await self.db.execute(
                select(AccountsPayableTitle).where(
                    AccountsPayableTitle.station_id == station_id,
                    AccountsPayableTitle.source_title_id == source_title_id,
                )
            )
        ).scalar_one_or_none()

    async def _load_erp_product(self, station_id: uuid.UUID, source_product_id: str | None) -> ErpProduct | None:
        if not source_product_id:
            return None
        return (
            await self.db.execute(
                select(ErpProduct).where(
                    ErpProduct.station_id == station_id,
                    ErpProduct.erp_product_id == source_product_id,
                )
            )
        ).scalar_one_or_none()

    async def _load_erp_supplier(self, station_id: uuid.UUID, source_supplier_id: str | None) -> ErpSupplier | None:
        if not source_supplier_id:
            return None
        return (
            await self.db.execute(
                select(ErpSupplier).where(
                    ErpSupplier.station_id == station_id,
                    ErpSupplier.erp_entity_id == source_supplier_id,
                )
            )
        ).scalar_one_or_none()

    @staticmethod
    def _as_date(value: Any) -> date | None:
        if value is None:
            return None
        if isinstance(value, date) and not isinstance(value, datetime):
            return value
        if isinstance(value, datetime):
            return value.date()
        text = str(value)[:10]
        try:
            return date.fromisoformat(text)
        except ValueError:
            return None

    @staticmethod
    def _invoice_eligibility(*, is_cancelled: bool, operation: str) -> tuple[str, list[str] | None]:
        if is_cancelled:
            return PurchaseMetricEligibilityStatus.EXCLUDED.value, [
                PurchaseMetricExclusionReason.CANCELLED_INVOICE.value
            ]
        if operation == PurchaseOperationType.PURCHASE_RETURN.value:
            return PurchaseMetricEligibilityStatus.ELIGIBLE.value, [
                PurchaseMetricExclusionReason.PURCHASE_RETURN.value
            ]
        return PurchaseMetricEligibilityStatus.ELIGIBLE.value, None

    @staticmethod
    def _item_eligibility(
        *,
        erp_product: ErpProduct | None,
        missing_product: bool,
        is_cancelled: bool,
        operation: str,
        volume: Decimal | None,
        extra_reasons: list[str],
    ) -> tuple[str, list[str] | None]:
        reasons = list(extra_reasons)
        if is_cancelled:
            reasons.append(PurchaseMetricExclusionReason.CANCELLED_INVOICE.value)
        if missing_product or erp_product is None:
            reasons.append(PurchaseMetricExclusionReason.MISSING_ERP_PRODUCT_REFERENCE.value)
        elif erp_product.mapping_status == MappingStatus.PENDING:
            reasons.append(PurchaseMetricExclusionReason.UNMAPPED_PRODUCT.value)
        elif erp_product.mapping_status == MappingStatus.IGNORED:
            reasons.append(PurchaseMetricExclusionReason.IGNORED_PRODUCT.value)
        if operation == PurchaseOperationType.PURCHASE_RETURN.value:
            reasons.append(PurchaseMetricExclusionReason.PURCHASE_RETURN.value)
        if volume is None or volume == 0:
            if PurchaseMetricExclusionReason.UNIT_CONVERSION_REQUIRED.value not in reasons:
                reasons.append(PurchaseMetricExclusionReason.INVALID_QUANTITY.value)

        if reasons and any(
            r
            in {
                PurchaseMetricExclusionReason.CANCELLED_INVOICE.value,
                PurchaseMetricExclusionReason.MISSING_ERP_PRODUCT_REFERENCE.value,
                PurchaseMetricExclusionReason.UNMAPPED_PRODUCT.value,
                PurchaseMetricExclusionReason.IGNORED_PRODUCT.value,
                PurchaseMetricExclusionReason.UNIT_CONVERSION_REQUIRED.value,
                PurchaseMetricExclusionReason.INVALID_QUANTITY.value,
            }
            for r in reasons
        ):
            # Retorno permanece elegível com sinal analítico, mas cancelado/unmapped exclui.
            if PurchaseMetricExclusionReason.CANCELLED_INVOICE.value in reasons:
                return PurchaseMetricEligibilityStatus.EXCLUDED.value, reasons
            if erp_product is None or erp_product.mapping_status != MappingStatus.MAPPED:
                return PurchaseMetricEligibilityStatus.EXCLUDED.value, reasons
            if volume is None:
                return PurchaseMetricEligibilityStatus.EXCLUDED.value, reasons
            return PurchaseMetricEligibilityStatus.ELIGIBLE_WITH_WARNINGS.value, reasons
        return PurchaseMetricEligibilityStatus.ELIGIBLE.value, reasons or None
