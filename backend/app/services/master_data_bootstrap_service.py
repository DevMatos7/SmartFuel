import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.seeds.master_data import seed_master_data_for_organization
from app.services.audit_service import AuditContext, AuditService
from app.services.organization_business_settings_service import OrganizationBusinessSettingsService


class MasterDataBootstrapService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.audit = AuditService(db)
        self.settings_service = OrganizationBusinessSettingsService(db)

    async def bootstrap_organization(
        self,
        *,
        organization_id: uuid.UUID,
        audit_ctx: AuditContext | None = None,
        user_id: uuid.UUID | None = None,
    ) -> dict[str, int | str]:
        seed_counts = await seed_master_data_for_organization(self.db, organization_id)
        await self.settings_service.ensure_defaults(organization_id, updated_by=user_id)

        if audit_ctx:
            await self.audit.log(
                ctx=audit_ctx,
                entity_type="organization",
                entity_id=organization_id,
                action="master_data_bootstrap",
                after_data={"seed_counts": seed_counts},
                metadata={"source": "bootstrap_service"},
            )

        return {
            **seed_counts,
            "business_settings": "ensured",
        }
