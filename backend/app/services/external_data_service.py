"""Catálogo, importação e analytics de índices externos."""

from __future__ import annotations

import csv
import hashlib
import io
import uuid
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.external_data_enums import (
    ExternalSeriesFrequency,
    ExternalSourceStatus,
    ExternalSourceType,
    ExternalUnit,
    ImportParseStatus,
    IngestionRunStatus,
    IngestionTriggerType,
    ObservationApplyResult,
    ObservationRevisionStatus,
)
from app.models.external_data import (
    ExternalDataSource,
    ExternalImportFile,
    ExternalIngestionRun,
    ExternalObservation,
    ExternalQualityIssue,
    ExternalSeries,
)
from app.services.audit_service import AuditContext, AuditService
from app.services.external_data.adapters import get_adapter
from app.services.external_data.freshness_service import ExternalFreshnessService
from app.services.external_data.observation_service import (
    ExternalObservationService,
    ObservationCandidate,
)
from app.services.external_data.units import parse_decimal
from app.storage.object_storage import ObjectStorageService

DEFAULT_SERIES_SEED = [
    {
        "source_code": "MANUAL_MARKET",
        "source_name": "Entrada manual de mercado",
        "source_type": ExternalSourceType.MANUAL.value,
        "series_code": "BRENT_CRUDE_OIL",
        "series_name": "Brent Crude Oil",
        "frequency": ExternalSeriesFrequency.DAILY.value,
        "source_unit": ExternalUnit.USD_PER_BARREL.value,
        "canonical_unit": ExternalUnit.USD_PER_BARREL.value,
        "currency": "USD",
        "freshness_grace_minutes": 2880,
    },
    {
        "source_code": "MANUAL_MARKET",
        "source_name": "Entrada manual de mercado",
        "source_type": ExternalSourceType.MANUAL.value,
        "series_code": "USD_BRL_REFERENCE",
        "series_name": "USD/BRL referência",
        "frequency": ExternalSeriesFrequency.DAILY.value,
        "source_unit": ExternalUnit.BRL_PER_USD.value,
        "canonical_unit": ExternalUnit.BRL_PER_USD.value,
        "currency": "BRL",
        "freshness_grace_minutes": 2880,
    },
    {
        "source_code": "MANUAL_MARKET",
        "source_name": "Entrada manual de mercado",
        "source_type": ExternalSourceType.MANUAL.value,
        "series_code": "CEPEA_ETHANOL_MT",
        "series_name": "CEPEA Etanol MT",
        "frequency": ExternalSeriesFrequency.WEEKLY.value,
        "source_unit": ExternalUnit.BRL_PER_LITER.value,
        "canonical_unit": ExternalUnit.BRL_PER_LITER.value,
        "currency": "BRL",
        "freshness_grace_minutes": 10080,
        "calendar_type": "SOURCE_SPECIFIC",
    },
    {
        "source_code": "CSONLINE",
        "source_name": "CSOnline Price Information",
        "source_type": ExternalSourceType.AUTHORIZED_WEB.value,
        "series_code": "CSONLINE_PRICE_INFORMATION",
        "series_name": "CSOnline — informações de preço",
        "frequency": ExternalSeriesFrequency.IRREGULAR.value,
        "source_unit": ExternalUnit.INDEX_POINTS.value,
        "canonical_unit": ExternalUnit.INDEX_POINTS.value,
        "currency": None,
        "freshness_grace_minutes": 10080,
        "source_status": ExternalSourceStatus.MISCONFIGURED.value,
        "scheduler_enabled": False,
        "requires_credentials": True,
    },
]


class ExternalDataService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.audit = AuditService(db)
        self.observations = ExternalObservationService(db)
        self.freshness = ExternalFreshnessService(db)
        self.storage = ObjectStorageService()
        self._memory_files: dict[str, bytes] = {}

    def _org_filter(self, stmt: Select, organization_id: uuid.UUID, column) -> Select:
        return stmt.where(
            (column == organization_id) | (column.is_(None))
        )

    async def seed_default_catalog(
        self,
        *,
        organization_id: uuid.UUID,
        user_id: uuid.UUID | None,
        audit_ctx: AuditContext | None = None,
    ) -> dict[str, Any]:
        created_sources = 0
        created_series = 0
        for row in DEFAULT_SERIES_SEED:
            source = (
                await self.db.execute(
                    select(ExternalDataSource).where(
                        ExternalDataSource.organization_id == organization_id,
                        ExternalDataSource.code == row["source_code"],
                    )
                )
            ).scalar_one_or_none()
            if source is None:
                adapter = get_adapter(
                    row["source_type"],
                    {
                        "requires_credentials": row.get("requires_credentials", False),
                        "authorized_mechanism": None,
                    },
                )
                caps = adapter.capabilities()
                source = ExternalDataSource(
                    organization_id=organization_id,
                    code=row["source_code"],
                    name=row["source_name"],
                    source_type=row["source_type"],
                    status=row.get("source_status", ExternalSourceStatus.READY_FOR_MANUAL.value),
                    connector_status=adapter.connector_status(),
                    requires_credentials=caps.requires_credentials,
                    supports_scheduling=caps.supports_scheduling,
                    scheduler_enabled=False,
                    capabilities=caps.__dict__,
                    terms_review_status="PENDING",
                    created_by=user_id,
                    updated_by=user_id,
                )
                self.db.add(source)
                await self.db.flush()
                created_sources += 1

            series = (
                await self.db.execute(
                    select(ExternalSeries).where(
                        ExternalSeries.organization_id == organization_id,
                        ExternalSeries.code == row["series_code"],
                    )
                )
            ).scalar_one_or_none()
            if series is None:
                series = ExternalSeries(
                    organization_id=organization_id,
                    source_id=source.id,
                    code=row["series_code"],
                    name=row["series_name"],
                    frequency=row["frequency"],
                    source_unit=row["source_unit"],
                    canonical_unit=row["canonical_unit"],
                    currency=row.get("currency"),
                    timezone="America/Sao_Paulo",
                    calendar_type=row.get("calendar_type", "BUSINESS_DAYS"),
                    freshness_grace_minutes=row["freshness_grace_minutes"],
                    conversion_policy={"forbid_auto_currency": True},
                    outlier_pct_threshold=Decimal("15"),
                    active=True,
                )
                self.db.add(series)
                created_series += 1
        await self.db.commit()
        if audit_ctx:
            await self.audit.log(
                ctx=audit_ctx,
                entity_type="external_data_catalog",
                entity_id=organization_id,
                action="SEED",
                after_data={"sources": created_sources, "series": created_series},
            )
            await self.db.commit()
        return {"sources_created": created_sources, "series_created": created_series}

    async def list_sources(self, organization_id: uuid.UUID) -> list[ExternalDataSource]:
        q = await self.db.execute(
            select(ExternalDataSource)
            .where(
                (ExternalDataSource.organization_id == organization_id)
                | (ExternalDataSource.organization_id.is_(None))
            )
            .order_by(ExternalDataSource.code)
        )
        return list(q.scalars().all())

    async def create_source(
        self,
        *,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        data: dict[str, Any],
        audit_ctx: AuditContext,
    ) -> ExternalDataSource:
        adapter = get_adapter(
            data["source_type"],
            {
                "base_url": data.get("base_url"),
                "secret_ref": data.get("secret_ref"),
                "requires_credentials": data.get("requires_credentials", False),
                "contract_validated": data.get("contract_validated", False),
                "authorized_mechanism": data.get("authorized_mechanism"),
            },
        )
        caps = adapter.capabilities()
        # Scheduler nunca liga sem homologação explícita
        scheduler_enabled = False
        source = ExternalDataSource(
            organization_id=organization_id,
            code=data["code"],
            name=data["name"],
            source_type=data["source_type"],
            status=adapter.connector_status(),
            connector_status=adapter.connector_status(),
            base_url=data.get("base_url"),
            secret_ref=data.get("secret_ref"),
            requires_credentials=caps.requires_credentials,
            supports_scheduling=caps.supports_scheduling,
            scheduler_enabled=scheduler_enabled,
            capabilities=caps.__dict__,
            metadata_json=data.get("metadata"),
            terms_review_status=data.get("terms_review_status", "PENDING"),
            created_by=user_id,
            updated_by=user_id,
        )
        self.db.add(source)
        await self.db.flush()
        await self.audit.log(
            ctx=audit_ctx,
            entity_type="external_data_source",
            entity_id=source.id,
            action="CREATE",
            after_data={"code": source.code, "status": source.status},
        )
        await self.db.commit()
        await self.db.refresh(source)
        return source

    async def get_source(self, source_id: uuid.UUID, organization_id: uuid.UUID) -> ExternalDataSource:
        source = await self.db.get(ExternalDataSource, source_id)
        if source is None or (
            source.organization_id is not None and source.organization_id != organization_id
        ):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fonte não encontrada")
        return source

    async def test_source(self, source_id: uuid.UUID, organization_id: uuid.UUID) -> dict[str, Any]:
        source = await self.get_source(source_id, organization_id)
        adapter = get_adapter(
            source.source_type,
            {
                "base_url": source.base_url,
                "secret_ref": source.secret_ref,
                "requires_credentials": source.requires_credentials,
                "contract_validated": (source.metadata_json or {}).get("contract_validated", False),
                "authorized_mechanism": (source.metadata_json or {}).get("authorized_mechanism"),
            },
        )
        errors = adapter.validate_config()
        result = {
            "ok": not errors,
            "connector_status": adapter.connector_status(),
            "errors": errors,
            "capabilities": adapter.capabilities().__dict__,
            "scheduler_enabled": source.scheduler_enabled,
            "note": "Scheduler permanece desabilitado até homologação manual completa",
        }
        source.last_test_result = result
        source.connector_status = adapter.connector_status()
        source.status = adapter.connector_status()
        if errors:
            source.last_failure_at = datetime.now(UTC)
        else:
            source.last_success_at = datetime.now(UTC)
        await self.db.commit()
        return result

    async def list_series(self, organization_id: uuid.UUID, active_only: bool = True) -> list[ExternalSeries]:
        stmt = select(ExternalSeries).where(
            (ExternalSeries.organization_id == organization_id)
            | (ExternalSeries.organization_id.is_(None))
        )
        if active_only:
            stmt = stmt.where(ExternalSeries.active.is_(True))
        q = await self.db.execute(stmt.order_by(ExternalSeries.code))
        return list(q.scalars().all())

    async def create_series(
        self,
        *,
        organization_id: uuid.UUID,
        data: dict[str, Any],
        audit_ctx: AuditContext,
    ) -> ExternalSeries:
        await self.get_source(data["source_id"], organization_id)
        series = ExternalSeries(
            organization_id=organization_id,
            source_id=data["source_id"],
            code=data["code"],
            name=data["name"],
            description=data.get("description"),
            frequency=data["frequency"],
            source_unit=data["source_unit"],
            canonical_unit=data["canonical_unit"],
            currency=data.get("currency"),
            timezone=data.get("timezone", "America/Sao_Paulo"),
            calendar_type=data.get("calendar_type", "BUSINESS_DAYS"),
            freshness_grace_minutes=data.get("freshness_grace_minutes", 1440),
            expected_publish_time=data.get("expected_publish_time"),
            conversion_policy=data.get("conversion_policy") or {"forbid_auto_currency": True},
            outlier_pct_threshold=Decimal(str(data["outlier_pct_threshold"]))
            if data.get("outlier_pct_threshold") is not None
            else Decimal("15"),
            active=data.get("active", True),
            metadata_json=data.get("metadata"),
        )
        self.db.add(series)
        await self.db.flush()
        await self.audit.log(
            ctx=audit_ctx,
            entity_type="external_series",
            entity_id=series.id,
            action="CREATE",
            after_data={"code": series.code},
        )
        await self.db.commit()
        await self.db.refresh(series)
        return series

    async def get_series(self, series_id: uuid.UUID, organization_id: uuid.UUID) -> ExternalSeries:
        series = await self.db.get(ExternalSeries, series_id)
        if series is None or (
            series.organization_id is not None and series.organization_id != organization_id
        ):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Série não encontrada")
        return series

    async def list_observations(
        self,
        *,
        series_id: uuid.UUID,
        organization_id: uuid.UUID,
        date_from: date | None = None,
        date_to: date | None = None,
        current_only: bool = True,
        limit: int = 500,
    ) -> list[ExternalObservation]:
        await self.get_series(series_id, organization_id)
        stmt = select(ExternalObservation).where(ExternalObservation.series_id == series_id)
        if current_only:
            stmt = stmt.where(
                ExternalObservation.revision_status == ObservationRevisionStatus.CURRENT.value
            )
        if date_from:
            stmt = stmt.where(
                ExternalObservation.observation_datetime
                >= datetime(date_from.year, date_from.month, date_from.day, tzinfo=UTC)
            )
        if date_to:
            from datetime import timedelta

            end = datetime(date_to.year, date_to.month, date_to.day, tzinfo=UTC) + timedelta(days=1)
            stmt = stmt.where(ExternalObservation.observation_datetime < end)
        stmt = stmt.order_by(ExternalObservation.observation_datetime.desc()).limit(limit)
        return list((await self.db.execute(stmt)).scalars().all())

    async def create_manual_observation(
        self,
        *,
        series_id: uuid.UUID,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        data: dict[str, Any],
        audit_ctx: AuditContext,
    ) -> dict[str, Any]:
        series = await self.get_series(series_id, organization_id)
        run = ExternalIngestionRun(
            source_id=series.source_id,
            series_id=series.id,
            organization_id=organization_id,
            trigger_type=IngestionTriggerType.MANUAL.value,
            status=IngestionRunStatus.RUNNING.value,
            started_at=datetime.now(UTC),
            requested_by=user_id,
            created_at=datetime.now(UTC),
        )
        self.db.add(run)
        await self.db.flush()

        value = parse_decimal(data.get("value"))
        if value is None:
            raise HTTPException(status_code=400, detail="Valor ausente — não convertido para zero")

        candidate = ObservationCandidate(
            observation_datetime=data["observation_datetime"],
            source_value=value,
            source_unit=data.get("source_unit") or series.source_unit,
            currency=data.get("currency") or series.currency,
            published_at=data.get("published_at"),
            available_at=data.get("available_at"),
            reference_period_start=data.get("reference_period_start"),
            reference_period_end=data.get("reference_period_end"),
            external_identifier=data.get("external_identifier"),
            raw_payload={"manual": True, **{k: str(v) if v is not None else None for k, v in data.items() if k != "raw"}},
        )
        outcome = await self.observations.apply_candidate(
            series=series, candidate=candidate, ingestion_run_id=run.id
        )
        run.records_read = 1
        if outcome.result == ObservationApplyResult.INSERTED:
            run.records_inserted = 1
        elif outcome.result == ObservationApplyResult.NEW_REVISION:
            run.records_revised = 1
        elif outcome.result == ObservationApplyResult.SKIPPED_UNCHANGED:
            run.records_unchanged = 1
        else:
            run.records_rejected = 1
        run.status = IngestionRunStatus.COMPLETED.value
        run.finished_at = datetime.now(UTC)
        await self.audit.log(
            ctx=audit_ctx,
            entity_type="external_observation",
            entity_id=outcome.observation.id if outcome.observation else series.id,
            action=outcome.result.value,
            after_data={"series": series.code, "result": outcome.result.value},
        )
        await self.db.commit()
        return {
            "result": outcome.result.value,
            "observation_id": str(outcome.observation.id) if outcome.observation else None,
            "run_id": str(run.id),
            "revision_number": outcome.observation.revision_number if outcome.observation else None,
        }

    async def preview_csv_import(
        self,
        *,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        series_id: uuid.UUID,
        filename: str,
        content: bytes,
        mapping: dict[str, str],
        audit_ctx: AuditContext,
    ) -> dict[str, Any]:
        series = await self.get_series(series_id, organization_id)
        if not filename.lower().endswith(".csv"):
            raise HTTPException(status_code=400, detail="Nesta etapa apenas CSV é suportado no preview")

        sha = hashlib.sha256(content).hexdigest()
        storage_key = f"external-imports/{organization_id}/{uuid.uuid4()}_{filename}"
        try:
            self.storage.put_object(key=storage_key, data=content, content_type="text/csv")
        except Exception:
            # fallback: chave lógica mesmo sem MinIO
            storage_key = f"memory://{storage_key}"
            self._memory_files[storage_key] = content

        run = ExternalIngestionRun(
            source_id=series.source_id,
            series_id=series.id,
            organization_id=organization_id,
            trigger_type=IngestionTriggerType.IMPORT.value,
            status=IngestionRunStatus.PENDING.value,
            started_at=datetime.now(UTC),
            requested_by=user_id,
            created_at=datetime.now(UTC),
        )
        self.db.add(run)
        await self.db.flush()

        text = content.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        date_col = mapping.get("date_column") or "date"
        value_col = mapping.get("value_column") or "value"
        preview_rows: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []
        for i, row in enumerate(reader, start=2):
            if i > 51:
                break
            raw_date = (row.get(date_col) or "").strip()
            raw_value = (row.get(value_col) or "").strip()
            entry: dict[str, Any] = {"line": i, "raw_date": raw_date, "raw_value": raw_value}
            try:
                if not raw_date:
                    raise ValueError("data ausente")
                if not raw_value:
                    raise ValueError("valor ausente (não vira zero)")
                obs_dt = self._parse_date(raw_date, mapping.get("date_format"), mapping.get("timezone"))
                val = parse_decimal(raw_value)
                if val is None:
                    raise ValueError("valor inválido")
                entry.update(
                    {
                        "observation_datetime": obs_dt.isoformat(),
                        "value": str(val),
                        "ok": True,
                    }
                )
            except Exception as exc:  # noqa: BLE001
                entry["ok"] = False
                entry["error"] = str(exc)
                errors.append(entry)
            preview_rows.append(entry)

        import_file = ExternalImportFile(
            ingestion_run_id=run.id,
            organization_id=organization_id,
            series_id=series.id,
            original_filename=filename,
            storage_key=storage_key,
            sha256=sha,
            size_bytes=len(content),
            parse_status=ImportParseStatus.PREVIEWED.value,
            column_mapping=mapping,
            preview_payload={
                {
                    "rows": preview_rows,
                    "headers": reader.fieldnames,
                    "content_b64": __import__("base64").b64encode(content).decode("ascii")
                    if len(content) <= 2_000_000
                    else None,
                }
            },
            parse_errors={"errors": errors} if errors else None,
            created_at=datetime.now(UTC),
        )
        self.db.add(import_file)
        await self.db.flush()
        await self.audit.log(
            ctx=audit_ctx,
            entity_type="external_import_file",
            entity_id=import_file.id,
            action="PREVIEW",
            after_data={"filename": filename, "rows": len(preview_rows), "errors": len(errors)},
        )
        await self.db.commit()
        await self.db.refresh(import_file)
        return {
            "import_file_id": str(import_file.id),
            "run_id": str(run.id),
            "preview": preview_rows,
            "error_count": len(errors),
            "note": "Nada foi aplicado. Confirme explicitamente para gravar observações.",
        }

    async def confirm_csv_import(
        self,
        *,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        import_file_id: uuid.UUID,
        audit_ctx: AuditContext,
    ) -> dict[str, Any]:
        import_file = await self.db.get(ExternalImportFile, import_file_id)
        if import_file is None or (
            import_file.organization_id is not None and import_file.organization_id != organization_id
        ):
            raise HTTPException(status_code=404, detail="Arquivo de importação não encontrado")
        if import_file.parse_status == ImportParseStatus.APPLIED.value:
            raise HTTPException(status_code=409, detail="Importação já aplicada")
        if not import_file.series_id:
            raise HTTPException(status_code=400, detail="Série não vinculada")

        series = await self.get_series(import_file.series_id, organization_id)
        run = await self.db.get(ExternalIngestionRun, import_file.ingestion_run_id)
        assert run is not None
        run.status = IngestionRunStatus.RUNNING.value

        # Re-ler do storage ou memória
        content: bytes | None = None
        if import_file.storage_key.startswith("memory://"):
            content = self._memory_files.get(import_file.storage_key)
        else:
            try:
                stream, _size, _ctype = self.storage.get_object(key=import_file.storage_key)
                content = stream.read()
            except Exception:
                content = None
        if content is None:
            b64 = (import_file.preview_payload or {}).get("content_b64")
            if b64:
                import base64

                content = base64.b64decode(b64)
        if content is None:
            # Reaplicar a partir do preview se disponível
            preview_rows = (import_file.preview_payload or {}).get("rows") or []
            if not preview_rows:
                raise HTTPException(
                    status_code=400,
                    detail="Conteúdo do arquivo indisponível para confirmação — reenvie o preview",
                )
            run.status = IngestionRunStatus.RUNNING.value
            for entry in preview_rows:
                run.records_read += 1
                if not entry.get("ok"):
                    run.records_rejected += 1
                    continue
                outcome = await self.observations.apply_candidate(
                    series=series,
                    candidate=ObservationCandidate(
                        observation_datetime=datetime.fromisoformat(entry["observation_datetime"]),
                        source_value=Decimal(entry["value"]),
                        source_unit=(import_file.column_mapping or {}).get("unit") or series.source_unit,
                        currency=(import_file.column_mapping or {}).get("currency") or series.currency,
                        published_at=datetime.fromisoformat(entry["observation_datetime"]),
                        raw_payload=entry,
                    ),
                    ingestion_run_id=run.id,
                )
                if outcome.result == ObservationApplyResult.INSERTED:
                    run.records_inserted += 1
                elif outcome.result == ObservationApplyResult.NEW_REVISION:
                    run.records_revised += 1
                elif outcome.result == ObservationApplyResult.SKIPPED_UNCHANGED:
                    run.records_unchanged += 1
                else:
                    run.records_rejected += 1
            import_file.parse_status = ImportParseStatus.APPLIED.value
            run.status = IngestionRunStatus.COMPLETED.value
            run.finished_at = datetime.now(UTC)
            await self.audit.log(
                ctx=audit_ctx,
                entity_type="external_import_file",
                entity_id=import_file.id,
                action="CONFIRM",
                after_data={
                    "inserted": run.records_inserted,
                    "revised": run.records_revised,
                    "unchanged": run.records_unchanged,
                    "rejected": run.records_rejected,
                    "via": "preview_payload",
                },
            )
            await self.db.commit()
            return {
                "run_id": str(run.id),
                "records_read": run.records_read,
                "records_inserted": run.records_inserted,
                "records_revised": run.records_revised,
                "records_unchanged": run.records_unchanged,
                "records_rejected": run.records_rejected,
            }

        mapping = import_file.column_mapping or {}
        date_col = mapping.get("date_column") or "date"
        value_col = mapping.get("value_column") or "value"
        text = content.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))

        for row in reader:
            run.records_read += 1
            raw_date = (row.get(date_col) or "").strip()
            raw_value = (row.get(value_col) or "").strip()
            if not raw_date or not raw_value:
                run.records_rejected += 1
                continue
            try:
                obs_dt = self._parse_date(raw_date, mapping.get("date_format"), mapping.get("timezone"))
                val = parse_decimal(raw_value)
                if val is None:
                    run.records_rejected += 1
                    continue
                outcome = await self.observations.apply_candidate(
                    series=series,
                    candidate=ObservationCandidate(
                        observation_datetime=obs_dt,
                        source_value=val,
                        source_unit=mapping.get("unit") or series.source_unit,
                        currency=mapping.get("currency") or series.currency,
                        published_at=obs_dt,
                        raw_payload=dict(row),
                    ),
                    ingestion_run_id=run.id,
                )
                if outcome.result == ObservationApplyResult.INSERTED:
                    run.records_inserted += 1
                elif outcome.result == ObservationApplyResult.NEW_REVISION:
                    run.records_revised += 1
                elif outcome.result == ObservationApplyResult.SKIPPED_UNCHANGED:
                    run.records_unchanged += 1
                else:
                    run.records_rejected += 1
            except (ValueError, InvalidOperation):
                run.records_rejected += 1

        import_file.parse_status = ImportParseStatus.APPLIED.value
        run.status = IngestionRunStatus.COMPLETED.value
        run.finished_at = datetime.now(UTC)
        await self.audit.log(
            ctx=audit_ctx,
            entity_type="external_import_file",
            entity_id=import_file.id,
            action="CONFIRM",
            after_data={
                "inserted": run.records_inserted,
                "revised": run.records_revised,
                "unchanged": run.records_unchanged,
                "rejected": run.records_rejected,
            },
        )
        await self.db.commit()
        return {
            "run_id": str(run.id),
            "records_read": run.records_read,
            "records_inserted": run.records_inserted,
            "records_revised": run.records_revised,
            "records_unchanged": run.records_unchanged,
            "records_rejected": run.records_rejected,
        }

    def _parse_date(self, raw: str, fmt: str | None, tz_name: str | None) -> datetime:
        from zoneinfo import ZoneInfo

        tz = ZoneInfo(tz_name or "America/Sao_Paulo")
        formats = [fmt] if fmt else ["%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y"]
        for f in formats:
            if not f:
                continue
            try:
                dt = datetime.strptime(raw, f)
                return dt.replace(tzinfo=tz).astimezone(UTC)
            except ValueError:
                continue
        raise ValueError(f"data inválida: {raw}")

    async def analytics_summary(self, organization_id: uuid.UUID) -> dict[str, Any]:
        series_list = await self.list_series(organization_id)
        cards = []
        stale = 0
        for series in series_list:
            fresh = await self.freshness.evaluate_series(series)
            if fresh.status.value in ("STALE", "SOURCE_UNAVAILABLE"):
                stale += 1
            last = None
            if fresh.last_observation_datetime:
                obs = (
                    await self.db.execute(
                        select(ExternalObservation).where(
                            ExternalObservation.series_id == series.id,
                            ExternalObservation.revision_status
                            == ObservationRevisionStatus.CURRENT.value,
                            ExternalObservation.observation_datetime
                            == fresh.last_observation_datetime,
                        )
                    )
                ).scalar_one_or_none()
                last = obs
            change_pct = None
            if last:
                prev = (
                    await self.db.execute(
                        select(ExternalObservation)
                        .where(
                            ExternalObservation.series_id == series.id,
                            ExternalObservation.revision_status
                            == ObservationRevisionStatus.CURRENT.value,
                            ExternalObservation.observation_datetime < last.observation_datetime,
                        )
                        .order_by(ExternalObservation.observation_datetime.desc())
                        .limit(1)
                    )
                ).scalar_one_or_none()
                if prev and prev.canonical_value != 0:
                    change_pct = str(
                        ((last.canonical_value - prev.canonical_value) / prev.canonical_value)
                        * Decimal("100")
                    )
            cards.append(
                {
                    "series_id": str(series.id),
                    "series_code": series.code,
                    "series_name": series.name,
                    "value": str(last.canonical_value) if last else None,
                    "unit": series.canonical_unit,
                    "currency": series.currency,
                    "observation_datetime": last.observation_datetime.isoformat() if last else None,
                    "published_at": last.published_at.isoformat() if last and last.published_at else None,
                    "fetched_at": last.fetched_at.isoformat() if last else None,
                    "freshness": fresh.status.value,
                    "change_pct": change_pct,
                    "frequency": series.frequency,
                    "note": "Variação percentual é descritiva; não implica correlação causal",
                }
            )

        open_issues = (
            await self.db.execute(
                select(func.count())
                .select_from(ExternalQualityIssue)
                .where(
                    ExternalQualityIssue.organization_id == organization_id,
                    ExternalQualityIssue.resolution_status == "OPEN",
                )
            )
        ).scalar_one()

        return {
            "cards": cards,
            "stale_series_count": stale,
            "open_quality_issues": int(open_issues or 0),
            "disclaimer": (
                "Sprint 9 armazena e apresenta séries. Correlação, repasse e previsão "
                "pertencem à Sprint 10 e não estão implementados."
            ),
        }

    async def list_runs(
        self, organization_id: uuid.UUID, limit: int = 50
    ) -> list[ExternalIngestionRun]:
        q = await self.db.execute(
            select(ExternalIngestionRun)
            .where(ExternalIngestionRun.organization_id == organization_id)
            .order_by(ExternalIngestionRun.started_at.desc())
            .limit(limit)
        )
        return list(q.scalars().all())

    async def list_quality_issues(
        self, organization_id: uuid.UUID, open_only: bool = True, limit: int = 100
    ) -> list[ExternalQualityIssue]:
        stmt = select(ExternalQualityIssue).where(
            ExternalQualityIssue.organization_id == organization_id
        )
        if open_only:
            stmt = stmt.where(ExternalQualityIssue.resolution_status == "OPEN")
        q = await self.db.execute(stmt.order_by(ExternalQualityIssue.created_at.desc()).limit(limit))
        return list(q.scalars().all())

    async def enable_scheduler_guard(
        self, source_id: uuid.UUID, organization_id: uuid.UUID, enabled: bool
    ) -> dict[str, Any]:
        source = await self.get_source(source_id, organization_id)
        if enabled:
            required = [
                source.connector_status == ExternalSourceStatus.HOMOLOGATED.value
                or source.status == ExternalSourceStatus.HOMOLOGATED.value,
                bool(source.secret_ref) if source.requires_credentials else True,
                source.terms_review_status == "APPROVED",
                (source.metadata_json or {}).get("contract_validated") is True,
                (source.metadata_json or {}).get("rate_limit") is not None,
                (source.metadata_json or {}).get("manual_homologation_done") is True,
            ]
            if not all(required):
                raise HTTPException(
                    status_code=400,
                    detail={
                        "message": "Scheduler bloqueado até homologação completa",
                        "required": {
                            "status_homologated": required[0],
                            "secret_ref_ok": required[1],
                            "terms_approved": required[2],
                            "contract_validated": required[3],
                            "rate_limit": required[4],
                            "manual_homologation_done": required[5],
                        },
                    },
                )
        source.scheduler_enabled = enabled
        if enabled:
            source.status = ExternalSourceStatus.SCHEDULED.value
        await self.db.commit()
        return {"scheduler_enabled": source.scheduler_enabled, "status": source.status}
