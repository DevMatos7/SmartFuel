import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_audit_context, get_current_active_user, get_current_user
from app.core.exceptions import AppError
from app.core.permissions import Permission
from app.models.organization import Organization
from app.schemas.organization import OrganizationCreate, OrganizationResponse, OrganizationUpdate
from app.services.audit_service import AuditContext
from app.services.auth_service import AuthenticatedUser
from app.services.organization_service import OrganizationService

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.get("", response_model=OrganizationResponse)
async def get_organization(
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Organization:
    if Permission.ORGANIZATIONS_READ.value not in user.permissions:
        raise AppError(
            "Você não possui permissão para executar esta ação.",
            status_code=403,
            code="FORBIDDEN",
        )
    service = OrganizationService(db)
    return await service.get_for_organization(user.organization_id)


@router.get("/{organization_id}", response_model=OrganizationResponse)
async def get_organization_by_id(
    organization_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Organization:
    if user.organization_id != organization_id:
        raise AppError(
            "Você não possui permissão para executar esta ação.",
            status_code=403,
            code="FORBIDDEN",
        )
    if Permission.ORGANIZATIONS_READ.value not in user.permissions:
        raise AppError(
            "Você não possui permissão para executar esta ação.",
            status_code=403,
            code="FORBIDDEN",
        )
    service = OrganizationService(db)
    return await service.get_for_organization(organization_id)


@router.post("", response_model=OrganizationResponse, status_code=201)
async def create_organization(
    payload: OrganizationCreate,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    audit_ctx: AuditContext = Depends(get_audit_context),
) -> Organization:
    if Permission.ORGANIZATIONS_WRITE.value not in user.permissions:
        raise AppError(
            "Você não possui permissão para executar esta ação.",
            status_code=403,
            code="FORBIDDEN",
        )
    existing = await db.execute(select(Organization))
    if existing.scalars().first():
        raise AppError("Organização já cadastrada.", status_code=409, code="ALREADY_EXISTS")
    service = OrganizationService(db)
    org = await service.create(data=payload.model_dump(), audit_ctx=audit_ctx)
    await db.commit()
    return org


@router.patch("/{organization_id}", response_model=OrganizationResponse)
async def update_organization(
    organization_id: uuid.UUID,
    payload: OrganizationUpdate,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    audit_ctx: AuditContext = Depends(get_audit_context),
) -> Organization:
    if user.organization_id != organization_id:
        raise AppError(
            "Você não possui permissão para executar esta ação.",
            status_code=403,
            code="FORBIDDEN",
        )
    if Permission.ORGANIZATIONS_WRITE.value not in user.permissions:
        raise AppError(
            "Você não possui permissão para executar esta ação.",
            status_code=403,
            code="FORBIDDEN",
        )
    service = OrganizationService(db)
    org = await service.get_for_organization(organization_id)
    if payload.active is False:
        from app.services.auth_service import AuthService

        auth = AuthService(db)
        if await auth.count_active_admins(organization_id) <= 1 and "ADMIN" in user.role_codes:
            raise AppError(
                "A operação não pode remover o último administrador ativo.",
                status_code=409,
                code="LAST_ADMIN_PROTECTION",
            )
    updated = await service.update(
        org=org,
        data={k: v for k, v in payload.model_dump().items() if v is not None},
        audit_ctx=audit_ctx,
    )
    await db.commit()
    return updated
