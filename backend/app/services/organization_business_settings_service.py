import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AppError
from app.models.organization_business_settings import OrganizationBusinessSettings
from app.services.audit_service import AuditContext, AuditService


class OrganizationBusinessSettingsService:
    DEFAULT_MINIMUM = Decimal("5000.000")

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.audit = AuditService(db)

    def _serialize(self, row: OrganizationBusinessSettings) -> dict:
        return {
            "organization_id": str(row.organization_id),
            "default_supplier_allowed": row.default_supplier_allowed,
            "default_minimum_volume_liters": str(row.default_minimum_volume_liters),
            "updated_by": str(row.updated_by) if row.updated_by else None,
        }

    async def get_for_organization(self, organization_id: uuid.UUID) -> OrganizationBusinessSettings:
        result = await self.db.execute(
            select(OrganizationBusinessSettings).where(
                OrganizationBusinessSettings.organization_id == organization_id
            )
        )
        settings_row = result.scalar_one_or_none()
        if settings_row is None:
            settings_row = await self.ensure_defaults(organization_id)
        return settings_row

    async def ensure_defaults(
        self, organization_id: uuid.UUID, *, updated_by: uuid.UUID | None = None
    ) -> OrganizationBusinessSettings:
        result = await self.db.execute(
            select(OrganizationBusinessSettings).where(
                OrganizationBusinessSettings.organization_id == organization_id
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            return existing

        bootstrap_allowed = settings.default_supplier_allowed
        bootstrap_minimum = Decimal(settings.default_minimum_volume_liters)

        row = OrganizationBusinessSettings(
            organization_id=organization_id,
            default_supplier_allowed=bootstrap_allowed,
            default_minimum_volume_liters=bootstrap_minimum,
            updated_by=updated_by,
        )
        self.db.add(row)
        await self.db.flush()
        return row

    async def update(
        self,
        *,
        organization_id: uuid.UUID,
        data: dict,
        user_id: uuid.UUID,
        audit_ctx: AuditContext,
    ) -> OrganizationBusinessSettings:
        row = await self.get_for_organization(organization_id)
        before = self._serialize(row)

        if "default_supplier_allowed" in data and data["default_supplier_allowed"] is not None:
            row.default_supplier_allowed = data["default_supplier_allowed"]

        if "default_minimum_volume_liters" in data and data["default_minimum_volume_liters"] is not None:
            minimum = Decimal(str(data["default_minimum_volume_liters"]))
            if minimum <= 0:
                raise AppError(
                    "O volume mínimo deve ser maior que zero.",
                    status_code=400,
                    code="INVALID_MINIMUM_VOLUME",
                )
            row.default_minimum_volume_liters = minimum

        row.updated_by = user_id
        await self.db.flush()

        await self.audit.log(
            ctx=audit_ctx,
            entity_type="organization_business_settings",
            entity_id=row.id,
            action="update",
            before_data=before,
            after_data=self._serialize(row),
        )
        return row
