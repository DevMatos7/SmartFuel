import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_audit_context, get_current_active_user
from app.core.exceptions import AppError
from app.core.permissions import Permission
from app.models.station import Station
from app.schemas.station import DeactivateRequest, StationCreate, StationListResponse, StationResponse, StationUpdate
from app.services.audit_service import AuditContext
from app.services.auth_service import AuthService, AuthenticatedUser
from app.services.station_service import StationService

router = APIRouter(prefix="/stations", tags=["stations"])


def _ensure_read(user: AuthenticatedUser) -> None:
    if Permission.STATIONS_READ.value not in user.permissions:
        raise AppError(
            "Você não possui permissão para executar esta ação.",
            status_code=403,
            code="FORBIDDEN",
        )


def _ensure_write(user: AuthenticatedUser) -> None:
    if Permission.STATIONS_WRITE.value not in user.permissions:
        raise AppError(
            "Você não possui permissão para executar esta ação.",
            status_code=403,
            code="FORBIDDEN",
        )


@router.get("", response_model=StationListResponse)
async def list_stations(
    search: str | None = None,
    station_type: str | None = None,
    brand_type: str | None = None,
    active: bool | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> StationListResponse:
    _ensure_read(user)
    auth = AuthService(db)
    allowed = None if user.has_all_stations_access else [s.id for s in await auth.allowed_stations(user)]
    service = StationService(db)
    items, total = await service.list_stations(
        user=user,
        search=search,
        station_type=station_type,
        brand_type=brand_type,
        active=active,
        page=page,
        page_size=page_size,
        allowed_station_ids=allowed,
    )
    return StationListResponse(
        items=[StationResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{station_id}", response_model=StationResponse)
async def get_station(
    station_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Station:
    _ensure_read(user)
    auth = AuthService(db)
    await auth.ensure_station_access(user, station_id)
    service = StationService(db)
    return await service.get_by_id(station_id, user.organization_id)


@router.post("", response_model=StationResponse, status_code=201)
async def create_station(
    payload: StationCreate,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    audit_ctx: AuditContext = Depends(get_audit_context),
) -> Station:
    _ensure_write(user)
    if payload.organization_id != user.organization_id:
        raise AppError(
            "Você não possui permissão para executar esta ação.",
            status_code=403,
            code="FORBIDDEN",
        )
    service = StationService(db)
    station = await service.create(data=payload.model_dump(), audit_ctx=audit_ctx)
    await db.commit()
    return station


@router.patch("/{station_id}", response_model=StationResponse)
async def update_station(
    station_id: uuid.UUID,
    payload: StationUpdate,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    audit_ctx: AuditContext = Depends(get_audit_context),
) -> Station:
    _ensure_write(user)
    auth = AuthService(db)
    await auth.ensure_station_access(user, station_id)
    service = StationService(db)
    station = await service.get_by_id(station_id, user.organization_id)
    updated = await service.update(
        station=station,
        data={k: v for k, v in payload.model_dump().items() if v is not None},
        audit_ctx=audit_ctx,
    )
    await db.commit()
    return updated


@router.post("/{station_id}/deactivate", response_model=StationResponse)
async def deactivate_station(
    station_id: uuid.UUID,
    payload: DeactivateRequest,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    audit_ctx: AuditContext = Depends(get_audit_context),
) -> Station:
    _ensure_write(user)
    auth = AuthService(db)
    await auth.ensure_station_access(user, station_id)
    service = StationService(db)
    station = await service.get_by_id(station_id, user.organization_id)
    updated = await service.deactivate(station=station, reason=payload.reason, audit_ctx=audit_ctx)
    await db.commit()
    return updated


@router.post("/{station_id}/reactivate", response_model=StationResponse)
async def reactivate_station(
    station_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    audit_ctx: AuditContext = Depends(get_audit_context),
) -> Station:
    _ensure_write(user)
    auth = AuthService(db)
    await auth.ensure_station_access(user, station_id)
    service = StationService(db)
    station = await service.get_by_id(station_id, user.organization_id)
    updated = await service.reactivate(station=station, audit_ctx=audit_ctx)
    await db.commit()
    return updated
