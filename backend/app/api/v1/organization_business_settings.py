import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_audit_context, get_current_active_user
from app.core.exceptions import AppError
from app.core.permissions import Permission
from app.models.organization_business_settings import OrganizationBusinessSettings
from app.schemas.organization_settings import (
    OrganizationBusinessSettingsResponse,
    OrganizationBusinessSettingsUpdate,
)
from app.services.audit_service import AuditContext
from app.services.auth_service import AuthenticatedUser
from app.services.organization_business_settings_service import OrganizationBusinessSettingsService

router = APIRouter(prefix="/organization-business-settings", tags=["organization-settings"])


def _ensure_read(user: AuthenticatedUser) -> None:
    if Permission.ORGANIZATIONS_READ.value not in user.permissions:
        raise AppError(
            "Você não possui permissão para executar esta ação.",
            status_code=403,
            code="FORBIDDEN",
        )


def _ensure_write(user: AuthenticatedUser) -> None:
    if Permission.ORGANIZATIONS_WRITE.value not in user.permissions:
        raise AppError(
            "Você não possui permissão para executar esta ação.",
            status_code=403,
            code="FORBIDDEN",
        )


@router.get("", response_model=OrganizationBusinessSettingsResponse)
async def get_organization_business_settings(
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> OrganizationBusinessSettings:
    _ensure_read(user)
    service = OrganizationBusinessSettingsService(db)
    return await service.get_for_organization(user.organization_id)


@router.patch("", response_model=OrganizationBusinessSettingsResponse)
async def update_organization_business_settings(
    payload: OrganizationBusinessSettingsUpdate,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    audit_ctx: AuditContext = Depends(get_audit_context),
) -> OrganizationBusinessSettings:
    _ensure_write(user)
    service = OrganizationBusinessSettingsService(db)
    updated = await service.update(
        organization_id=user.organization_id,
        data=payload.model_dump(exclude_unset=True),
        user_id=user.id,
        audit_ctx=audit_ctx,
    )
    await db.commit()
    return updated
