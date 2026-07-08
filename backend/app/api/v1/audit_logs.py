import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.core.exceptions import AppError
from app.core.permissions import Permission
from app.schemas.audit import AuditLogListResponse, AuditLogResponse
from app.services.audit_service import AuditService
from app.services.auth_service import AuthenticatedUser

router = APIRouter(prefix="/audit-logs", tags=["audit"])


@router.get("", response_model=AuditLogListResponse)
async def list_audit_logs(
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    action: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> AuditLogListResponse:
    if Permission.AUDIT_READ.value not in user.permissions:
        raise AppError(
            "Você não possui permissão para executar esta ação.",
            status_code=403,
            code="FORBIDDEN",
        )
    service = AuditService(db)
    items, total = await service.list_logs(
        organization_id=user.organization_id,
        entity_type=entity_type,
        entity_id=entity_id,
        user_id=user_id,
        action=action,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )
    return AuditLogListResponse(
        items=[AuditLogResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )
