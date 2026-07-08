import uuid
from datetime import UTC, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.models.organization import Organization
from app.services.audit_service import AuditContext, AuditService
from app.utils.cnpj import normalize_cnpj, validate_cnpj


class OrganizationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.audit = AuditService(db)

    async def get_by_id(self, org_id: uuid.UUID) -> Organization | None:
        return await self.db.get(Organization, org_id)

    async def get_for_organization(self, organization_id: uuid.UUID) -> Organization:
        org = await self.get_by_id(organization_id)
        if org is None:
            raise AppError("Organização não encontrada.", status_code=404, code="NOT_FOUND")
        return org

    async def create(
        self,
        *,
        data: dict,
        audit_ctx: AuditContext,
    ) -> Organization:
        cnpj = normalize_cnpj(data["cnpj"])
        if not validate_cnpj(cnpj):
            raise AppError("CNPJ inválido.", status_code=400, code="INVALID_CNPJ")
        existing = await self.db.execute(select(Organization).where(Organization.cnpj == cnpj))
        if existing.scalar_one_or_none():
            raise AppError("Já existe um cadastro com este CNPJ.", status_code=409, code="CNPJ_ALREADY_EXISTS")

        org = Organization(
            name=data["name"],
            corporate_name=data["corporate_name"],
            cnpj=cnpj,
            timezone=data.get("timezone", "America/Cuiaba"),
            active=data.get("active", True),
        )
        self.db.add(org)
        await self.db.flush()
        await self.audit.log(
            ctx=audit_ctx,
            entity_type="organization",
            entity_id=org.id,
            action="create",
            after_data=self._serialize(org),
        )
        return org

    async def update(
        self,
        *,
        org: Organization,
        data: dict,
        audit_ctx: AuditContext,
    ) -> Organization:
        before = self._serialize(org)
        if "name" in data:
            org.name = data["name"]
        if "corporate_name" in data:
            org.corporate_name = data["corporate_name"]
        if "timezone" in data:
            org.timezone = data["timezone"]
        if "active" in data:
            org.active = data["active"]
        if "cnpj" in data:
            cnpj = normalize_cnpj(data["cnpj"])
            if not validate_cnpj(cnpj):
                raise AppError("CNPJ inválido.", status_code=400, code="INVALID_CNPJ")
            existing = await self.db.execute(
                select(Organization).where(Organization.cnpj == cnpj, Organization.id != org.id)
            )
            if existing.scalar_one_or_none():
                raise AppError(
                    "Já existe um cadastro com este CNPJ.",
                    status_code=409,
                    code="CNPJ_ALREADY_EXISTS",
                )
            org.cnpj = cnpj
        org.updated_at = datetime.now(UTC)
        await self.audit.log(
            ctx=audit_ctx,
            entity_type="organization",
            entity_id=org.id,
            action="update",
            before_data=before,
            after_data=self._serialize(org),
        )
        return org

    def _serialize(self, org: Organization) -> dict:
        return {
            "id": str(org.id),
            "name": org.name,
            "corporate_name": org.corporate_name,
            "cnpj": org.cnpj,
            "timezone": org.timezone,
            "active": org.active,
        }
