import uuid
from datetime import UTC, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.models.distribution_base import DistributionBase
from app.models.distributor import Distributor
from app.services.audit_service import AuditContext, AuditService
from app.services.distributor_service import DistributorService
from app.utils.text import normalize_name
from app.utils.uf import is_valid_uf


class DistributionBaseService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.audit = AuditService(db)
        self.distributor_service = DistributorService(db)

    async def list_bases(
        self,
        *,
        organization_id: uuid.UUID,
        distributor_id: uuid.UUID | None = None,
        search: str | None = None,
        state: str | None = None,
        active: bool | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[DistributionBase], int]:
        query = select(DistributionBase).where(DistributionBase.organization_id == organization_id)
        if distributor_id:
            query = query.where(DistributionBase.distributor_id == distributor_id)
        if state:
            query = query.where(DistributionBase.state == state.upper())
        if active is not None:
            query = query.where(DistributionBase.active.is_(active))
        if search:
            term = f"%{search}%"
            query = query.where(
                or_(
                    DistributionBase.name.ilike(term),
                    DistributionBase.city.ilike(term),
                    DistributionBase.external_code.ilike(term),
                )
            )

        count_q = select(func.count()).select_from(query.subquery())
        total = int((await self.db.execute(count_q)).scalar_one())

        query = (
            query.order_by(DistributionBase.state, DistributionBase.name)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def get_by_id(self, base_id: uuid.UUID, organization_id: uuid.UUID) -> DistributionBase:
        base = await self.db.get(DistributionBase, base_id)
        if base is None or base.organization_id != organization_id:
            raise AppError("Base de distribuição não encontrada.", status_code=404, code="NOT_FOUND")
        return base

    async def _ensure_distributor(
        self, distributor_id: uuid.UUID, organization_id: uuid.UUID
    ) -> Distributor:
        return await self.distributor_service.get_by_id(distributor_id, organization_id)

    async def _ensure_unique_base(
        self,
        distributor_id: uuid.UUID,
        state: str,
        normalized_name: str,
        exclude_id: uuid.UUID | None = None,
    ) -> None:
        query = select(DistributionBase).where(
            DistributionBase.distributor_id == distributor_id,
            DistributionBase.state == state,
            DistributionBase.normalized_name == normalized_name,
            DistributionBase.active.is_(True),
        )
        if exclude_id:
            query = query.where(DistributionBase.id != exclude_id)
        existing = await self.db.execute(query)
        if existing.scalar_one_or_none():
            raise AppError(
                "Já existe uma base com este nome para a distribuidora.",
                status_code=409,
                code="DISTRIBUTION_BASE_ALREADY_EXISTS",
            )

    def _validate_state(self, state: str) -> str:
        uf = state.strip().upper()
        if not is_valid_uf(uf):
            raise AppError("Estado inválido.", status_code=400, code="VALIDATION_ERROR")
        return uf

    async def create(
        self, *, organization_id: uuid.UUID, data: dict, audit_ctx: AuditContext
    ) -> DistributionBase:
        distributor = await self._ensure_distributor(data["distributor_id"], organization_id)
        name = str(data["name"]).strip()
        city = str(data["city"]).strip()
        if not name or not city:
            raise AppError(
                "Nome e cidade da base são obrigatórios.",
                status_code=400,
                code="VALIDATION_ERROR",
            )

        state = self._validate_state(data["state"])
        normalized = normalize_name(name)
        await self._ensure_unique_base(distributor.id, state, normalized)

        base = DistributionBase(
            organization_id=organization_id,
            distributor_id=distributor.id,
            external_code=data.get("external_code"),
            name=name,
            normalized_name=normalized,
            city=city,
            state=state,
            notes=data.get("notes"),
            active=data.get("active", True),
        )
        self.db.add(base)
        await self.db.flush()
        await self.audit.log(
            ctx=audit_ctx,
            entity_type="distribution_base",
            entity_id=base.id,
            action="create",
            after_data=self._serialize(base),
        )
        return base

    async def update(
        self, *, base: DistributionBase, data: dict, audit_ctx: AuditContext
    ) -> DistributionBase:
        before = self._serialize(base)

        if "distributor_id" in data:
            distributor = await self._ensure_distributor(data["distributor_id"], base.organization_id)
            base.distributor_id = distributor.id

        name = data.get("name", base.name)
        state = data.get("state", base.state)
        if "name" in data:
            name = str(name).strip()
            if not name:
                raise AppError("Nome da base é obrigatório.", status_code=400, code="VALIDATION_ERROR")
            base.name = name
            base.normalized_name = normalize_name(name)
        if "state" in data:
            state = self._validate_state(state)
            base.state = state
        if "name" in data or "state" in data or "distributor_id" in data:
            await self._ensure_unique_base(
                base.distributor_id,
                base.state,
                base.normalized_name,
                exclude_id=base.id,
            )

        if "city" in data:
            city = str(data["city"]).strip()
            if not city:
                raise AppError("Cidade é obrigatória.", status_code=400, code="VALIDATION_ERROR")
            base.city = city

        for field in ("external_code", "notes", "active"):
            if field in data:
                setattr(base, field, data[field])

        base.updated_at = datetime.now(UTC)
        await self.audit.log(
            ctx=audit_ctx,
            entity_type="distribution_base",
            entity_id=base.id,
            action="update",
            before_data=before,
            after_data=self._serialize(base),
        )
        return base

    async def deactivate(
        self, *, base: DistributionBase, reason: str, audit_ctx: AuditContext
    ) -> DistributionBase:
        before = self._serialize(base)
        base.active = False
        base.updated_at = datetime.now(UTC)
        await self.audit.log(
            ctx=audit_ctx,
            entity_type="distribution_base",
            entity_id=base.id,
            action="deactivate",
            before_data=before,
            after_data=self._serialize(base),
            metadata={"reason": reason},
        )
        return base

    async def reactivate(self, *, base: DistributionBase, audit_ctx: AuditContext) -> DistributionBase:
        await self._ensure_unique_base(
            base.distributor_id, base.state, base.normalized_name, exclude_id=base.id
        )
        before = self._serialize(base)
        base.active = True
        base.updated_at = datetime.now(UTC)
        await self.audit.log(
            ctx=audit_ctx,
            entity_type="distribution_base",
            entity_id=base.id,
            action="reactivate",
            before_data=before,
            after_data=self._serialize(base),
        )
        return base

    def _serialize(self, base: DistributionBase) -> dict:
        return {
            "id": str(base.id),
            "organization_id": str(base.organization_id),
            "distributor_id": str(base.distributor_id),
            "external_code": base.external_code,
            "name": base.name,
            "normalized_name": base.normalized_name,
            "city": base.city,
            "state": base.state,
            "notes": base.notes,
            "active": base.active,
        }
