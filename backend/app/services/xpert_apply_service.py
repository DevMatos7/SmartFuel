from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.master_data_enums import MappingSource, MappingStatus
from app.core.xpert_sync_enums import ErpDatasetCode, ErpStagingStatus
from app.integrations.xpert.canonical_hash import canonical_record_hash
from app.integrations.xpert.normalizers import hash_payload_for_dataset
from app.models.distributor import ErpSupplier
from app.models.erp_integration import ErpStagingRecord, ErpSyncRun
from app.models.erp_product import ErpProduct
from app.services.fuel_sales_apply_service import FuelSalesApplyService
from app.services.fuel_purchases_apply_service import FuelPurchasesApplyService

SOURCE_SYSTEM = "XPERT"


class XpertApplyService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.fuel_sales_apply = FuelSalesApplyService(db)
        self.fuel_purchases_apply = FuelPurchasesApplyService(db)

    @property
    def pending_aggregation_keys(self):
        return self.fuel_sales_apply._affected_keys  # noqa: SLF001

    @property
    def pending_purchase_aggregation_keys(self):
        return self.fuel_purchases_apply._affected_keys  # noqa: SLF001

    def clear_aggregation_keys(self) -> None:
        self.fuel_sales_apply._affected_keys.clear()  # noqa: SLF001
        self.fuel_purchases_apply._affected_keys.clear()  # noqa: SLF001

    async def apply_staging_record(
        self,
        *,
        run: ErpSyncRun,
        staging: ErpStagingRecord,
        now: datetime,
    ) -> str:
        if staging.dataset_code == ErpDatasetCode.PRODUCTS:
            return await self._apply_product(run=run, staging=staging, now=now)
        if staging.dataset_code == ErpDatasetCode.SUPPLIERS:
            return await self._apply_supplier(run=run, staging=staging, now=now)
        if staging.dataset_code in (
            ErpDatasetCode.PAYMENT_METHODS,
            ErpDatasetCode.FUEL_SALES_ITEMS,
            ErpDatasetCode.FUEL_RETAIL_PRICES,
        ):
            result = await self.fuel_sales_apply.apply_staging_record(run=run, staging=staging, now=now)
            return result.outcome
        if staging.dataset_code in (
            ErpDatasetCode.FUEL_PURCHASE_INVOICES,
            ErpDatasetCode.FUEL_PURCHASE_ITEMS,
            ErpDatasetCode.ACCOUNTS_PAYABLE_TITLES,
        ):
            result = await self.fuel_purchases_apply.apply_staging_record(run=run, staging=staging, now=now)
            return result.outcome
        staging.processing_status = ErpStagingStatus.SKIPPED_UNCHANGED
        return "skipped"

    async def _apply_product(self, *, run: ErpSyncRun, staging: ErpStagingRecord, now: datetime) -> str:
        normalized = staging.normalized_payload or {}
        product_id = normalized.get("erp_product_id")
        if not product_id:
            staging.processing_status = ErpStagingStatus.ERROR
            return "error"

        record_hash = staging.record_hash or canonical_record_hash(
            hash_payload_for_dataset(ErpDatasetCode.PRODUCTS, normalized)
        )
        existing = await self._load_product(run.station_id, product_id)
        if existing is None:
            entity = ErpProduct(
                organization_id=run.organization_id,
                station_id=run.station_id,
                erp_product_id=product_id,
                erp_product_code=normalized.get("erp_product_code"),
                erp_description=normalized.get("erp_description") or product_id,
                erp_unit=normalized.get("erp_unit"),
                erp_group_id=normalized.get("erp_group_id"),
                erp_group_name=normalized.get("erp_group_name"),
                erp_subgroup_id=normalized.get("erp_subgroup_id"),
                erp_subgroup_name=normalized.get("erp_subgroup_name"),
                mapping_status=MappingStatus.PENDING,
                mapping_source=MappingSource.ERP_SYNC,
                raw_payload=normalized,
                last_synced_at=now,
                active=True,
                source_system=SOURCE_SYSTEM,
                source_record_hash=record_hash,
                source_updated_at=staging.source_updated_at,
                source_last_seen_at=now,
                source_active=staging.source_active if staging.source_active is not None else True,
                last_sync_run_id=run.id,
            )
            self.db.add(entity)
            await self.db.flush()
            staging.applied_entity_type = "erp_product"
            staging.applied_entity_id = entity.id
            staging.processing_status = ErpStagingStatus.APPLIED
            staging.applied_at = now
            return "inserted"

        if existing.mapping_status == MappingStatus.IGNORED:
            self._update_product_origin_fields(existing, normalized, staging, record_hash, run, now)
            staging.applied_entity_type = "erp_product"
            staging.applied_entity_id = existing.id
            staging.processing_status = ErpStagingStatus.APPLIED
            staging.applied_at = now
            return "updated"

        if existing.source_record_hash == record_hash:
            existing.source_last_seen_at = now
            existing.last_sync_run_id = run.id
            staging.applied_entity_type = "erp_product"
            staging.applied_entity_id = existing.id
            staging.processing_status = ErpStagingStatus.SKIPPED_UNCHANGED
            staging.applied_at = now
            return "unchanged"

        self._update_product_origin_fields(existing, normalized, staging, record_hash, run, now)
        staging.applied_entity_type = "erp_product"
        staging.applied_entity_id = existing.id
        staging.processing_status = ErpStagingStatus.APPLIED
        staging.applied_at = now
        return "updated"

    def _update_product_origin_fields(
        self,
        existing: ErpProduct,
        normalized: dict,
        staging: ErpStagingRecord,
        record_hash: str,
        run: ErpSyncRun,
        now: datetime,
    ) -> None:
        existing.erp_product_code = normalized.get("erp_product_code")
        existing.erp_description = normalized.get("erp_description") or existing.erp_description
        existing.erp_unit = normalized.get("erp_unit")
        existing.erp_group_id = normalized.get("erp_group_id")
        existing.erp_group_name = normalized.get("erp_group_name")
        existing.erp_subgroup_id = normalized.get("erp_subgroup_id")
        existing.erp_subgroup_name = normalized.get("erp_subgroup_name")
        existing.raw_payload = normalized
        existing.last_synced_at = now
        existing.updated_at = now
        existing.source_system = SOURCE_SYSTEM
        existing.source_record_hash = record_hash
        existing.source_updated_at = staging.source_updated_at
        existing.source_last_seen_at = now
        if staging.source_active is not None:
            existing.source_active = staging.source_active
        existing.last_sync_run_id = run.id
        if existing.mapping_status == MappingStatus.PENDING:
            existing.mapping_source = MappingSource.ERP_SYNC

    async def _apply_supplier(self, *, run: ErpSyncRun, staging: ErpStagingRecord, now: datetime) -> str:
        normalized = staging.normalized_payload or {}
        entity_id = normalized.get("erp_entity_id")
        if not entity_id:
            staging.processing_status = ErpStagingStatus.ERROR
            return "error"

        record_hash = staging.record_hash or canonical_record_hash(
            hash_payload_for_dataset(ErpDatasetCode.SUPPLIERS, normalized)
        )
        existing = await self._load_supplier(run.station_id, entity_id)
        if existing is None:
            entity = ErpSupplier(
                organization_id=run.organization_id,
                station_id=run.station_id,
                erp_entity_id=entity_id,
                erp_entity_code=normalized.get("erp_entity_code"),
                erp_name=normalized.get("erp_name") or entity_id,
                erp_cnpj=normalized.get("erp_cnpj"),
                mapping_status=MappingStatus.PENDING,
                mapping_source=MappingSource.ERP_SYNC,
                raw_payload=normalized,
                last_synced_at=now,
                active=True,
                source_system=SOURCE_SYSTEM,
                source_record_hash=record_hash,
                source_updated_at=staging.source_updated_at,
                source_last_seen_at=now,
                source_active=staging.source_active if staging.source_active is not None else True,
                last_sync_run_id=run.id,
            )
            self.db.add(entity)
            await self.db.flush()
            staging.applied_entity_type = "erp_supplier"
            staging.applied_entity_id = entity.id
            staging.processing_status = ErpStagingStatus.APPLIED
            staging.applied_at = now
            return "inserted"

        if existing.mapping_status == MappingStatus.IGNORED:
            self._update_supplier_origin_fields(existing, normalized, staging, record_hash, run, now)
            staging.applied_entity_type = "erp_supplier"
            staging.applied_entity_id = existing.id
            staging.processing_status = ErpStagingStatus.APPLIED
            staging.applied_at = now
            return "updated"

        if existing.source_record_hash == record_hash:
            existing.source_last_seen_at = now
            existing.last_sync_run_id = run.id
            staging.applied_entity_type = "erp_supplier"
            staging.applied_entity_id = existing.id
            staging.processing_status = ErpStagingStatus.SKIPPED_UNCHANGED
            staging.applied_at = now
            return "unchanged"

        self._update_supplier_origin_fields(existing, normalized, staging, record_hash, run, now)
        staging.applied_entity_type = "erp_supplier"
        staging.applied_entity_id = existing.id
        staging.processing_status = ErpStagingStatus.APPLIED
        staging.applied_at = now
        return "updated"

    def _update_supplier_origin_fields(
        self,
        existing: ErpSupplier,
        normalized: dict,
        staging: ErpStagingRecord,
        record_hash: str,
        run: ErpSyncRun,
        now: datetime,
    ) -> None:
        existing.erp_entity_code = normalized.get("erp_entity_code")
        existing.erp_name = normalized.get("erp_name") or existing.erp_name
        existing.erp_cnpj = normalized.get("erp_cnpj")
        existing.raw_payload = normalized
        existing.last_synced_at = now
        existing.updated_at = now
        existing.source_system = SOURCE_SYSTEM
        existing.source_record_hash = record_hash
        existing.source_updated_at = staging.source_updated_at
        existing.source_last_seen_at = now
        if staging.source_active is not None:
            existing.source_active = staging.source_active
        existing.last_sync_run_id = run.id
        if existing.mapping_status == MappingStatus.PENDING:
            existing.mapping_source = MappingSource.ERP_SYNC

    async def mark_absent_by_dataset(
        self,
        *,
        run: ErpSyncRun,
        dataset_code: str,
        seen_keys: set[str],
        now: datetime,
    ) -> int:
        if run.station_id is None:
            return 0
        marked = 0
        if dataset_code == ErpDatasetCode.PRODUCTS:
            result = await self.db.execute(
                select(ErpProduct).where(
                    ErpProduct.station_id == run.station_id,
                    ErpProduct.source_system == SOURCE_SYSTEM,
                    ErpProduct.source_active.is_(True),
                )
            )
            for product in result.scalars().all():
                if product.erp_product_id not in seen_keys:
                    product.source_active = False
                    product.source_last_seen_at = now
                    product.last_sync_run_id = run.id
                    marked += 1
        elif dataset_code == ErpDatasetCode.SUPPLIERS:
            result = await self.db.execute(
                select(ErpSupplier).where(
                    ErpSupplier.station_id == run.station_id,
                    ErpSupplier.source_system == SOURCE_SYSTEM,
                    ErpSupplier.source_active.is_(True),
                )
            )
            for supplier in result.scalars().all():
                if supplier.erp_entity_id not in seen_keys:
                    supplier.source_active = False
                    supplier.source_last_seen_at = now
                    supplier.last_sync_run_id = run.id
                    marked += 1
        elif dataset_code == ErpDatasetCode.PAYMENT_METHODS:
            marked = await self.fuel_sales_apply.mark_absent_payment_methods(
                run=run, seen_keys=seen_keys, now=now
            )
        return marked

    async def _load_product(self, station_id: uuid.UUID | None, erp_product_id: str) -> ErpProduct | None:
        if station_id is None:
            return None
        result = await self.db.execute(
            select(ErpProduct).where(
                ErpProduct.station_id == station_id,
                ErpProduct.erp_product_id == erp_product_id,
            )
        )
        return result.scalar_one_or_none()

    async def _load_supplier(self, station_id: uuid.UUID | None, erp_entity_id: str) -> ErpSupplier | None:
        if station_id is None:
            return None
        result = await self.db.execute(
            select(ErpSupplier).where(
                ErpSupplier.station_id == station_id,
                ErpSupplier.erp_entity_id == erp_entity_id,
            )
        )
        return result.scalar_one_or_none()
