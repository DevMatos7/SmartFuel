from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.xpert_sync_enums import (
    ErpConnectionStatus,
    ErpContractStatus,
    ErpDatasetCode,
    ErpSecurityStatus,
    ErpStagingStatus,
    ErpSyncMode,
    ErpSyncPhase,
    ErpSyncRunStatus,
    ErpSyncTrigger,
)
from app.integrations.xpert.canonical_hash import canonical_record_hash
from app.integrations.xpert.direct_sqlserver import create_datasource
from app.integrations.xpert.datasource import XpertDataSource
from app.integrations.xpert.normalizers import (
    hash_payload_for_dataset,
    json_safe,
    normalize_row,
    parse_source_datetime,
    source_key_for_row,
)
from app.integrations.xpert.query_guard import QueryChangedError, current_query_hash, ensure_dataset_query_unchanged
from app.integrations.xpert.secret_resolver import load_query_file
from app.integrations.xpert.sync_lock import sync_lock_key
from app.integrations.xpert.odbc_health import driver_available
from app.models.erp_integration import ErpDataset, ErpSource, ErpStagingRecord, ErpSyncCheckpoint, ErpSyncError, ErpSyncRun
from app.models.station import Station
from app.services.xpert_apply_service import XpertApplyService
from app.services.xpert_checkpoint_service import XpertCheckpointService
from app.services.xpert_worker_service import XpertWorkerService
from app.utils.brazilian_document import SupplierDocumentType


ACTIVE_STATUSES = {
    ErpSyncRunStatus.QUEUED,
    ErpSyncRunStatus.CONNECTING,
    ErpSyncRunStatus.EXTRACTING,
    ErpSyncRunStatus.STAGING,
    ErpSyncRunStatus.VALIDATING,
    ErpSyncRunStatus.APPLYING,
    ErpSyncRunStatus.CANCELLATION_REQUESTED,
}


class XpertSyncService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.apply_service = XpertApplyService(db)
        self.checkpoint_service = XpertCheckpointService(db)
        self.worker_service = XpertWorkerService(db)

    async def claim_next_run(self, worker_id: str) -> ErpSyncRun | None:
        result = await self.db.execute(
            select(ErpSyncRun)
            .where(ErpSyncRun.status == ErpSyncRunStatus.QUEUED)
            .order_by(ErpSyncRun.created_at.asc())
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        run = result.scalar_one_or_none()
        if run is None:
            return None
        run.status = ErpSyncRunStatus.CONNECTING
        run.worker_id = worker_id
        run.started_at = datetime.now(UTC)
        run.last_heartbeat_at = run.started_at
        await self.db.flush()
        return run

    async def process_run(self, run_id: uuid.UUID, *, datasource: XpertDataSource | None = None) -> ErpSyncRun:
        result = await self.db.execute(
            select(ErpSyncRun)
            .where(ErpSyncRun.id == run_id)
            .options(selectinload(ErpSyncRun.staging_records))
        )
        run = result.scalar_one_or_none()
        if run is None:
            raise ValueError(f"Run not found: {run_id}")

        source = await self.db.get(ErpSource, run.erp_source_id)
        dataset = await self.db.get(ErpDataset, run.erp_dataset_id)
        station = await self.db.get(Station, run.station_id) if run.station_id else None
        if source is None or dataset is None:
            run.status = ErpSyncRunStatus.FAILED
            run.error_code = "XPERT_MISCONFIGURED"
            run.error_message = "Fonte ou dataset não encontrado."
            run.finished_at = datetime.now(UTC)
            return run

        if settings.app_env == "production" and (
            settings.xpert_allow_unsafe_privileges or source.security_status == ErpSecurityStatus.UNSAFE
        ):
            run.status = ErpSyncRunStatus.FAILED
            run.error_code = "UNSAFE_SOURCE_BLOCKED_IN_PRODUCTION"
            run.error_message = "Fonte insegura ou override bloqueado em produção."
            run.finished_at = datetime.now(UTC)
            return run

        if source.security_status == ErpSecurityStatus.UNSAFE and run.trigger_type == ErpSyncTrigger.SCHEDULED:
            run.status = ErpSyncRunStatus.FAILED
            run.error_code = "UNSAFE_SOURCE_SCHEDULE_BLOCKED"
            run.error_message = "Agenda bloqueada para fonte UNSAFE."
            run.finished_at = datetime.now(UTC)
            return run

        lock_key = sync_lock_key(
            source_id=source.id, dataset_id=dataset.id, station_id=run.station_id
        )
        locked = await self._try_advisory_lock(lock_key)
        if not locked:
            run.status = ErpSyncRunStatus.SKIPPED_LOCKED
            run.finished_at = datetime.now(UTC)
            return run

        ds: XpertDataSource | None = datasource
        seen_keys: set[str] = set()
        duplicate_keys: set[str] = set()
        now = datetime.now(UTC)

        try:
            if datasource is None:
                odbc_ok, odbc_msg = driver_available()
                if not odbc_ok:
                    raise RuntimeError(odbc_msg or "Driver ODBC indisponível.")

            try:
                ensure_dataset_query_unchanged(dataset)
            except QueryChangedError as exc:
                raise RuntimeError(str(exc)) from exc

            if dataset.contract_status != ErpContractStatus.VALID:
                raise RuntimeError("Contrato do dataset não validado.")

            if dataset.code == ErpDatasetCode.STATIONS:
                raise RuntimeError("Dataset STATIONS permanece desabilitado até validação do DBA.")

            if dataset.code in (
                ErpDatasetCode.PRODUCTS,
                ErpDatasetCode.SUPPLIERS,
                ErpDatasetCode.FUEL_SALES_ITEMS,
                ErpDatasetCode.FUEL_RETAIL_PRICES,
                ErpDatasetCode.PAYMENT_METHODS,
            ):
                if station is None or not station.erp_branch_id:
                    raise RuntimeError("Posto sem erp_branch_id configurado.")

            self.apply_service.clear_aggregation_keys()

            run.status = ErpSyncRunStatus.EXTRACTING
            checkpoint = await self.checkpoint_service.get_or_create(
                source=source, dataset=dataset, station_id=run.station_id
            )
            run.checkpoint_before = checkpoint.watermark_value

            ds = create_datasource(source, fake=datasource)
            source_upper = ds.get_source_utc_time()
            run.source_upper_bound = source_upper
            preset_window_start = run.window_start
            preset_window_end = run.window_end
            # Carga histórica com intervalo explícito: usa a janela do run e NÃO avança checkpoint.
            explicit_history_window = preset_window_start is not None and preset_window_end is not None
            if explicit_history_window:
                overlap = timedelta(seconds=dataset.overlap_seconds)
                window_start = preset_window_start - overlap
                window_end = preset_window_end
            else:
                window_start, window_end = self.checkpoint_service.compute_window(
                    dataset=dataset, checkpoint=checkpoint, source_upper_bound=source_upper
                )
            run.window_start = window_start
            run.window_end = window_end

            sql = load_query_file(dataset.query_file)
            params = self._build_params(
                dataset=dataset,
                station=station,
                window_start=window_start,
                window_end=window_end,
                checkpoint=checkpoint,
            )

            run.status = ErpSyncRunStatus.STAGING
            keys_in_run: dict[str, int] = {}
            for batch in ds.stream_rows(sql, params, batch_size=dataset.batch_size):
                if await self._is_cancel_requested(run.id):
                    run.status = ErpSyncRunStatus.CANCELLED
                    run.finished_at = datetime.now(UTC)
                    return run

                await self.worker_service.touch_run_heartbeat(run.id)
                run.last_heartbeat_at = datetime.now(UTC)

                run.current_batch += 1
                for raw in batch:
                    run.rows_read += 1
                    normalized = normalize_row(dataset.code, raw)
                    try:
                        source_key = source_key_for_row(dataset.code, normalized)
                    except (KeyError, TypeError, ValueError):
                        await self._record_row_error(
                            run, None, ErpSyncPhase.STAGE, "MISSING_SOURCE_KEY", "Chave de origem ausente.", raw
                        )
                        run.rows_error += 1
                        continue

                    keys_in_run[source_key] = keys_in_run.get(source_key, 0) + 1
                    if keys_in_run[source_key] > 1:
                        duplicate_keys.add(source_key)
                        continue

                    hash_payload = hash_payload_for_dataset(dataset.code, normalized)
                    record_hash = canonical_record_hash(hash_payload)
                    staging = ErpStagingRecord(
                        sync_run_id=run.id,
                        organization_id=run.organization_id,
                        station_id=run.station_id,
                        dataset_code=dataset.code,
                        source_key=source_key,
                        source_updated_at=parse_source_datetime(normalized.get("source_updated_at")),
                        source_active=normalized.get("source_active"),
                        raw_payload=json_safe(raw),
                        normalized_payload=json_safe(normalized),
                        record_hash=record_hash,
                        processing_status=ErpStagingStatus.RECEIVED,
                        created_at=now,
                    )
                    self.db.add(staging)
                    run.rows_staged += 1
                    seen_keys.add(source_key)

                await self.db.flush()

            if duplicate_keys:
                for key in duplicate_keys:
                    await self._record_row_error(
                        run,
                        key,
                        ErpSyncPhase.STAGE,
                        "DUPLICATE_SOURCE_KEY",
                        "Chave duplicada na origem.",
                        {"source_key": key},
                    )
                run.rows_error += len(duplicate_keys)

            run.status = ErpSyncRunStatus.VALIDATING
            staging_rows = await self._load_staging(run.id)
            for staging in staging_rows:
                if staging.source_key in duplicate_keys:
                    staging.processing_status = ErpStagingStatus.ERROR
                    continue
                errors = self._validate_row(dataset.code, staging.normalized_payload or {})
                if errors:
                    staging.validation_errors = errors
                    staging.processing_status = ErpStagingStatus.QUARANTINED
                    staging.validated_at = now
                    run.rows_quarantined += 1
                    for err in errors:
                        await self._record_row_error(
                            run,
                            staging.source_key,
                            ErpSyncPhase.VALIDATE,
                            err["code"],
                            err["message"],
                            err,
                            staging.id,
                        )
                else:
                    staging.processing_status = ErpStagingStatus.VALIDATED
                    staging.validated_at = now
                    run.rows_valid += 1

            run.status = ErpSyncRunStatus.APPLYING
            for staging in staging_rows:
                if staging.processing_status not in (
                    ErpStagingStatus.VALIDATED,
                    ErpStagingStatus.RECEIVED,
                ):
                    continue
                if staging.processing_status == ErpStagingStatus.RECEIVED:
                    staging.processing_status = ErpStagingStatus.VALIDATED
                outcome = await self.apply_service.apply_staging_record(run=run, staging=staging, now=now)
                if outcome == "inserted":
                    run.rows_inserted += 1
                    run.rows_applied += 1
                elif outcome == "updated":
                    run.rows_updated += 1
                    run.rows_applied += 1
                elif outcome == "unchanged":
                    run.rows_unchanged += 1
                elif outcome == "waiting_for_invoice":
                    run.rows_unchanged += 1
                elif outcome == "error":
                    run.rows_error += 1
                else:
                    run.rows_unchanged += 1

            if dataset.code == ErpDatasetCode.FUEL_SALES_ITEMS and self.apply_service.pending_aggregation_keys:
                from app.services.fuel_sales_aggregation_service import FuelSalesAggregationService

                agg = FuelSalesAggregationService(self.db)
                await agg.rebuild_keys(
                    organization_id=run.organization_id,
                    keys=list(self.apply_service.pending_aggregation_keys),
                    sync_run_id=run.id,
                )
                self.apply_service.clear_aggregation_keys()

            if dataset.code == ErpDatasetCode.FUEL_PURCHASE_ITEMS and self.apply_service.pending_purchase_aggregation_keys:
                from app.services.fuel_purchase_aggregation_service import FuelPurchaseAggregationService

                agg = FuelPurchaseAggregationService(self.db)
                await agg.rebuild_keys(
                    organization_id=run.organization_id,
                    keys=list(self.apply_service.pending_purchase_aggregation_keys),
                    sync_run_id=run.id,
                )
                self.apply_service.clear_aggregation_keys()

            if dataset.code == ErpDatasetCode.FUEL_PURCHASE_INVOICES:
                await self.apply_service.fuel_purchases_apply.reprocess_waiting_items(run=run, now=now)
                await self.apply_service.fuel_purchases_apply.reconcile_title_links(run=run)

            if dataset.code == ErpDatasetCode.ACCOUNTS_PAYABLE_TITLES:
                await self.apply_service.fuel_purchases_apply.reconcile_title_links(run=run)
            if run.rows_error > 0 or run.rows_quarantined > 0:
                run.status = ErpSyncRunStatus.PARTIAL
            else:
                run.status = ErpSyncRunStatus.COMPLETED

            if (
                run.status == ErpSyncRunStatus.COMPLETED
                and run.sync_mode in (ErpSyncMode.FULL, ErpSyncMode.FULL_SNAPSHOT_HASH)
                and not duplicate_keys
            ):
                run.rows_marked_inactive = await self.apply_service.mark_absent_by_dataset(
                    run=run, dataset_code=dataset.code, seen_keys=seen_keys, now=now
                )

            if (
                not explicit_history_window
                and self.checkpoint_service.should_advance(run, dataset)
            ):
                watermark = self.checkpoint_service.watermark_for_run(run, dataset)
                await self.checkpoint_service.advance_after_success(
                    checkpoint=checkpoint,
                    run=run,
                    new_watermark=watermark,
                    source_upper_bound=source_upper,
                )
                source.last_success_at = now
            elif explicit_history_window:
                # Homologação histórica: preserva watermark anterior; não cria avanço incremental.
                run.checkpoint_after = run.checkpoint_before
                source.last_success_at = now

        except Exception as exc:
            run.status = ErpSyncRunStatus.FAILED
            if isinstance(exc, RuntimeError) and "alterada após" in str(exc):
                run.error_code = "QUERY_CHANGED_AFTER_VALIDATION"
            elif "ODBC" in str(exc) or "Driver ODBC" in str(exc):
                run.error_code = "XPERT_ODBC_DRIVER_MISSING"
            else:
                run.error_code = "XPERT_SYNC_FAILED"
            run.error_message = str(exc)[:1000]
            run.finished_at = datetime.now(UTC)
        finally:
            if ds is not None and datasource is None:
                ds.close()
            await self._release_advisory_lock(lock_key)
            if run.finished_at is None:
                run.finished_at = datetime.now(UTC)

        return run

    async def request_cancel(self, run: ErpSyncRun) -> ErpSyncRun:
        if run.status not in ACTIVE_STATUSES:
            return run
        run.cancellation_requested_at = datetime.now(UTC)
        run.status = ErpSyncRunStatus.CANCELLATION_REQUESTED
        return run

    async def create_scheduled_runs(self) -> int:
        now = datetime.now(UTC)
        result = await self.db.execute(
            select(ErpDataset)
            .join(ErpSource)
            .where(
                ErpDataset.schedule_enabled.is_(True),
                ErpDataset.enabled.is_(True),
                ErpDataset.contract_status == ErpContractStatus.VALID,
                ErpDataset.code != ErpDatasetCode.STATIONS,
                ErpSource.enabled.is_(True),
                ErpSource.connection_status == ErpConnectionStatus.CONNECTED,
                ErpSource.security_status != ErpSecurityStatus.UNSAFE,
                ErpDataset.next_scheduled_at <= now,
            )
            .options(selectinload(ErpDataset.source))
            .with_for_update(skip_locked=True)
        )
        created = 0
        for dataset in result.scalars().all():
            if dataset.query_hash != current_query_hash(dataset.query_file):
                dataset.contract_status = ErpContractStatus.PENDING_VALIDATION
                dataset.schedule_enabled = False
                continue
            stations = await self.db.execute(
                select(Station).where(Station.organization_id == dataset.source.organization_id)
            )
            for station in stations.scalars().all():
                if dataset.sync_mode in (ErpSyncMode.INCREMENTAL_TIMESTAMP, ErpSyncMode.INCREMENTAL_ID):
                    cp_result = await self.db.execute(
                        select(ErpSyncCheckpoint).where(
                            ErpSyncCheckpoint.erp_source_id == dataset.erp_source_id,
                            ErpSyncCheckpoint.erp_dataset_id == dataset.id,
                            ErpSyncCheckpoint.station_id == station.id,
                        )
                    )
                    checkpoint = cp_result.scalar_one_or_none()
                    if checkpoint is None or checkpoint.last_success_at is None:
                        continue
                if await self._has_active_run(dataset.erp_source_id, dataset.id, station.id):
                    continue
                run = ErpSyncRun(
                    organization_id=dataset.source.organization_id,
                    erp_source_id=dataset.erp_source_id,
                    erp_dataset_id=dataset.id,
                    station_id=station.id,
                    trigger_type="SCHEDULED",
                    sync_mode=dataset.sync_mode,
                    status=ErpSyncRunStatus.QUEUED,
                    query_hash=dataset.query_hash,
                    created_at=now,
                )
                self.db.add(run)
                created += 1
            interval = dataset.schedule_interval_minutes or 60
            dataset.next_scheduled_at = now + timedelta(minutes=interval)
        await self.db.flush()
        return created

    def _build_params(
        self,
        *,
        dataset: ErpDataset,
        station: Station | None,
        window_start: datetime | None,
        window_end: datetime | None,
        checkpoint,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if station and station.erp_branch_id:
            params["station_erp_id"] = station.erp_branch_id
        if window_start is not None:
            params["window_start"] = window_start
        if window_end is not None:
            params["window_end"] = window_end
        if checkpoint.watermark_value and dataset.sync_mode == ErpSyncMode.INCREMENTAL_ID:
            params["last_source_id"] = checkpoint.watermark_value
        params["batch_limit"] = dataset.batch_size
        return params

    def _validate_row(self, dataset_code: str, normalized: dict[str, Any]) -> list[dict[str, str]]:
        errors: list[dict[str, str]] = []
        if dataset_code == ErpDatasetCode.PRODUCTS:
            if not normalized.get("erp_product_id"):
                errors.append({"code": "MISSING_SOURCE_KEY", "message": "source_product_id obrigatório.", "field": "source_product_id"})
            if not normalized.get("erp_description"):
                errors.append({"code": "MISSING_DESCRIPTION", "message": "source_description obrigatório.", "field": "source_description"})
        elif dataset_code == ErpDatasetCode.SUPPLIERS:
            if not normalized.get("erp_entity_id"):
                errors.append({"code": "MISSING_SOURCE_KEY", "message": "source_supplier_id obrigatório.", "field": "source_supplier_id"})
            if not normalized.get("erp_name"):
                errors.append({"code": "MISSING_NAME", "message": "source_name obrigatório.", "field": "source_name"})
            doc_type = normalized.get("erp_document_type")
            if doc_type == SupplierDocumentType.INVALID.value:
                reason = normalized.get("document_diagnostic") or "OTHER_FORMAT"
                errors.append(
                    {
                        "code": "INVALID_CNPJ",
                        "message": f"Documento inválido ({reason}).",
                        "field": "source_cnpj",
                        "reason": reason,
                    }
                )
        elif dataset_code == ErpDatasetCode.PAYMENT_METHODS:
            if not normalized.get("source_payment_method_id"):
                errors.append({"code": "MISSING_SOURCE_KEY", "message": "source_payment_method_id obrigatório.", "field": "source_payment_method_id"})
            if not normalized.get("source_payment_method_name"):
                errors.append({"code": "MISSING_NAME", "message": "source_payment_method_name obrigatório.", "field": "source_payment_method_name"})
        elif dataset_code == ErpDatasetCode.FUEL_SALES_ITEMS:
            required = (
                ("source_sale_id", "source_sale_id"),
                ("source_sale_item_id", "source_sale_item_id"),
                ("source_product_id", "source_product_id"),
            )
            for key, label in required:
                if not normalized.get(key):
                    errors.append({"code": "MISSING_FIELD", "message": f"{label} obrigatório.", "field": label})
            if normalized.get("source_sale_datetime") is None:
                errors.append({"code": "MISSING_FIELD", "message": "source_sale_datetime obrigatório.", "field": "source_sale_datetime"})
            if normalized.get("source_business_date") is None:
                errors.append({"code": "MISSING_FIELD", "message": "source_business_date obrigatório.", "field": "source_business_date"})
            if normalized.get("source_quantity") is None:
                errors.append({"code": "MISSING_FIELD", "message": "source_quantity obrigatório.", "field": "source_quantity"})
            if normalized.get("source_net_amount") is None:
                errors.append({"code": "MISSING_FIELD", "message": "source_net_amount obrigatório.", "field": "source_net_amount"})
            if normalized.get("source_updated_at") is None:
                errors.append({"code": "MISSING_FIELD", "message": "source_updated_at obrigatório.", "field": "source_updated_at"})
        elif dataset_code == ErpDatasetCode.FUEL_RETAIL_PRICES:
            for key, label in (
                ("source_product_id", "source_product_id"),
                ("source_payment_method_id", "source_payment_method_id"),
            ):
                if not normalized.get(key):
                    errors.append({"code": "MISSING_FIELD", "message": f"{label} obrigatório.", "field": label})
            if normalized.get("source_price_per_liter") is None:
                errors.append({"code": "MISSING_FIELD", "message": "source_price_per_liter obrigatório.", "field": "source_price_per_liter"})
        elif dataset_code == ErpDatasetCode.FUEL_PURCHASE_INVOICES:
            for key in (
                "source_invoice_id",
                "source_branch_id",
                "source_supplier_id",
                "source_document_number",
                "source_status",
            ):
                if not normalized.get(key):
                    errors.append({"code": "MISSING_FIELD", "message": f"{key} obrigatório.", "field": key})
            for key in ("source_issue_date", "source_entry_date", "source_total_amount", "source_updated_at"):
                if normalized.get(key) is None:
                    errors.append({"code": "MISSING_FIELD", "message": f"{key} obrigatório.", "field": key})
        elif dataset_code == ErpDatasetCode.FUEL_PURCHASE_ITEMS:
            for key in (
                "source_invoice_id",
                "source_invoice_item_id",
                "source_branch_id",
                "source_supplier_id",
                "source_product_id",
                "source_unit",
            ):
                if not normalized.get(key):
                    errors.append({"code": "MISSING_FIELD", "message": f"{key} obrigatório.", "field": key})
            for key in ("source_quantity", "source_unit_price", "source_item_total", "source_updated_at"):
                if normalized.get(key) is None:
                    errors.append({"code": "MISSING_FIELD", "message": f"{key} obrigatório.", "field": key})
        elif dataset_code == ErpDatasetCode.ACCOUNTS_PAYABLE_TITLES:
            for key in (
                "source_title_id",
                "source_branch_id",
                "source_supplier_id",
                "source_invoice_id",
                "source_status",
            ):
                if not normalized.get(key):
                    errors.append({"code": "MISSING_FIELD", "message": f"{key} obrigatório.", "field": key})
            for key in ("source_due_date", "source_original_amount", "source_open_amount", "source_updated_at"):
                if normalized.get(key) is None:
                    errors.append({"code": "MISSING_FIELD", "message": f"{key} obrigatório.", "field": key})
        return errors

    async def _load_staging(self, run_id: uuid.UUID) -> list[ErpStagingRecord]:
        result = await self.db.execute(
            select(ErpStagingRecord).where(ErpStagingRecord.sync_run_id == run_id).order_by(ErpStagingRecord.created_at)
        )
        return list(result.scalars().all())

    async def _record_row_error(
        self,
        run: ErpSyncRun,
        source_key: str | None,
        phase: str,
        code: str,
        message: str,
        details: Any,
        staging_id: uuid.UUID | None = None,
    ) -> None:
        field = details.get("field") if isinstance(details, dict) else None
        self.db.add(
            ErpSyncError(
                sync_run_id=run.id,
                staging_record_id=staging_id,
                phase=phase,
                error_code=code,
                message=message,
                field_name=field,
                source_key=source_key,
                details=details if isinstance(details, dict) else {"payload": str(details)[:500]},
                created_at=datetime.now(UTC),
            )
        )

    async def _is_cancel_requested(self, run_id: uuid.UUID) -> bool:
        result = await self.db.execute(select(ErpSyncRun.status).where(ErpSyncRun.id == run_id))
        status = result.scalar_one_or_none()
        return status == ErpSyncRunStatus.CANCELLATION_REQUESTED

    async def _try_advisory_lock(self, key: int) -> bool:
        result = await self.db.execute(text("SELECT pg_try_advisory_lock(:key)"), {"key": key})
        return bool(result.scalar())

    async def _release_advisory_lock(self, key: int) -> None:
        await self.db.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": key})

    async def _has_active_run(
        self, source_id: uuid.UUID, dataset_id: uuid.UUID, station_id: uuid.UUID
    ) -> bool:
        result = await self.db.execute(
            select(func.count())
            .select_from(ErpSyncRun)
            .where(
                ErpSyncRun.erp_source_id == source_id,
                ErpSyncRun.erp_dataset_id == dataset_id,
                ErpSyncRun.station_id == station_id,
                ErpSyncRun.status.in_(list(ACTIVE_STATUSES)),
            )
        )
        return bool(result.scalar())
