import uuid
from datetime import UTC, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.models.station import Station
from app.services.audit_service import AuditContext, AuditService
from app.services.auth_service import AuthenticatedUser
from app.utils.cnpj import normalize_cnpj, validate_cnpj


class StationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.audit = AuditService(db)

    async def list_stations(
        self,
        *,
        user: AuthenticatedUser,
        search: str | None = None,
        station_type: str | None = None,
        brand_type: str | None = None,
        active: bool | None = None,
        page: int = 1,
        page_size: int = 20,
        allowed_station_ids: list[uuid.UUID] | None = None,
    ) -> tuple[list[Station], int]:
        query = select(Station).where(Station.organization_id == user.organization_id)
        if not user.has_all_stations_access and allowed_station_ids is not None:
            if not allowed_station_ids:
                return [], 0
            query = query.where(Station.id.in_(allowed_station_ids))
        if search:
            term = f"%{search}%"
            query = query.where(
                or_(
                    Station.trade_name.ilike(term),
                    Station.corporate_name.ilike(term),
                    Station.cnpj.ilike(term),
                )
            )
        if station_type:
            query = query.where(Station.station_type == station_type)
        if brand_type:
            query = query.where(Station.brand_type == brand_type)
        if active is not None:
            query = query.where(Station.active.is_(active))

        count_q = select(func.count()).select_from(query.subquery())
        total = int((await self.db.execute(count_q)).scalar_one())

        query = query.order_by(Station.trade_name).offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def get_by_id(self, station_id: uuid.UUID, organization_id: uuid.UUID) -> Station:
        station = await self.db.get(Station, station_id)
        if station is None or station.organization_id != organization_id:
            raise AppError("Posto não encontrado.", status_code=404, code="NOT_FOUND")
        return station

    async def _ensure_single_headquarters(
        self, organization_id: uuid.UUID, exclude_id: uuid.UUID | None = None
    ) -> None:
        query = select(Station).where(
            Station.organization_id == organization_id,
            Station.station_type == "HEADQUARTERS",
            Station.active.is_(True),
        )
        if exclude_id:
            query = query.where(Station.id != exclude_id)
        result = await self.db.execute(query)
        if result.scalar_one_or_none():
            raise AppError(
                "Já existe uma matriz ativa nesta organização.",
                status_code=409,
                code="HEADQUARTERS_ALREADY_EXISTS",
            )

    def _validate_brand(self, brand_type: str, brand_name: str | None) -> None:
        if brand_type == "BRANDED" and not brand_name:
            raise AppError(
                "Nome da bandeira é obrigatório para postos bandeirados.",
                status_code=400,
                code="VALIDATION_ERROR",
            )

    async def create(self, *, data: dict, audit_ctx: AuditContext) -> Station:
        cnpj = normalize_cnpj(data["cnpj"])
        if not validate_cnpj(cnpj):
            raise AppError("CNPJ inválido.", status_code=400, code="INVALID_CNPJ")

        existing_cnpj = await self.db.execute(select(Station).where(Station.cnpj == cnpj))
        if existing_cnpj.scalar_one_or_none():
            raise AppError("Já existe um cadastro com este CNPJ.", status_code=409, code="CNPJ_ALREADY_EXISTS")

        org_id = uuid.UUID(str(data["organization_id"]))
        erp = data.get("erp_branch_id")
        if erp:
            dup = await self.db.execute(
                select(Station).where(Station.organization_id == org_id, Station.erp_branch_id == erp)
            )
            if dup.scalar_one_or_none():
                raise AppError(
                    "Código ERP já cadastrado nesta organização.",
                    status_code=409,
                    code="ERP_BRANCH_ALREADY_EXISTS",
                )

        anp = data.get("anp_code")
        if anp:
            dup_anp = await self.db.execute(select(Station).where(Station.anp_code == anp))
            if dup_anp.scalar_one_or_none():
                raise AppError("Código ANP já cadastrado.", status_code=409, code="ANP_ALREADY_EXISTS")

        station_type = data["station_type"]
        brand_type = data["brand_type"]
        brand_name = data.get("brand_name")
        self._validate_brand(brand_type, brand_name)

        if station_type == "HEADQUARTERS":
            await self._ensure_single_headquarters(org_id)

        station = Station(
            organization_id=org_id,
            station_type=station_type,
            erp_branch_id=erp,
            corporate_name=data["corporate_name"],
            trade_name=data["trade_name"],
            cnpj=cnpj,
            anp_code=anp,
            brand_type=brand_type,
            brand_name=brand_name,
            timezone=data.get("timezone", "America/Cuiaba"),
            active=data.get("active", True),
        )
        self.db.add(station)
        await self.db.flush()
        await self.audit.log(
            ctx=audit_ctx,
            entity_type="station",
            entity_id=station.id,
            action="create",
            after_data=self._serialize(station),
        )
        return station

    async def update(self, *, station: Station, data: dict, audit_ctx: AuditContext) -> Station:
        before = self._serialize(station)
        if "station_type" in data and data["station_type"] == "HEADQUARTERS":
            await self._ensure_single_headquarters(station.organization_id, exclude_id=station.id)
            station.station_type = "HEADQUARTERS"
        elif "station_type" in data:
            station.station_type = data["station_type"]

        for field in ("corporate_name", "trade_name", "erp_branch_id", "anp_code", "timezone", "active"):
            if field in data:
                setattr(station, field, data[field])

        if "cnpj" in data:
            cnpj = normalize_cnpj(data["cnpj"])
            if not validate_cnpj(cnpj):
                raise AppError("CNPJ inválido.", status_code=400, code="INVALID_CNPJ")
            dup = await self.db.execute(
                select(Station).where(Station.cnpj == cnpj, Station.id != station.id)
            )
            if dup.scalar_one_or_none():
                raise AppError("Já existe um cadastro com este CNPJ.", status_code=409, code="CNPJ_ALREADY_EXISTS")
            station.cnpj = cnpj

        if "brand_type" in data or "brand_name" in data:
            brand_type = data.get("brand_type", station.brand_type)
            brand_name = data.get("brand_name", station.brand_name)
            self._validate_brand(brand_type, brand_name)
            station.brand_type = brand_type
            station.brand_name = brand_name

        if "erp_branch_id" in data and data["erp_branch_id"]:
            dup = await self.db.execute(
                select(Station).where(
                    Station.organization_id == station.organization_id,
                    Station.erp_branch_id == data["erp_branch_id"],
                    Station.id != station.id,
                )
            )
            if dup.scalar_one_or_none():
                raise AppError(
                    "Código ERP já cadastrado nesta organização.",
                    status_code=409,
                    code="ERP_BRANCH_ALREADY_EXISTS",
                )

        station.updated_at = datetime.now(UTC)
        await self.audit.log(
            ctx=audit_ctx,
            entity_type="station",
            entity_id=station.id,
            action="update",
            before_data=before,
            after_data=self._serialize(station),
        )
        return station

    async def deactivate(self, *, station: Station, reason: str, audit_ctx: AuditContext) -> Station:
        if station.station_type == "HEADQUARTERS" and station.active:
            raise AppError(
                "Não é possível inativar a matriz sem definir outra matriz.",
                status_code=400,
                code="VALIDATION_ERROR",
            )
        before = self._serialize(station)
        station.active = False
        station.updated_at = datetime.now(UTC)
        await self.audit.log(
            ctx=audit_ctx,
            entity_type="station",
            entity_id=station.id,
            action="deactivate",
            before_data=before,
            after_data=self._serialize(station),
            metadata={"reason": reason},
        )
        return station

    async def reactivate(self, *, station: Station, audit_ctx: AuditContext) -> Station:
        if station.station_type == "HEADQUARTERS":
            await self._ensure_single_headquarters(station.organization_id, exclude_id=station.id)
        before = self._serialize(station)
        station.active = True
        station.updated_at = datetime.now(UTC)
        await self.audit.log(
            ctx=audit_ctx,
            entity_type="station",
            entity_id=station.id,
            action="reactivate",
            before_data=before,
            after_data=self._serialize(station),
        )
        return station

    def _serialize(self, station: Station) -> dict:
        return {
            "id": str(station.id),
            "organization_id": str(station.organization_id),
            "station_type": station.station_type,
            "erp_branch_id": station.erp_branch_id,
            "corporate_name": station.corporate_name,
            "trade_name": station.trade_name,
            "cnpj": station.cnpj,
            "anp_code": station.anp_code,
            "brand_type": station.brand_type,
            "brand_name": station.brand_name,
            "timezone": station.timezone,
            "active": station.active,
        }
