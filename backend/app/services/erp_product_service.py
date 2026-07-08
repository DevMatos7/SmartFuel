import uuid
from datetime import UTC, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.core.master_data_enums import MappingSource, MappingStatus
from app.models.erp_product import ErpProduct, ProductMappingHistory
from app.models.product import Product
from app.models.station import Station
from app.services.audit_service import AuditContext, AuditService
from app.services.product_service import ProductService


class ErpProductService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.audit = AuditService(db)
        self.product_service = ProductService(db)

    async def list_erp_products(
        self,
        *,
        organization_id: uuid.UUID,
        station_id: uuid.UUID | None = None,
        mapping_status: str | None = None,
        canonical_product_id: uuid.UUID | None = None,
        search: str | None = None,
        source: str | None = None,
        active: bool | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[ErpProduct], int]:
        query = select(ErpProduct).where(ErpProduct.organization_id == organization_id)
        if station_id:
            query = query.where(ErpProduct.station_id == station_id)
        if mapping_status:
            query = query.where(ErpProduct.mapping_status == mapping_status)
        if canonical_product_id:
            query = query.where(ErpProduct.canonical_product_id == canonical_product_id)
        if source:
            query = query.where(ErpProduct.mapping_source == source)
        if active is not None:
            query = query.where(ErpProduct.active.is_(active))
        if search:
            term = f"%{search}%"
            query = query.where(
                or_(
                    ErpProduct.erp_product_id.ilike(term),
                    ErpProduct.erp_product_code.ilike(term),
                    ErpProduct.erp_description.ilike(term),
                )
            )

        count_q = select(func.count()).select_from(query.subquery())
        total = int((await self.db.execute(count_q)).scalar_one())

        query = (
            query.order_by(ErpProduct.updated_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def get_by_id(self, erp_product_id: uuid.UUID, organization_id: uuid.UUID) -> ErpProduct:
        erp_product = await self.db.get(ErpProduct, erp_product_id)
        if erp_product is None or erp_product.organization_id != organization_id:
            raise AppError("Produto ERP não encontrado.", status_code=404, code="NOT_FOUND")
        return erp_product

    async def get_status_counts(
        self, *, organization_id: uuid.UUID, station_id: uuid.UUID | None = None
    ) -> dict[str, int]:
        query = (
            select(ErpProduct.mapping_status, func.count())
            .where(ErpProduct.organization_id == organization_id, ErpProduct.active.is_(True))
            .group_by(ErpProduct.mapping_status)
        )
        if station_id:
            query = query.where(ErpProduct.station_id == station_id)
        result = await self.db.execute(query)
        counts = {status.value: 0 for status in MappingStatus}
        for status, count in result.all():
            counts[status] = int(count)
        return counts

    async def get_history(
        self, *, erp_product: ErpProduct, organization_id: uuid.UUID
    ) -> list[ProductMappingHistory]:
        if erp_product.organization_id != organization_id:
            raise AppError("Produto ERP não encontrado.", status_code=404, code="NOT_FOUND")
        result = await self.db.execute(
            select(ProductMappingHistory)
            .where(ProductMappingHistory.erp_product_id == erp_product.id)
            .order_by(ProductMappingHistory.created_at.desc())
        )
        return list(result.scalars().all())

    async def _ensure_station(self, station_id: uuid.UUID, organization_id: uuid.UUID) -> Station:
        station = await self.db.get(Station, station_id)
        if station is None or station.organization_id != organization_id:
            raise AppError(
                "Os cadastros informados não pertencem à mesma organização.",
                status_code=400,
                code="CROSS_ORGANIZATION_REFERENCE",
            )
        return station

    async def _ensure_canonical_product(
        self, product_id: uuid.UUID, organization_id: uuid.UUID, *, for_mapping: bool = True
    ) -> Product:
        product = await self.product_service.get_by_id(product_id, organization_id)
        if for_mapping and not product.active:
            raise AppError(
                "Não é possível mapear para um produto inativo.",
                status_code=400,
                code="INVALID_PRODUCT_MAPPING",
            )
        return product

    async def _record_history(
        self,
        *,
        erp_product: ErpProduct,
        previous_product_id: uuid.UUID | None,
        new_product_id: uuid.UUID | None,
        previous_status: str | None,
        new_status: str,
        reason: str | None,
        changed_by: uuid.UUID,
    ) -> ProductMappingHistory:
        entry = ProductMappingHistory(
            erp_product_id=erp_product.id,
            previous_product_id=previous_product_id,
            new_product_id=new_product_id,
            previous_status=previous_status,
            new_status=new_status,
            reason=reason,
            changed_by=changed_by,
            created_at=datetime.now(UTC),
        )
        self.db.add(entry)
        await self.db.flush()
        return entry

    async def map_product(
        self,
        *,
        erp_product: ErpProduct,
        canonical_product_id: uuid.UUID,
        user_id: uuid.UUID,
        reason: str | None,
        audit_ctx: AuditContext,
    ) -> ErpProduct:
        before = self._serialize(erp_product)
        canonical = await self._ensure_canonical_product(
            canonical_product_id, erp_product.organization_id
        )

        previous_status = erp_product.mapping_status
        previous_product_id = erp_product.canonical_product_id
        is_remap = previous_status == MappingStatus.MAPPED and previous_product_id != canonical_product_id

        if is_remap and not (reason and reason.strip()):
            raise AppError(
                "Motivo é obrigatório para remapeamento.",
                status_code=400,
                code="MAPPING_REASON_REQUIRED",
            )

        now = datetime.now(UTC)
        erp_product.canonical_product_id = canonical.id
        erp_product.mapping_status = MappingStatus.MAPPED
        erp_product.mapping_source = MappingSource.MANUAL
        erp_product.mapped_by = user_id
        erp_product.mapped_at = now
        erp_product.ignore_reason = None
        erp_product.updated_at = now

        await self.product_service.lock_code_if_used(canonical)
        await self._record_history(
            erp_product=erp_product,
            previous_product_id=previous_product_id,
            new_product_id=canonical.id,
            previous_status=previous_status,
            new_status=MappingStatus.MAPPED,
            reason=reason,
            changed_by=user_id,
        )
        await self.audit.log(
            ctx=audit_ctx,
            entity_type="erp_product",
            entity_id=erp_product.id,
            action="map" if not is_remap else "remap",
            before_data=before,
            after_data=self._serialize(erp_product),
            metadata={"reason": reason, "canonical_product_id": str(canonical.id)},
        )
        return erp_product

    async def bulk_map(
        self,
        *,
        organization_id: uuid.UUID,
        erp_product_ids: list[uuid.UUID],
        canonical_product_id: uuid.UUID,
        user_id: uuid.UUID,
        reason: str | None,
        audit_ctx: AuditContext,
    ) -> tuple[list[ErpProduct], list[dict]]:
        if not erp_product_ids:
            raise AppError(
                "Nenhum produto ERP selecionado.",
                status_code=400,
                code="VALIDATION_ERROR",
            )

        canonical = await self._ensure_canonical_product(canonical_product_id, organization_id)
        mapped: list[ErpProduct] = []
        failures: list[dict] = []

        for erp_id in erp_product_ids:
            try:
                erp_product = await self.get_by_id(erp_id, organization_id)
                mapped_product = await self.map_product(
                    erp_product=erp_product,
                    canonical_product_id=canonical.id,
                    user_id=user_id,
                    reason=reason,
                    audit_ctx=audit_ctx,
                )
                mapped.append(mapped_product)
            except AppError as exc:
                failures.append({"erp_product_id": str(erp_id), "code": exc.code, "message": exc.message})

        if mapped:
            await self.audit.log(
                ctx=audit_ctx,
                entity_type="erp_product",
                entity_id=None,
                action="bulk_map",
                after_data={
                    "canonical_product_id": str(canonical.id),
                    "mapped_count": len(mapped),
                    "failed_count": len(failures),
                },
                metadata={"reason": reason},
            )
        return mapped, failures

    async def ignore_product(
        self,
        *,
        erp_product: ErpProduct,
        user_id: uuid.UUID,
        reason: str,
        audit_ctx: AuditContext,
    ) -> ErpProduct:
        if not reason or not reason.strip():
            raise AppError(
                "Motivo é obrigatório para ignorar o produto.",
                status_code=400,
                code="MAPPING_REASON_REQUIRED",
            )

        before = self._serialize(erp_product)
        previous_status = erp_product.mapping_status
        previous_product_id = erp_product.canonical_product_id
        now = datetime.now(UTC)

        erp_product.mapping_status = MappingStatus.IGNORED
        erp_product.mapping_source = MappingSource.MANUAL
        erp_product.canonical_product_id = None
        erp_product.ignore_reason = reason.strip()
        erp_product.mapped_by = user_id
        erp_product.mapped_at = now
        erp_product.updated_at = now

        await self._record_history(
            erp_product=erp_product,
            previous_product_id=previous_product_id,
            new_product_id=None,
            previous_status=previous_status,
            new_status=MappingStatus.IGNORED,
            reason=reason,
            changed_by=user_id,
        )
        await self.audit.log(
            ctx=audit_ctx,
            entity_type="erp_product",
            entity_id=erp_product.id,
            action="ignore",
            before_data=before,
            after_data=self._serialize(erp_product),
            metadata={"reason": reason},
        )
        return erp_product

    async def reopen_product(
        self,
        *,
        erp_product: ErpProduct,
        user_id: uuid.UUID,
        reason: str | None,
        audit_ctx: AuditContext,
    ) -> ErpProduct:
        if erp_product.mapping_status not in (MappingStatus.IGNORED, MappingStatus.CONFLICT):
            raise AppError(
                "Somente produtos ignorados ou em conflito podem ser reabertos.",
                status_code=400,
                code="INVALID_PRODUCT_MAPPING",
            )

        before = self._serialize(erp_product)
        previous_status = erp_product.mapping_status
        previous_product_id = erp_product.canonical_product_id
        now = datetime.now(UTC)

        erp_product.mapping_status = MappingStatus.PENDING
        erp_product.canonical_product_id = None
        erp_product.ignore_reason = None
        erp_product.mapped_by = None
        erp_product.mapped_at = None
        erp_product.updated_at = now

        await self._record_history(
            erp_product=erp_product,
            previous_product_id=previous_product_id,
            new_product_id=None,
            previous_status=previous_status,
            new_status=MappingStatus.PENDING,
            reason=reason,
            changed_by=user_id,
        )
        await self.audit.log(
            ctx=audit_ctx,
            entity_type="erp_product",
            entity_id=erp_product.id,
            action="reopen",
            before_data=before,
            after_data=self._serialize(erp_product),
            metadata={"reason": reason},
        )
        return erp_product

    def _serialize(self, erp_product: ErpProduct) -> dict:
        return {
            "id": str(erp_product.id),
            "organization_id": str(erp_product.organization_id),
            "station_id": str(erp_product.station_id),
            "erp_product_id": erp_product.erp_product_id,
            "erp_product_code": erp_product.erp_product_code,
            "erp_description": erp_product.erp_description,
            "erp_unit": erp_product.erp_unit,
            "erp_group_id": erp_product.erp_group_id,
            "erp_group_name": erp_product.erp_group_name,
            "erp_subgroup_id": erp_product.erp_subgroup_id,
            "erp_subgroup_name": erp_product.erp_subgroup_name,
            "canonical_product_id": (
                str(erp_product.canonical_product_id) if erp_product.canonical_product_id else None
            ),
            "mapping_status": erp_product.mapping_status,
            "mapping_source": erp_product.mapping_source,
            "ignore_reason": erp_product.ignore_reason,
            "mapped_by": str(erp_product.mapped_by) if erp_product.mapped_by else None,
            "mapped_at": erp_product.mapped_at.isoformat() if erp_product.mapped_at else None,
            "last_synced_at": (
                erp_product.last_synced_at.isoformat() if erp_product.last_synced_at else None
            ),
            "active": erp_product.active,
        }
