import hashlib
import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.exceptions import AppError
from app.core.master_data_enums import ImportJobStatus, ImportType, MappingSource, MappingStatus
from app.integrations.xpert import csv_importer
from app.models.distributor import ErpSupplier
from app.models.erp_product import ErpProduct
from app.models.import_job import MasterDataImportJob, MasterDataImportRow
from app.models.station import Station
from app.services.audit_service import AuditContext, AuditService
from app.utils.cnpj import normalize_cnpj


class MasterDataImportService:
    _ALLOWED_EXTENSIONS = {".csv"}

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.audit = AuditService(db)

    async def list_jobs(
        self,
        *,
        organization_id: uuid.UUID,
        import_type: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[MasterDataImportJob], int]:
        query = select(MasterDataImportJob).where(
            MasterDataImportJob.organization_id == organization_id
        )
        if import_type:
            query = query.where(MasterDataImportJob.import_type == import_type)
        if status:
            query = query.where(MasterDataImportJob.status == status)

        count_q = select(func.count()).select_from(query.subquery())
        total = int((await self.db.execute(count_q)).scalar_one())

        query = (
            query.order_by(MasterDataImportJob.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def get_job(self, job_id: uuid.UUID, organization_id: uuid.UUID) -> MasterDataImportJob:
        result = await self.db.execute(
            select(MasterDataImportJob)
            .options(selectinload(MasterDataImportJob.rows))
            .where(
                MasterDataImportJob.id == job_id,
                MasterDataImportJob.organization_id == organization_id,
            )
        )
        job = result.scalar_one_or_none()
        if job is None:
            raise AppError("Importação não encontrada.", status_code=404, code="NOT_FOUND")
        return job

    async def _ensure_station(self, station_id: uuid.UUID, organization_id: uuid.UUID) -> Station:
        station = await self.db.get(Station, station_id)
        if station is None or station.organization_id != organization_id:
            raise AppError(
                "Os cadastros informados não pertencem à mesma organização.",
                status_code=400,
                code="CROSS_ORGANIZATION_REFERENCE",
            )
        return station

    def _validate_file(self, *, file_name: str, content: bytes) -> None:
        suffix = Path(file_name).suffix.lower()
        if suffix not in self._ALLOWED_EXTENSIONS:
            raise AppError(
                "O arquivo não possui o formato esperado.",
                status_code=400,
                code="INVALID_IMPORT_FILE",
            )
        if len(content) == 0:
            raise AppError(
                "O arquivo está vazio.",
                status_code=400,
                code="INVALID_IMPORT_FILE",
            )
        if len(content) > settings.master_data_import_max_bytes:
            raise AppError(
                "O arquivo excede o tamanho máximo permitido.",
                status_code=400,
                code="INVALID_IMPORT_FILE",
            )

    def _file_hash(self, content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()

    async def _load_existing_erp_product(
        self, station_id: uuid.UUID, erp_product_id: str
    ) -> ErpProduct | None:
        result = await self.db.execute(
            select(ErpProduct).where(
                ErpProduct.station_id == station_id,
                ErpProduct.erp_product_id == erp_product_id,
            )
        )
        return result.scalar_one_or_none()

    async def _load_existing_erp_supplier(
        self, station_id: uuid.UUID, erp_entity_id: str
    ) -> ErpSupplier | None:
        result = await self.db.execute(
            select(ErpSupplier).where(
                ErpSupplier.station_id == station_id,
                ErpSupplier.erp_entity_id == erp_entity_id,
            )
        )
        return result.scalar_one_or_none()

    def _erp_product_origin_changed(self, existing: ErpProduct, data: dict) -> bool:
        fields = (
            "erp_product_code",
            "erp_description",
            "erp_unit",
            "erp_group_id",
            "erp_group_name",
            "erp_subgroup_id",
            "erp_subgroup_name",
        )
        return any(getattr(existing, field) != data.get(field) for field in fields)

    def _erp_supplier_origin_changed(self, existing: ErpSupplier, data: dict) -> bool:
        fields = ("erp_entity_code", "erp_name", "erp_cnpj")
        return any(getattr(existing, field) != data.get(field) for field in fields)

    async def upload_and_validate(
        self,
        *,
        organization_id: uuid.UUID,
        station_id: uuid.UUID,
        import_type: ImportType,
        file_name: str,
        content: bytes,
        created_by: uuid.UUID,
        audit_ctx: AuditContext,
    ) -> MasterDataImportJob:
        self._validate_file(file_name=file_name, content=content)
        await self._ensure_station(station_id, organization_id)

        now = datetime.now(UTC)
        file_hash = self._file_hash(content)
        job = MasterDataImportJob(
            organization_id=organization_id,
            station_id=station_id,
            import_type=import_type.value,
            source_file_name=file_name,
            source_file_hash=file_hash,
            status=ImportJobStatus.VALIDATING,
            created_by=created_by,
            created_at=now,
            started_at=now,
        )
        self.db.add(job)
        await self.db.flush()

        try:
            headers, raw_rows = csv_importer.parse_csv_content(content)
            missing = csv_importer.validate_headers(headers, import_type)
            if missing:
                job.status = ImportJobStatus.FAILED
                job.finished_at = datetime.now(UTC)
                job.error_summary = {"missing_columns": missing}
                await self.db.flush()
                await self.audit.log(
                    ctx=audit_ctx,
                    entity_type="master_data_import",
                    entity_id=job.id,
                    action="upload_failed",
                    after_data=self._serialize_job(job),
                    metadata={"missing_columns": missing},
                )
                raise AppError(
                    "O arquivo não possui o formato esperado.",
                    status_code=400,
                    code="INVALID_IMPORT_FILE",
                )

            seen_identifiers: set[str] = set()
            valid_count = 0
            failed_count = 0
            insert_count = 0
            update_count = 0
            unchanged_count = 0

            for index, raw_row in enumerate(raw_rows, start=2):
                errors = csv_importer.validate_row(raw_row, import_type)
                normalized = csv_importer.normalize_row(raw_row, import_type)
                identifier = csv_importer.external_identifier(normalized, import_type)

                if identifier and identifier in seen_identifiers:
                    errors["duplicate"] = "Identificador duplicado no arquivo."
                elif identifier:
                    seen_identifiers.add(identifier)

                if errors:
                    action = "ERROR"
                    status = "INVALID"
                    failed_count += 1
                else:
                    if import_type == ImportType.ERP_PRODUCTS:
                        existing = await self._load_existing_erp_product(
                            station_id, normalized["erp_product_id"]
                        )
                        if existing is None:
                            action = "INSERT"
                            update_count += 0
                            insert_count += 1
                        elif self._erp_product_origin_changed(existing, normalized):
                            action = "UPDATE"
                            update_count += 1
                        else:
                            action = "UNCHANGED"
                            unchanged_count += 1
                    else:
                        cnpj = normalized.get("erp_cnpj")
                        if cnpj:
                            normalized["erp_cnpj"] = normalize_cnpj(cnpj) or None
                        existing = await self._load_existing_erp_supplier(
                            station_id, normalized["erp_entity_id"]
                        )
                        if existing is None:
                            action = "INSERT"
                            insert_count += 1
                        elif self._erp_supplier_origin_changed(existing, normalized):
                            action = "UPDATE"
                            update_count += 1
                        else:
                            action = "UNCHANGED"
                            unchanged_count += 1
                    status = "VALID"
                    valid_count += 1

                self.db.add(
                    MasterDataImportRow(
                        import_job_id=job.id,
                        row_number=index,
                        external_identifier=identifier,
                        action=action,
                        status=status,
                        raw_data=dict(raw_row),
                        normalized_data=normalized if not errors else None,
                        validation_errors=errors or None,
                    )
                )

            job.records_total = len(raw_rows)
            job.records_valid = valid_count
            job.records_failed = failed_count
            job.records_inserted = insert_count
            job.records_updated = update_count
            job.records_unchanged = unchanged_count
            job.finished_at = datetime.now(UTC)

            if valid_count == 0:
                job.status = ImportJobStatus.FAILED
                job.error_summary = {"message": "Nenhuma linha válida encontrada."}
            else:
                job.status = ImportJobStatus.READY

        except AppError:
            await self.db.flush()
            raise
        except UnicodeDecodeError as exc:
            job.status = ImportJobStatus.FAILED
            job.finished_at = datetime.now(UTC)
            job.error_summary = {"message": "Encoding do arquivo inválido."}
            await self.db.flush()
            raise AppError(
                "O arquivo não possui o formato esperado.",
                status_code=400,
                code="INVALID_IMPORT_FILE",
            ) from exc

        await self.audit.log(
            ctx=audit_ctx,
            entity_type="master_data_import",
            entity_id=job.id,
            action="upload",
            after_data=self._serialize_job(job),
            metadata={"import_type": import_type.value, "station_id": str(station_id)},
        )
        return job

    async def confirm(self, *, job: MasterDataImportJob, audit_ctx: AuditContext) -> MasterDataImportJob:
        if job.status != ImportJobStatus.READY:
            raise AppError(
                "A importação não está pronta para confirmação.",
                status_code=400,
                code="IMPORT_NOT_READY",
            )

        before = self._serialize_job(job)
        job.status = ImportJobStatus.PROCESSING
        job.started_at = datetime.now(UTC)
        now = datetime.now(UTC)

        result = await self.db.execute(
            select(MasterDataImportRow)
            .where(MasterDataImportRow.import_job_id == job.id)
            .order_by(MasterDataImportRow.row_number)
        )
        rows = list(result.scalars().all())

        inserted = 0
        updated = 0
        unchanged = 0
        failed = 0
        import_type = ImportType(job.import_type)

        for row in rows:
            if row.status != "VALID" or row.action == "ERROR":
                failed += 1
                continue

            data = row.normalized_data or {}
            try:
                if import_type == ImportType.ERP_PRODUCTS:
                    outcome = await self._process_erp_product_row(
                        job=job, data=data, action=row.action, now=now
                    )
                else:
                    outcome = await self._process_erp_supplier_row(
                        job=job, data=data, action=row.action, now=now
                    )

                row.processed_at = now
                if outcome == "INSERT":
                    inserted += 1
                elif outcome == "UPDATE":
                    updated += 1
                else:
                    unchanged += 1
            except Exception:
                row.status = "INVALID"
                row.validation_errors = {"processing": "Falha ao processar a linha."}
                failed += 1

        job.records_inserted = inserted
        job.records_updated = updated
        job.records_unchanged = unchanged
        job.records_failed = failed
        job.finished_at = now

        if failed and (inserted or updated):
            job.status = ImportJobStatus.PARTIAL
        elif failed:
            job.status = ImportJobStatus.FAILED
        else:
            job.status = ImportJobStatus.SUCCESS

        await self.audit.log(
            ctx=audit_ctx,
            entity_type="master_data_import",
            entity_id=job.id,
            action="confirm",
            before_data=before,
            after_data=self._serialize_job(job),
        )
        return job

    async def _process_erp_product_row(
        self, *, job: MasterDataImportJob, data: dict, action: str, now: datetime
    ) -> str:
        existing = await self._load_existing_erp_product(job.station_id, data["erp_product_id"])
        if existing is None:
            self.db.add(
                ErpProduct(
                    organization_id=job.organization_id,
                    station_id=job.station_id,
                    erp_product_id=data["erp_product_id"],
                    erp_product_code=data.get("erp_product_code"),
                    erp_description=data["erp_description"],
                    erp_unit=data.get("erp_unit"),
                    erp_group_id=data.get("erp_group_id"),
                    erp_group_name=data.get("erp_group_name"),
                    erp_subgroup_id=data.get("erp_subgroup_id"),
                    erp_subgroup_name=data.get("erp_subgroup_name"),
                    mapping_status=MappingStatus.PENDING,
                    mapping_source=MappingSource.CSV,
                    raw_payload=data,
                    last_synced_at=now,
                    active=True,
                )
            )
            return "INSERT"

        if action == "UNCHANGED":
            return "UNCHANGED"

        existing.erp_product_code = data.get("erp_product_code")
        existing.erp_description = data["erp_description"]
        existing.erp_unit = data.get("erp_unit")
        existing.erp_group_id = data.get("erp_group_id")
        existing.erp_group_name = data.get("erp_group_name")
        existing.erp_subgroup_id = data.get("erp_subgroup_id")
        existing.erp_subgroup_name = data.get("erp_subgroup_name")
        existing.raw_payload = data
        existing.last_synced_at = now
        existing.updated_at = now
        if existing.mapping_status == MappingStatus.PENDING:
            existing.mapping_source = MappingSource.CSV
        return "UPDATE"

    async def _process_erp_supplier_row(
        self, *, job: MasterDataImportJob, data: dict, action: str, now: datetime
    ) -> str:
        existing = await self._load_existing_erp_supplier(job.station_id, data["erp_entity_id"])
        if existing is None:
            self.db.add(
                ErpSupplier(
                    organization_id=job.organization_id,
                    station_id=job.station_id,
                    erp_entity_id=data["erp_entity_id"],
                    erp_entity_code=data.get("erp_entity_code"),
                    erp_name=data["erp_name"],
                    erp_cnpj=data.get("erp_cnpj"),
                    mapping_status=MappingStatus.PENDING,
                    raw_payload=data,
                    last_synced_at=now,
                    active=True,
                )
            )
            return "INSERT"

        if action == "UNCHANGED":
            return "UNCHANGED"

        existing.erp_entity_code = data.get("erp_entity_code")
        existing.erp_name = data["erp_name"]
        existing.erp_cnpj = data.get("erp_cnpj")
        existing.raw_payload = data
        existing.last_synced_at = now
        existing.updated_at = now
        return "UPDATE"

    async def cancel(self, *, job: MasterDataImportJob, audit_ctx: AuditContext) -> MasterDataImportJob:
        if job.status in (
            ImportJobStatus.PROCESSING,
            ImportJobStatus.SUCCESS,
            ImportJobStatus.PARTIAL,
            ImportJobStatus.FAILED,
            ImportJobStatus.CANCELLED,
        ):
            raise AppError(
                "Esta importação já foi processada ou não pode ser cancelada.",
                status_code=400,
                code="IMPORT_ALREADY_PROCESSED",
            )

        before = self._serialize_job(job)
        job.status = ImportJobStatus.CANCELLED
        job.finished_at = datetime.now(UTC)
        await self.audit.log(
            ctx=audit_ctx,
            entity_type="master_data_import",
            entity_id=job.id,
            action="cancel",
            before_data=before,
            after_data=self._serialize_job(job),
        )
        return job

    def _serialize_job(self, job: MasterDataImportJob) -> dict:
        return {
            "id": str(job.id),
            "organization_id": str(job.organization_id),
            "station_id": str(job.station_id) if job.station_id else None,
            "import_type": job.import_type,
            "source_file_name": job.source_file_name,
            "source_file_hash": job.source_file_hash,
            "status": job.status,
            "records_total": job.records_total,
            "records_valid": job.records_valid,
            "records_inserted": job.records_inserted,
            "records_updated": job.records_updated,
            "records_unchanged": job.records_unchanged,
            "records_failed": job.records_failed,
            "error_summary": job.error_summary,
            "created_by": str(job.created_by),
            "created_at": job.created_at.isoformat(),
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "finished_at": job.finished_at.isoformat() if job.finished_at else None,
        }
