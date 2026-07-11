from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, time, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.exceptions import AppError
from app.core.fuel_sales_normalization import (
    FUEL_SALES_HASH_SCHEMA_VERSION,
    FUEL_SALES_NORMALIZATION_VERSION,
)
from app.core.fuel_purchases_normalization import (
    FUEL_PURCHASE_HASH_SCHEMA_VERSION,
    FUEL_PURCHASE_NORMALIZATION_VERSION,
)
from app.core.xpert_sync_enums import (
    ErpConnectionStatus,
    ErpContractStatus,
    ErpDatasetCode,
    ErpSecurityStatus,
    ErpSyncMode,
    ErpSyncRunStatus,
    ErpSyncTrigger,
)
from app.integrations.xpert.source_security import security_status_from_test
from app.integrations.xpert.canonical_hash import query_file_hash
from app.integrations.xpert.odbc_health import driver_available
from app.integrations.xpert.direct_sqlserver import create_datasource
from app.integrations.xpert.datasource import XpertDataSource
from app.integrations.xpert.query_contracts import validate_contract
from app.integrations.xpert.secret_resolver import load_query_file, validate_query_file
from app.integrations.xpert.query_guard import current_query_hash
from app.models.erp_integration import ErpDataset, ErpSource, ErpSyncRun
from app.models.station import Station
from app.services.audit_service import AuditContext, AuditService
from app.services.xpert_worker_service import XpertWorkerService
from app.services.xpert_checkpoint_service import XpertCheckpointService

DEFAULT_DATASETS = (
    {
        "code": ErpDatasetCode.STATIONS,
        "name": "Filiais",
        "query_file": "stations.sql",
        "sync_mode": ErpSyncMode.FULL_SNAPSHOT_HASH,
        "checkpoint_type": "NONE",
    },
    {
        "code": ErpDatasetCode.PRODUCTS,
        "name": "Produtos",
        "query_file": "products.sql",
        "sync_mode": ErpSyncMode.FULL_SNAPSHOT_HASH,
        "checkpoint_type": "NONE",
    },
    {
        "code": ErpDatasetCode.SUPPLIERS,
        "name": "Fornecedores",
        "query_file": "suppliers.sql",
        "sync_mode": ErpSyncMode.FULL_SNAPSHOT_HASH,
        "checkpoint_type": "NONE",
    },
    {
        "code": ErpDatasetCode.PAYMENT_METHODS,
        "name": "Formas de pagamento",
        "query_file": "payment_methods.sql",
        "sync_mode": ErpSyncMode.FULL_SNAPSHOT_HASH,
        "checkpoint_type": "NONE",
    },
    {
        "code": ErpDatasetCode.FUEL_SALES_ITEMS,
        "name": "Itens de venda combustível",
        "query_file": "fuel_sales_items.sql",
        "sync_mode": ErpSyncMode.INCREMENTAL_TIMESTAMP,
        "checkpoint_type": "TIMESTAMP",
        "overlap_seconds": 86400,
    },
    {
        "code": ErpDatasetCode.FUEL_RETAIL_PRICES,
        "name": "Preços praticados",
        "query_file": "fuel_retail_prices.sql",
        "sync_mode": ErpSyncMode.FULL_SNAPSHOT_HASH,
        "checkpoint_type": "NONE",
    },
    {
        "code": ErpDatasetCode.FUEL_PURCHASE_INVOICES,
        "name": "Notas de entrada de combustível",
        "query_file": "fuel_purchase_invoices.sql",
        "sync_mode": ErpSyncMode.INCREMENTAL_TIMESTAMP,
        "checkpoint_type": "TIMESTAMP",
        "overlap_seconds": 86400,
    },
    {
        "code": ErpDatasetCode.FUEL_PURCHASE_ITEMS,
        "name": "Itens de compra de combustível",
        "query_file": "fuel_purchase_items.sql",
        "sync_mode": ErpSyncMode.INCREMENTAL_TIMESTAMP,
        "checkpoint_type": "TIMESTAMP",
        "overlap_seconds": 86400,
    },
    {
        "code": ErpDatasetCode.ACCOUNTS_PAYABLE_TITLES,
        "name": "Títulos a pagar",
        "query_file": "accounts_payable_titles.sql",
        "sync_mode": ErpSyncMode.INCREMENTAL_TIMESTAMP,
        "checkpoint_type": "TIMESTAMP",
        "overlap_seconds": 86400,
    },
)

_MISCONFIGURED_UNTIL_REAL_SQL = frozenset({
    ErpDatasetCode.STATIONS,
    ErpDatasetCode.FUEL_SALE_PAYMENTS,
    ErpDatasetCode.NFE_XML_DOCUMENTS,
})

_PURCHASE_HISTORY_DATASETS = frozenset({
    ErpDatasetCode.FUEL_PURCHASE_INVOICES,
    ErpDatasetCode.FUEL_PURCHASE_ITEMS,
    ErpDatasetCode.ACCOUNTS_PAYABLE_TITLES,
})

_STATION_REQUIRED_DATASETS = frozenset({
    ErpDatasetCode.FUEL_SALES_ITEMS,
    ErpDatasetCode.FUEL_RETAIL_PRICES,
    ErpDatasetCode.PRODUCTS,
    ErpDatasetCode.SUPPLIERS,
    ErpDatasetCode.FUEL_PURCHASE_INVOICES,
    ErpDatasetCode.FUEL_PURCHASE_ITEMS,
    ErpDatasetCode.ACCOUNTS_PAYABLE_TITLES,
})

_BRANCH_ISOLATION_DATASETS = frozenset({
    ErpDatasetCode.FUEL_SALES_ITEMS,
    ErpDatasetCode.FUEL_RETAIL_PRICES,
    ErpDatasetCode.FUEL_PURCHASE_INVOICES,
    ErpDatasetCode.FUEL_PURCHASE_ITEMS,
    ErpDatasetCode.ACCOUNTS_PAYABLE_TITLES,
})


def _probe_parameters(
    *,
    dataset_code: str,
    station: Station | None,
    probe_days: int = 1,
) -> dict[str, Any]:
    params: dict[str, Any] = {}
    if station and station.erp_branch_id:
        params["station_erp_id"] = station.erp_branch_id
    if dataset_code in (
        ErpDatasetCode.FUEL_SALES_ITEMS,
        ErpDatasetCode.FUEL_PURCHASE_INVOICES,
        ErpDatasetCode.FUEL_PURCHASE_ITEMS,
        ErpDatasetCode.ACCOUNTS_PAYABLE_TITLES,
    ):
        now = datetime.now(UTC)
        params["window_start"] = now - timedelta(days=probe_days)
        params["window_end"] = now
    return params


def _validate_branch_isolation(
    *,
    dataset_code: str,
    rows: list[dict[str, Any]],
    expected_branch_id: str,
) -> list[str]:
    if dataset_code not in _BRANCH_ISOLATION_DATASETS:
        return []
    errors: list[str] = []
    foreign: set[str] = set()
    for row in rows:
        branch = row.get("source_branch_id")
        if branch is None:
            continue
        branch_str = str(branch).strip()
        if branch_str != str(expected_branch_id).strip():
            foreign.add(branch_str)
    if foreign:
        errors.append(
            f"Vazamento de filial detectado: esperado {expected_branch_id}, encontrado {sorted(foreign)}"
        )
    return errors


def _validate_natural_key_duplicates(
    *,
    dataset_code: str,
    rows: list[dict[str, Any]],
) -> list[str]:
    if dataset_code != ErpDatasetCode.FUEL_SALES_ITEMS:
        return []
    seen: set[tuple[str, str]] = set()
    duplicates: list[str] = []
    for row in rows:
        sale_id = str(row.get("source_sale_id", ""))
        item_id = str(row.get("source_sale_item_id", ""))
        key = (sale_id, item_id)
        if key in seen:
            duplicates.append(f"{sale_id}:{item_id}")
        seen.add(key)
    if duplicates:
        return [f"Chave natural duplicada na amostra: {duplicates[:5]}"]
    return []


class XpertSourceService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.audit = AuditService(db)

    async def list_sources(self, organization_id: uuid.UUID) -> list[ErpSource]:
        result = await self.db.execute(
            select(ErpSource)
            .where(ErpSource.organization_id == organization_id)
            .options(selectinload(ErpSource.datasets))
            .order_by(ErpSource.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_source(self, organization_id: uuid.UUID, source_id: uuid.UUID) -> ErpSource:
        result = await self.db.execute(
            select(ErpSource)
            .where(ErpSource.id == source_id, ErpSource.organization_id == organization_id)
            .options(selectinload(ErpSource.datasets))
        )
        source = result.scalar_one_or_none()
        if source is None:
            raise AppError("Fonte XPERT não encontrada.", status_code=404, code="XPERT_SOURCE_NOT_FOUND")
        return source

    async def create_source(
        self,
        *,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        data: dict[str, Any],
        audit_ctx: AuditContext,
    ) -> ErpSource:
        source = ErpSource(
            organization_id=organization_id,
            code=data["code"],
            name=data["name"],
            connector_type=data.get("connector_type", "XPERT_SQLSERVER"),
            connector_mode=data.get("connector_mode", "DIRECT"),
            host=data["host"],
            port=data.get("port", 1433),
            database_name=data["database_name"],
            driver_name=data.get("driver_name", settings.xpert_odbc_driver),
            encrypt_connection=data.get("encrypt_connection", True),
            trust_server_certificate=data.get("trust_server_certificate", False),
            secret_ref=data["secret_ref"],
            source_timezone=data.get("source_timezone", "America/Cuiaba"),
            enabled=data.get("enabled", False),
            connection_status=ErpConnectionStatus.UNKNOWN,
            created_by=user_id,
        )
        self.db.add(source)
        await self.db.flush()
        await self._bootstrap_datasets(source)
        await self.audit.log(
            ctx=audit_ctx,
            entity_type="erp_source",
            entity_id=source.id,
            action="create",
            after_data=self._serialize_source(source),
        )
        return source

    async def update_source(
        self,
        *,
        source: ErpSource,
        data: dict[str, Any],
        user_id: uuid.UUID,
        audit_ctx: AuditContext,
    ) -> ErpSource:
        before = self._serialize_source(source)
        for field in (
            "name",
            "host",
            "port",
            "database_name",
            "driver_name",
            "encrypt_connection",
            "trust_server_certificate",
            "secret_ref",
            "source_timezone",
            "enabled",
        ):
            if field in data:
                setattr(source, field, data[field])
        source.updated_by = user_id
        source.updated_at = datetime.now(UTC)
        await self.audit.log(
            ctx=audit_ctx,
            entity_type="erp_source",
            entity_id=source.id,
            action="update",
            before_data=before,
            after_data=self._serialize_source(source),
        )
        return source

    async def test_connection(
        self,
        *,
        source: ErpSource,
        audit_ctx: AuditContext,
        datasource: XpertDataSource | None = None,
    ) -> dict[str, Any]:
        ds = create_datasource(source, fake=datasource)
        try:
            result = ds.test_connection()
        finally:
            ds.close()
        source.last_tested_at = datetime.now(UTC)
        payload = {
            "status": result.status,
            "latency_ms": result.latency_ms,
            "server_version": result.server_version,
            "database_name": result.database_name,
            "source_utc_time": result.source_utc_time.isoformat() if result.source_utc_time else None,
            "encryption": result.encryption,
            "privileges": result.privileges,
            "warnings": result.warnings,
            "error": result.error,
        }
        source.last_test_result = payload
        if result.status == "CONNECTED":
            source.connection_status = ErpConnectionStatus.CONNECTED
        elif result.status == "UNSAFE":
            source.connection_status = ErpConnectionStatus.UNSAFE if not settings.xpert_allow_unsafe_privileges else ErpConnectionStatus.CONNECTED
        else:
            source.connection_status = ErpConnectionStatus.DISCONNECTED
        source.security_status = security_status_from_test(
            connection_status=source.connection_status,
            privileges=result.privileges,
            allow_unsafe_override=settings.xpert_allow_unsafe_privileges,
        )
        payload["security_status"] = source.security_status
        await self.audit.log(
            ctx=audit_ctx,
            entity_type="erp_source",
            entity_id=source.id,
            action="test_connection",
            after_data={"status": result.status, "latency_ms": result.latency_ms},
        )
        return payload

    async def validate_dataset_contract(
        self,
        *,
        source: ErpSource,
        dataset: ErpDataset,
        audit_ctx: AuditContext,
        datasource: XpertDataSource | None = None,
        station: Station | None = None,
    ) -> dict[str, Any]:
        file_validation = validate_query_file(dataset.query_file)
        if not file_validation["valid"]:
            dataset.contract_status = ErpContractStatus.INVALID
            dataset.contract_result = file_validation
            dataset.last_contract_validation_at = datetime.now(UTC)
            raise AppError(
                "A consulta configurada não atende à política de somente leitura.",
                status_code=400,
                code="XPERT_QUERY_NOT_READ_ONLY",
            )

        sql = load_query_file(dataset.query_file)
        dataset.query_hash = file_validation["query_hash"]

        if dataset.code in _STATION_REQUIRED_DATASETS:
            if station is None:
                raise AppError(
                    "station_id é obrigatório para validar este dataset (fail closed).",
                    status_code=400,
                    code="XPERT_STATION_REQUIRED",
                )
            if not station.erp_branch_id:
                raise AppError(
                    "Posto sem erp_branch_id configurado.",
                    status_code=400,
                    code="XPERT_STATION_BRANCH_MISSING",
                )

        params = _probe_parameters(dataset_code=dataset.code, station=station, probe_days=1)
        if dataset.code in _STATION_REQUIRED_DATASETS and "station_erp_id" not in params:
            raise AppError(
                "Parâmetro @station_erp_id ausente (fail closed).",
                status_code=400,
                code="XPERT_STATION_PARAMETER_MISSING",
            )

        ds = create_datasource(source, fake=datasource)
        isolation_rows: list[dict[str, Any]] = []
        try:
            probe = ds.probe_contract(sql, params, limit=5)
            if dataset.code in _BRANCH_ISOLATION_DATASETS:
                for batch in ds.stream_rows(sql, params, batch_size=500):
                    isolation_rows.extend(batch)
                    if len(isolation_rows) >= 500:
                        isolation_rows = isolation_rows[:500]
                        break
            else:
                isolation_rows = list(probe.sample_rows)
        except KeyError as exc:
            dataset.contract_status = ErpContractStatus.INVALID
            dataset.contract_result = {"error": str(exc)[:500]}
            dataset.last_contract_validation_at = datetime.now(UTC)
            raise AppError(
                "Parâmetro obrigatório ausente na execução da query.",
                status_code=400,
                code="XPERT_QUERY_PARAMETER_MISSING",
            ) from exc
        except Exception as exc:
            dataset.contract_status = ErpContractStatus.INVALID
            dataset.contract_result = {"error": str(exc)[:500]}
            dataset.last_contract_validation_at = datetime.now(UTC)
            raise AppError(
                "Não foi possível conectar ao XPERT.",
                status_code=502,
                code="XPERT_CONNECTION_FAILED",
            ) from exc
        finally:
            ds.close()

        contract = validate_contract(dataset.code, probe.columns)
        isolation_errors: list[str] = []
        if station and station.erp_branch_id:
            isolation_errors.extend(
                _validate_branch_isolation(
                    dataset_code=dataset.code,
                    rows=isolation_rows,
                    expected_branch_id=station.erp_branch_id,
                )
            )
        isolation_errors.extend(
            _validate_natural_key_duplicates(dataset_code=dataset.code, rows=isolation_rows)
        )
        result = {
            "valid": contract.valid and not isolation_errors,
            "missing_columns": contract.missing_columns,
            "extra_columns": contract.extra_columns,
            "found_columns": contract.found_columns,
            "query_hash": dataset.query_hash,
            "sample_count": probe.row_count,
            "isolation_sample_size": len(isolation_rows),
            "isolation_errors": isolation_errors,
            "distinct_branch_ids": sorted(
                {str(r.get("source_branch_id")) for r in isolation_rows if r.get("source_branch_id") is not None}
            ),
        }
        dataset.contract_result = result
        dataset.last_contract_validation_at = datetime.now(UTC)
        dataset.contract_status = (
            ErpContractStatus.VALID if contract.valid and not isolation_errors else ErpContractStatus.INVALID
        )
        if not contract.valid:
            raise AppError(
                "A consulta não retornou as colunas obrigatórias.",
                status_code=400,
                code="XPERT_DATASET_CONTRACT_INVALID",
            )
        if isolation_errors:
            raise AppError(
                isolation_errors[0],
                status_code=400,
                code="XPERT_BRANCH_ISOLATION_FAILED",
            )
        await self.audit.log(
            ctx=audit_ctx,
            entity_type="erp_dataset",
            entity_id=dataset.id,
            action="validate_contract",
            after_data=result,
        )
        return result

    async def enqueue_sync_runs(
        self,
        *,
        organization_id: uuid.UUID,
        source: ErpSource,
        dataset_codes: list[str],
        station_ids: list[uuid.UUID],
        sync_mode: str,
        trigger_type: str,
        requested_by: uuid.UUID | None,
        retried_from_run_id: uuid.UUID | None = None,
        unsafe_homologation_acknowledged: bool = False,
        audit_ctx: AuditContext | None = None,
        history_start_date: date | None = None,
        history_end_date: date | None = None,
    ) -> list[ErpSyncRun]:
        datasets = {d.code: d for d in source.datasets}
        runs: list[ErpSyncRun] = []
        self._validate_unsafe_manual_run(
            source=source,
            trigger_type=trigger_type,
            unsafe_homologation_acknowledged=unsafe_homologation_acknowledged,
        )
        for code in dataset_codes:
            dataset = datasets.get(code)
            if dataset is None:
                raise AppError(f"Dataset não encontrado: {code}", status_code=404, code="XPERT_DATASET_NOT_FOUND")
            for station_id in station_ids:
                await self._validate_enqueue_request(
                    source=source,
                    dataset=dataset,
                    station_id=station_id,
                    sync_mode=sync_mode,
                    history_start_date=history_start_date,
                    history_end_date=history_end_date,
                )
                active = await self._has_active_run(source.id, dataset.id, station_id)
                if active:
                    raise AppError(
                        "Já existe uma sincronização em andamento para este dataset e posto.",
                        status_code=409,
                        code="XPERT_SYNC_ALREADY_RUNNING",
                    )
                run = ErpSyncRun(
                    organization_id=organization_id,
                    erp_source_id=source.id,
                    erp_dataset_id=dataset.id,
                    station_id=station_id,
                    trigger_type=trigger_type,
                    sync_mode=sync_mode or dataset.sync_mode,
                    status=ErpSyncRunStatus.QUEUED,
                    query_hash=dataset.query_hash,
                    requested_by=requested_by,
                    retried_from_run_id=retried_from_run_id,
                    created_at=datetime.now(UTC),
                )
                if (
                    dataset.code
                    in (
                        ErpDatasetCode.FUEL_SALES_ITEMS,
                        *_PURCHASE_HISTORY_DATASETS,
                    )
                    and history_start_date is not None
                ):
                    run.window_start = datetime.combine(history_start_date, time.min, tzinfo=UTC)
                if history_end_date is not None:
                    run.window_end = datetime.combine(
                        history_end_date + timedelta(days=1),
                        time.min,
                        tzinfo=UTC,
                    )
                if dataset.code == ErpDatasetCode.FUEL_SALES_ITEMS:
                    run.normalization_version = FUEL_SALES_NORMALIZATION_VERSION
                    run.hash_schema_version = FUEL_SALES_HASH_SCHEMA_VERSION
                if dataset.code in _PURCHASE_HISTORY_DATASETS:
                    run.normalization_version = FUEL_PURCHASE_NORMALIZATION_VERSION
                    run.hash_schema_version = FUEL_PURCHASE_HASH_SCHEMA_VERSION
                self.db.add(run)
                runs.append(run)
        await self.db.flush()
        if audit_ctx and source.security_status == ErpSecurityStatus.UNSAFE:
            await self.audit.log(
                ctx=audit_ctx,
                entity_type="erp_source",
                entity_id=source.id,
                action="unsafe_manual_sync",
                after_data={
                    "dataset_codes": dataset_codes,
                    "station_ids": [str(s) for s in station_ids],
                    "sync_mode": sync_mode,
                    "run_ids": [str(r.id) for r in runs],
                },
            )
        return runs

    def _validate_unsafe_manual_run(
        self,
        *,
        source: ErpSource,
        trigger_type: str,
        unsafe_homologation_acknowledged: bool,
    ) -> None:
        if settings.app_env == "production" and settings.xpert_allow_unsafe_privileges:
            raise AppError(
                "Override inseguro bloqueado em produção.",
                status_code=403,
                code="UNSAFE_SOURCE_BLOCKED_IN_PRODUCTION",
            )
        if source.security_status != ErpSecurityStatus.UNSAFE:
            return
        if trigger_type == ErpSyncTrigger.SCHEDULED:
            raise AppError(
                "Agenda automática bloqueada para fonte UNSAFE.",
                status_code=403,
                code="UNSAFE_SOURCE_SCHEDULE_BLOCKED",
            )
        if not settings.xpert_allow_unsafe_privileges:
            raise AppError(
                "Fonte XPERT insegura. Configure XPERT_ALLOW_UNSAFE_PRIVILEGES apenas em homologação.",
                status_code=403,
                code="UNSAFE_SOURCE_NOT_ALLOWED",
            )
        if not unsafe_homologation_acknowledged:
            raise AppError(
                "Confirmação explícita obrigatória para fonte insegura.",
                status_code=400,
                code="UNSAFE_HOMOLOGATION_ACK_REQUIRED",
            )

    async def has_completed_full_run(
        self, *, dataset_id: uuid.UUID, station_id: uuid.UUID
    ) -> bool:
        result = await self.db.execute(
            select(func.count())
            .select_from(ErpSyncRun)
            .where(
                ErpSyncRun.erp_dataset_id == dataset_id,
                ErpSyncRun.station_id == station_id,
                ErpSyncRun.status == ErpSyncRunStatus.COMPLETED,
                ErpSyncRun.sync_mode.in_(
                    [ErpSyncMode.FULL, ErpSyncMode.FULL_SNAPSHOT_HASH]
                ),
            )
        )
        return bool(result.scalar())

    async def _validate_enqueue_request(
        self,
        *,
        source: ErpSource,
        dataset: ErpDataset,
        station_id: uuid.UUID,
        sync_mode: str,
        history_start_date: date | None = None,
        history_end_date: date | None = None,
    ) -> None:
        if dataset.code == ErpDatasetCode.STATIONS:
            raise AppError(
                "Dataset STATIONS permanece bloqueado até validação do DBA.",
                status_code=400,
                code="XPERT_DATASET_STATIONS_BLOCKED",
            )
        if not dataset.enabled:
            raise AppError("Dataset desabilitado.", status_code=400, code="XPERT_DATASET_DISABLED")
        if dataset.contract_status != ErpContractStatus.VALID:
            raise AppError(
                "Contrato do dataset não validado.",
                status_code=400,
                code="XPERT_DATASET_CONTRACT_INVALID",
            )
        if dataset.query_hash != current_query_hash(dataset.query_file):
            raise AppError(
                "A consulta do dataset foi alterada após a última validação.",
                status_code=400,
                code="QUERY_CHANGED_AFTER_VALIDATION",
            )
        if source.connection_status not in (
            ErpConnectionStatus.CONNECTED,
            ErpConnectionStatus.DEGRADED,
        ):
            raise AppError(
                "Fonte XPERT não está conectada.",
                status_code=400,
                code="XPERT_SOURCE_DISCONNECTED",
            )
        if dataset.code in (
            ErpDatasetCode.PRODUCTS,
            ErpDatasetCode.SUPPLIERS,
            ErpDatasetCode.FUEL_SALES_ITEMS,
            ErpDatasetCode.FUEL_RETAIL_PRICES,
            ErpDatasetCode.FUEL_PURCHASE_INVOICES,
            ErpDatasetCode.FUEL_PURCHASE_ITEMS,
            ErpDatasetCode.ACCOUNTS_PAYABLE_TITLES,
        ):
            station = await self.db.get(Station, station_id)
            if station is None or not station.erp_branch_id:
                raise AppError(
                    "Posto sem erp_branch_id configurado.",
                    status_code=400,
                    code="XPERT_STATION_BRANCH_MISSING",
                )
        incremental_modes = {ErpSyncMode.INCREMENTAL_TIMESTAMP, ErpSyncMode.INCREMENTAL_ID}
        if sync_mode in incremental_modes:
            if dataset.code in (
                ErpDatasetCode.FUEL_SALES_ITEMS,
                *_PURCHASE_HISTORY_DATASETS,
            ):
                checkpoint_service = XpertCheckpointService(self.db)
                checkpoint = await checkpoint_service.get_or_create(
                    source=source, dataset=dataset, station_id=station_id
                )
                if not checkpoint.watermark_value and (
                    history_start_date is None or history_end_date is None
                ):
                    raise AppError(
                        "A primeira carga exige history_start_date e history_end_date.",
                        status_code=400,
                        code="HISTORY_WINDOW_REQUIRED",
                    )
                return
            has_full = await self.has_completed_full_run(
                dataset_id=dataset.id, station_id=station_id
            )
            if not has_full:
                raise AppError(
                    "Sincronização incremental requer uma carga completa anterior concluída.",
                    status_code=400,
                    code="XPERT_INCREMENTAL_REQUIRES_FULL",
                )

    async def get_summary(self, organization_id: uuid.UUID) -> dict[str, Any]:
        sources = await self.list_sources(organization_id)
        if not sources:
            return {
                "status": ErpConnectionStatus.DISABLED,
                "sources_count": 0,
                "datasets_enabled": 0,
                "pending_products": 0,
                "pending_suppliers": 0,
                "error_runs": 0,
                "last_success_at": None,
                "odbc_available": driver_available()[0],
                "worker_healthy": False,
                "worker_last_heartbeat_at": None,
            }
        source = sources[0]
        datasets_enabled = sum(1 for d in source.datasets if d.enabled)
        last_success = source.last_success_at
        error_runs = await self.db.scalar(
            select(func.count())
            .select_from(ErpSyncRun)
            .where(
                ErpSyncRun.organization_id == organization_id,
                ErpSyncRun.status.in_([ErpSyncRunStatus.FAILED, ErpSyncRunStatus.PARTIAL]),
            )
        )
        from app.models.erp_product import ErpProduct
        from app.models.distributor import ErpSupplier
        from app.core.master_data_enums import MappingStatus

        pending_products = await self.db.scalar(
            select(func.count())
            .select_from(ErpProduct)
            .where(
                ErpProduct.organization_id == organization_id,
                ErpProduct.mapping_status == MappingStatus.PENDING,
            )
        )
        pending_suppliers = await self.db.scalar(
            select(func.count())
            .select_from(ErpSupplier)
            .where(
                ErpSupplier.organization_id == organization_id,
                ErpSupplier.mapping_status == MappingStatus.PENDING,
            )
        )
        odbc_ok, _ = driver_available()
        worker = XpertWorkerService(self.db)
        worker_row = await worker.latest_worker_status()
        worker_healthy = False
        worker_last = None
        if worker_row is not None:
            worker_last = worker_row.last_heartbeat_at.isoformat()
            from datetime import timedelta
            from app.core.config import settings as app_settings

            worker_healthy = worker_row.last_heartbeat_at >= datetime.now(UTC) - timedelta(
                seconds=app_settings.xpert_worker_heartbeat_timeout_seconds
            )
        return {
            "status": source.connection_status,
            "security_status": source.security_status,
            "source_id": str(source.id),
            "sources_count": len(sources),
            "datasets_enabled": datasets_enabled,
            "pending_products": pending_products or 0,
            "pending_suppliers": pending_suppliers or 0,
            "error_runs": error_runs or 0,
            "last_success_at": last_success.isoformat() if last_success else None,
            "odbc_available": odbc_ok,
            "worker_healthy": worker_healthy and odbc_ok,
            "worker_last_heartbeat_at": worker_last,
        }

    async def _bootstrap_datasets(self, source: ErpSource) -> None:
        for item in DEFAULT_DATASETS:
            query_file = item["query_file"]
            try:
                sql = load_query_file(query_file)
                q_hash = query_file_hash(sql)
                file_ok = validate_query_file(query_file)["valid"]
            except FileNotFoundError:
                q_hash = None
                file_ok = False
            if item["code"] in _MISCONFIGURED_UNTIL_REAL_SQL:
                contract_status = ErpContractStatus.MISCONFIGURED
            elif file_ok:
                contract_status = ErpContractStatus.PENDING
            else:
                contract_status = ErpContractStatus.MISCONFIGURED
            overlap = item.get("overlap_seconds", settings.xpert_sync_default_overlap_seconds)
            self.db.add(
                ErpDataset(
                    erp_source_id=source.id,
                    code=item["code"],
                    name=item["name"],
                    query_file=query_file,
                    query_hash=q_hash,
                    sync_mode=item["sync_mode"],
                    checkpoint_type=item["checkpoint_type"],
                    overlap_seconds=overlap,
                    batch_size=settings.xpert_sync_default_batch_size,
                    contract_status=contract_status,
                    enabled=False,
                )
            )
        await self.db.flush()

    async def ensure_missing_datasets(self, source: ErpSource) -> list[str]:
        """Provisiona datasets DEFAULT ausentes (ex.: fonte criada antes da Sprint 6)."""
        existing = {dataset.code for dataset in source.datasets}
        created: list[str] = []
        for item in DEFAULT_DATASETS:
            if item["code"] in existing:
                continue
            query_file = item["query_file"]
            try:
                sql = load_query_file(query_file)
                q_hash = query_file_hash(sql)
                file_ok = validate_query_file(query_file)["valid"]
            except FileNotFoundError:
                q_hash = None
                file_ok = False
            if item["code"] in _MISCONFIGURED_UNTIL_REAL_SQL:
                contract_status = ErpContractStatus.MISCONFIGURED
            elif file_ok:
                contract_status = ErpContractStatus.PENDING
            else:
                contract_status = ErpContractStatus.MISCONFIGURED
            overlap = item.get("overlap_seconds", settings.xpert_sync_default_overlap_seconds)
            self.db.add(
                ErpDataset(
                    erp_source_id=source.id,
                    code=item["code"],
                    name=item["name"],
                    query_file=query_file,
                    query_hash=q_hash,
                    sync_mode=item["sync_mode"],
                    checkpoint_type=item["checkpoint_type"],
                    overlap_seconds=overlap,
                    batch_size=settings.xpert_sync_default_batch_size,
                    contract_status=contract_status,
                    enabled=False,
                )
            )
            created.append(item["code"])
        if created:
            await self.db.flush()
        return created

    async def _has_active_run(
        self, source_id: uuid.UUID, dataset_id: uuid.UUID, station_id: uuid.UUID
    ) -> bool:
        active_statuses = [
            ErpSyncRunStatus.QUEUED,
            ErpSyncRunStatus.CONNECTING,
            ErpSyncRunStatus.EXTRACTING,
            ErpSyncRunStatus.STAGING,
            ErpSyncRunStatus.VALIDATING,
            ErpSyncRunStatus.APPLYING,
            ErpSyncRunStatus.CANCELLATION_REQUESTED,
        ]
        result = await self.db.execute(
            select(func.count())
            .select_from(ErpSyncRun)
            .where(
                ErpSyncRun.erp_source_id == source_id,
                ErpSyncRun.erp_dataset_id == dataset_id,
                ErpSyncRun.station_id == station_id,
                ErpSyncRun.status.in_(active_statuses),
            )
        )
        return bool(result.scalar())

    def _serialize_source(self, source: ErpSource) -> dict[str, Any]:
        return {
            "id": str(source.id),
            "code": source.code,
            "name": source.name,
            "host": source.host,
            "port": source.port,
            "database_name": source.database_name,
            "enabled": source.enabled,
            "connection_status": source.connection_status,
            "secret_ref": source.secret_ref,
        }
