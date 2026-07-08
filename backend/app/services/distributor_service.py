import uuid
from datetime import UTC, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.core.master_data_enums import MappingStatus, RegistrationStatus
from app.models.distributor import Distributor, ErpSupplier
from app.models.station import Station
from app.services.audit_service import AuditContext, AuditService
from app.utils.cnpj import normalize_cnpj, validate_cnpj
from app.utils.text import normalize_name


class DistributorService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.audit = AuditService(db)

    async def list_distributors(
        self,
        *,
        organization_id: uuid.UUID,
        search: str | None = None,
        registration_status: str | None = None,
        active: bool | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Distributor], int]:
        query = select(Distributor).where(Distributor.organization_id == organization_id)
        if search:
            term = f"%{search}%"
            query = query.where(
                or_(
                    Distributor.trade_name.ilike(term),
                    Distributor.corporate_name.ilike(term),
                    Distributor.internal_code.ilike(term),
                    Distributor.cnpj.ilike(term),
                )
            )
        if registration_status:
            query = query.where(Distributor.registration_status == registration_status)
        if active is not None:
            query = query.where(Distributor.active.is_(active))

        count_q = select(func.count()).select_from(query.subquery())
        total = int((await self.db.execute(count_q)).scalar_one())

        query = (
            query.order_by(Distributor.trade_name)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def get_by_id(self, distributor_id: uuid.UUID, organization_id: uuid.UUID) -> Distributor:
        distributor = await self.db.get(Distributor, distributor_id)
        if distributor is None or distributor.organization_id != organization_id:
            raise AppError("Distribuidora não encontrada.", status_code=404, code="NOT_FOUND")
        return distributor

    def _registration_status_for_cnpj(self, cnpj: str | None) -> str:
        return RegistrationStatus.COMPLETE if cnpj else RegistrationStatus.INCOMPLETE

    async def _ensure_cnpj_unique(
        self,
        organization_id: uuid.UUID,
        cnpj: str | None,
        exclude_id: uuid.UUID | None = None,
    ) -> None:
        if not cnpj:
            return
        query = select(Distributor).where(
            Distributor.organization_id == organization_id,
            Distributor.cnpj == cnpj,
            Distributor.active.is_(True),
        )
        if exclude_id:
            query = query.where(Distributor.id != exclude_id)
        existing = await self.db.execute(query)
        if existing.scalar_one_or_none():
            raise AppError(
                "Já existe uma distribuidora com este CNPJ.",
                status_code=409,
                code="DISTRIBUTOR_CNPJ_ALREADY_EXISTS",
            )

    async def _ensure_normalized_name_unique(
        self,
        organization_id: uuid.UUID,
        normalized_name: str,
        *,
        confirm_duplicate: bool = False,
        exclude_id: uuid.UUID | None = None,
    ) -> None:
        query = select(Distributor).where(
            Distributor.organization_id == organization_id,
            Distributor.normalized_name == normalized_name,
            Distributor.active.is_(True),
        )
        if exclude_id:
            query = query.where(Distributor.id != exclude_id)
        existing = await self.db.execute(query)
        if existing.scalar_one_or_none() and not confirm_duplicate:
            raise AppError(
                "Já existe uma distribuidora ativa com nome semelhante.",
                status_code=409,
                code="DISTRIBUTOR_POSSIBLE_DUPLICATE",
            )

    async def create(
        self, *, organization_id: uuid.UUID, data: dict, audit_ctx: AuditContext
    ) -> Distributor:
        cnpj_raw = data.get("cnpj")
        cnpj = normalize_cnpj(cnpj_raw) if cnpj_raw else None
        if cnpj and not validate_cnpj(cnpj):
            raise AppError("CNPJ inválido.", status_code=400, code="INVALID_CNPJ")

        trade_name = str(data["trade_name"]).strip()
        corporate_name = str(data["corporate_name"]).strip()
        if not trade_name or not corporate_name:
            raise AppError(
                "Razão social e nome fantasia são obrigatórios.",
                status_code=400,
                code="VALIDATION_ERROR",
            )

        normalized = normalize_name(trade_name)
        await self._ensure_cnpj_unique(organization_id, cnpj)
        await self._ensure_normalized_name_unique(
            organization_id,
            normalized,
            confirm_duplicate=data.get("confirm_duplicate", False),
        )

        distributor = Distributor(
            organization_id=organization_id,
            internal_code=str(data["internal_code"]).strip(),
            corporate_name=corporate_name,
            trade_name=trade_name,
            cnpj=cnpj,
            normalized_name=normalized,
            registration_status=self._registration_status_for_cnpj(cnpj),
            notes=data.get("notes"),
            active=data.get("active", True),
        )
        self.db.add(distributor)
        await self.db.flush()
        await self.audit.log(
            ctx=audit_ctx,
            entity_type="distributor",
            entity_id=distributor.id,
            action="create",
            after_data=self._serialize(distributor),
        )
        return distributor

    async def update(
        self, *, distributor: Distributor, data: dict, audit_ctx: AuditContext
    ) -> Distributor:
        before = self._serialize(distributor)

        for field in ("internal_code", "corporate_name", "notes", "active"):
            if field in data:
                setattr(distributor, field, data[field])

        if "trade_name" in data:
            trade_name = str(data["trade_name"]).strip()
            if not trade_name:
                raise AppError("Nome fantasia é obrigatório.", status_code=400, code="VALIDATION_ERROR")
            distributor.trade_name = trade_name
            distributor.normalized_name = normalize_name(trade_name)
            await self._ensure_normalized_name_unique(
                distributor.organization_id,
                distributor.normalized_name,
                confirm_duplicate=data.get("confirm_duplicate", False),
                exclude_id=distributor.id,
            )

        if "corporate_name" in data:
            corporate_name = str(data["corporate_name"]).strip()
            if not corporate_name:
                raise AppError("Razão social é obrigatória.", status_code=400, code="VALIDATION_ERROR")
            distributor.corporate_name = corporate_name

        if "cnpj" in data:
            cnpj_raw = data["cnpj"]
            cnpj = normalize_cnpj(cnpj_raw) if cnpj_raw else None
            if cnpj and not validate_cnpj(cnpj):
                raise AppError("CNPJ inválido.", status_code=400, code="INVALID_CNPJ")
            await self._ensure_cnpj_unique(distributor.organization_id, cnpj, exclude_id=distributor.id)
            distributor.cnpj = cnpj
            distributor.registration_status = self._registration_status_for_cnpj(cnpj)

        distributor.updated_at = datetime.now(UTC)
        await self.audit.log(
            ctx=audit_ctx,
            entity_type="distributor",
            entity_id=distributor.id,
            action="update",
            before_data=before,
            after_data=self._serialize(distributor),
        )
        return distributor

    async def deactivate(
        self, *, distributor: Distributor, reason: str, audit_ctx: AuditContext
    ) -> Distributor:
        before = self._serialize(distributor)
        distributor.active = False
        distributor.updated_at = datetime.now(UTC)
        await self.audit.log(
            ctx=audit_ctx,
            entity_type="distributor",
            entity_id=distributor.id,
            action="deactivate",
            before_data=before,
            after_data=self._serialize(distributor),
            metadata={"reason": reason},
        )
        return distributor

    async def reactivate(self, *, distributor: Distributor, audit_ctx: AuditContext) -> Distributor:
        if distributor.cnpj:
            await self._ensure_cnpj_unique(distributor.organization_id, distributor.cnpj, exclude_id=distributor.id)
        await self._ensure_normalized_name_unique(
            distributor.organization_id,
            distributor.normalized_name,
            confirm_duplicate=True,
            exclude_id=distributor.id,
        )
        before = self._serialize(distributor)
        distributor.active = True
        distributor.updated_at = datetime.now(UTC)
        await self.audit.log(
            ctx=audit_ctx,
            entity_type="distributor",
            entity_id=distributor.id,
            action="reactivate",
            before_data=before,
            after_data=self._serialize(distributor),
        )
        return distributor

    # --- ERP Suppliers ---

    async def list_erp_suppliers(
        self,
        *,
        organization_id: uuid.UUID,
        station_id: uuid.UUID | None = None,
        mapping_status: str | None = None,
        distributor_id: uuid.UUID | None = None,
        search: str | None = None,
        active: bool | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[ErpSupplier], int]:
        query = select(ErpSupplier).where(ErpSupplier.organization_id == organization_id)
        if station_id:
            query = query.where(ErpSupplier.station_id == station_id)
        if mapping_status:
            query = query.where(ErpSupplier.mapping_status == mapping_status)
        if distributor_id:
            query = query.where(ErpSupplier.distributor_id == distributor_id)
        if active is not None:
            query = query.where(ErpSupplier.active.is_(active))
        if search:
            term = f"%{search}%"
            query = query.where(
                or_(
                    ErpSupplier.erp_entity_id.ilike(term),
                    ErpSupplier.erp_entity_code.ilike(term),
                    ErpSupplier.erp_name.ilike(term),
                )
            )

        count_q = select(func.count()).select_from(query.subquery())
        total = int((await self.db.execute(count_q)).scalar_one())

        query = (
            query.order_by(ErpSupplier.updated_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def get_erp_supplier_by_id(
        self, erp_supplier_id: uuid.UUID, organization_id: uuid.UUID
    ) -> ErpSupplier:
        erp_supplier = await self.db.get(ErpSupplier, erp_supplier_id)
        if erp_supplier is None or erp_supplier.organization_id != organization_id:
            raise AppError("Fornecedor ERP não encontrado.", status_code=404, code="NOT_FOUND")
        return erp_supplier

    async def _ensure_distributor_for_mapping(
        self, distributor_id: uuid.UUID, organization_id: uuid.UUID
    ) -> Distributor:
        distributor = await self.get_by_id(distributor_id, organization_id)
        if not distributor.active:
            raise AppError(
                "Não é possível mapear para uma distribuidora inativa.",
                status_code=400,
                code="VALIDATION_ERROR",
            )
        return distributor

    async def map_erp_supplier(
        self,
        *,
        erp_supplier: ErpSupplier,
        distributor_id: uuid.UUID,
        user_id: uuid.UUID,
        reason: str | None,
        audit_ctx: AuditContext,
    ) -> ErpSupplier:
        before = self._serialize_erp_supplier(erp_supplier)
        distributor = await self._ensure_distributor_for_mapping(
            distributor_id, erp_supplier.organization_id
        )

        is_remap = (
            erp_supplier.mapping_status == MappingStatus.MAPPED
            and erp_supplier.distributor_id != distributor.id
        )
        if is_remap and not (reason and reason.strip()):
            raise AppError(
                "Motivo é obrigatório para remapeamento.",
                status_code=400,
                code="MAPPING_REASON_REQUIRED",
            )

        now = datetime.now(UTC)
        erp_supplier.distributor_id = distributor.id
        erp_supplier.mapping_status = MappingStatus.MAPPED
        erp_supplier.mapped_by = user_id
        erp_supplier.mapped_at = now
        erp_supplier.ignore_reason = None
        erp_supplier.updated_at = now

        await self.audit.log(
            ctx=audit_ctx,
            entity_type="erp_supplier",
            entity_id=erp_supplier.id,
            action="map" if not is_remap else "remap",
            before_data=before,
            after_data=self._serialize_erp_supplier(erp_supplier),
            metadata={"reason": reason, "distributor_id": str(distributor.id)},
        )
        return erp_supplier

    async def ignore_erp_supplier(
        self,
        *,
        erp_supplier: ErpSupplier,
        user_id: uuid.UUID,
        reason: str,
        audit_ctx: AuditContext,
    ) -> ErpSupplier:
        if not reason or not reason.strip():
            raise AppError(
                "Motivo é obrigatório para ignorar o fornecedor.",
                status_code=400,
                code="MAPPING_REASON_REQUIRED",
            )

        before = self._serialize_erp_supplier(erp_supplier)
        now = datetime.now(UTC)
        erp_supplier.mapping_status = MappingStatus.IGNORED
        erp_supplier.distributor_id = None
        erp_supplier.ignore_reason = reason.strip()
        erp_supplier.mapped_by = user_id
        erp_supplier.mapped_at = now
        erp_supplier.updated_at = now

        await self.audit.log(
            ctx=audit_ctx,
            entity_type="erp_supplier",
            entity_id=erp_supplier.id,
            action="ignore",
            before_data=before,
            after_data=self._serialize_erp_supplier(erp_supplier),
            metadata={"reason": reason},
        )
        return erp_supplier

    async def reopen_erp_supplier(
        self,
        *,
        erp_supplier: ErpSupplier,
        user_id: uuid.UUID,
        reason: str | None,
        audit_ctx: AuditContext,
    ) -> ErpSupplier:
        if erp_supplier.mapping_status not in (MappingStatus.IGNORED, MappingStatus.CONFLICT):
            raise AppError(
                "Somente fornecedores ignorados ou em conflito podem ser reabertos.",
                status_code=400,
                code="VALIDATION_ERROR",
            )

        before = self._serialize_erp_supplier(erp_supplier)
        now = datetime.now(UTC)
        erp_supplier.mapping_status = MappingStatus.PENDING
        erp_supplier.distributor_id = None
        erp_supplier.ignore_reason = None
        erp_supplier.mapped_by = None
        erp_supplier.mapped_at = None
        erp_supplier.updated_at = now

        await self.audit.log(
            ctx=audit_ctx,
            entity_type="erp_supplier",
            entity_id=erp_supplier.id,
            action="reopen",
            before_data=before,
            after_data=self._serialize_erp_supplier(erp_supplier),
            metadata={"reason": reason, "reopened_by": str(user_id)},
        )
        return erp_supplier

    async def _ensure_station(self, station_id: uuid.UUID, organization_id: uuid.UUID) -> Station:
        station = await self.db.get(Station, station_id)
        if station is None or station.organization_id != organization_id:
            raise AppError(
                "Os cadastros informados não pertencem à mesma organização.",
                status_code=400,
                code="CROSS_ORGANIZATION_REFERENCE",
            )
        return station

    def _serialize(self, distributor: Distributor) -> dict:
        return {
            "id": str(distributor.id),
            "organization_id": str(distributor.organization_id),
            "internal_code": distributor.internal_code,
            "corporate_name": distributor.corporate_name,
            "trade_name": distributor.trade_name,
            "cnpj": distributor.cnpj,
            "normalized_name": distributor.normalized_name,
            "registration_status": distributor.registration_status,
            "notes": distributor.notes,
            "active": distributor.active,
        }

    def _serialize_erp_supplier(self, erp_supplier: ErpSupplier) -> dict:
        return {
            "id": str(erp_supplier.id),
            "organization_id": str(erp_supplier.organization_id),
            "station_id": str(erp_supplier.station_id),
            "erp_entity_id": erp_supplier.erp_entity_id,
            "erp_entity_code": erp_supplier.erp_entity_code,
            "erp_name": erp_supplier.erp_name,
            "erp_cnpj": erp_supplier.erp_cnpj,
            "distributor_id": (
                str(erp_supplier.distributor_id) if erp_supplier.distributor_id else None
            ),
            "mapping_status": erp_supplier.mapping_status,
            "ignore_reason": erp_supplier.ignore_reason,
            "mapped_by": str(erp_supplier.mapped_by) if erp_supplier.mapped_by else None,
            "mapped_at": erp_supplier.mapped_at.isoformat() if erp_supplier.mapped_at else None,
            "active": erp_supplier.active,
        }
