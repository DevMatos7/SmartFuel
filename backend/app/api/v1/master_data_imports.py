import uuid

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_audit_context, get_current_active_user
from app.core.exceptions import AppError
from app.core.master_data_enums import ImportType
from app.core.permissions import Permission
from app.models.import_job import MasterDataImportJob
from app.schemas.master_data import (
    MasterDataImportJobDetailResponse,
    MasterDataImportJobListResponse,
    MasterDataImportJobResponse,
    MasterDataImportRowResponse,
)
from app.services.audit_service import AuditContext
from app.services.auth_service import AuthService, AuthenticatedUser
from app.services.master_data_import_service import MasterDataImportService

router = APIRouter(prefix="/master-data-imports", tags=["master-data-imports"])


def _ensure_read(user: AuthenticatedUser) -> None:
    if Permission.MASTER_DATA_IMPORTS_READ.value not in user.permissions:
        raise AppError(
            "Você não possui permissão para executar esta ação.",
            status_code=403,
            code="FORBIDDEN",
        )


def _ensure_execute(user: AuthenticatedUser) -> None:
    if Permission.MASTER_DATA_IMPORTS_EXECUTE.value not in user.permissions:
        raise AppError(
            "Você não possui permissão para executar esta ação.",
            status_code=403,
            code="FORBIDDEN",
        )


def _job_to_detail(job: MasterDataImportJob) -> MasterDataImportJobDetailResponse:
    return MasterDataImportJobDetailResponse(
        id=job.id,
        organization_id=job.organization_id,
        station_id=job.station_id,
        import_type=job.import_type,
        source_file_name=job.source_file_name,
        source_file_hash=job.source_file_hash,
        status=job.status,
        records_total=job.records_total,
        records_valid=job.records_valid,
        records_inserted=job.records_inserted,
        records_updated=job.records_updated,
        records_unchanged=job.records_unchanged,
        records_failed=job.records_failed,
        error_summary=job.error_summary,
        created_by=job.created_by,
        created_at=job.created_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
        rows=[MasterDataImportRowResponse.model_validate(r) for r in job.rows],
    )


async def _ensure_job_station_access(
    auth: AuthService, user: AuthenticatedUser, job: MasterDataImportJob
) -> None:
    if job.station_id is not None:
        await auth.ensure_station_access(user, job.station_id)


@router.get("", response_model=MasterDataImportJobListResponse)
async def list_import_jobs(
    import_type: str | None = None,
    status: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> MasterDataImportJobListResponse:
    _ensure_read(user)
    service = MasterDataImportService(db)
    items, total = await service.list_jobs(
        organization_id=user.organization_id,
        import_type=import_type,
        status=status,
        page=page,
        page_size=page_size,
    )
    return MasterDataImportJobListResponse(
        items=[MasterDataImportJobResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{job_id}", response_model=MasterDataImportJobDetailResponse)
async def get_import_job(
    job_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> MasterDataImportJobDetailResponse:
    _ensure_read(user)
    auth = AuthService(db)
    service = MasterDataImportService(db)
    job = await service.get_job(job_id, user.organization_id)
    await _ensure_job_station_access(auth, user, job)
    return _job_to_detail(job)


@router.post("/erp-products", response_model=MasterDataImportJobDetailResponse, status_code=201)
async def upload_erp_products_import(
    station_id: uuid.UUID = Form(...),
    file: UploadFile = File(...),
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    audit_ctx: AuditContext = Depends(get_audit_context),
) -> MasterDataImportJobDetailResponse:
    _ensure_execute(user)
    if Permission.ERP_PRODUCTS_IMPORT.value not in user.permissions:
        raise AppError(
            "Você não possui permissão para executar esta ação.",
            status_code=403,
            code="FORBIDDEN",
        )
    auth = AuthService(db)
    await auth.ensure_station_access(user, station_id)
    content = await file.read()
    service = MasterDataImportService(db)
    try:
        job = await service.upload_and_validate(
            organization_id=user.organization_id,
            station_id=station_id,
            import_type=ImportType.ERP_PRODUCTS,
            file_name=file.filename or "upload.csv",
            content=content,
            created_by=user.id,
            audit_ctx=audit_ctx,
        )
        await db.commit()
        job = await service.get_job(job.id, user.organization_id)
        return _job_to_detail(job)
    except AppError:
        await db.commit()
        raise


@router.post("/erp-suppliers", response_model=MasterDataImportJobDetailResponse, status_code=201)
async def upload_erp_suppliers_import(
    station_id: uuid.UUID = Form(...),
    file: UploadFile = File(...),
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    audit_ctx: AuditContext = Depends(get_audit_context),
) -> MasterDataImportJobDetailResponse:
    _ensure_execute(user)
    auth = AuthService(db)
    await auth.ensure_station_access(user, station_id)
    content = await file.read()
    service = MasterDataImportService(db)
    try:
        job = await service.upload_and_validate(
            organization_id=user.organization_id,
            station_id=station_id,
            import_type=ImportType.ERP_SUPPLIERS,
            file_name=file.filename or "upload.csv",
            content=content,
            created_by=user.id,
            audit_ctx=audit_ctx,
        )
        await db.commit()
        job = await service.get_job(job.id, user.organization_id)
        return _job_to_detail(job)
    except AppError:
        await db.commit()
        raise


@router.post("/{job_id}/confirm", response_model=MasterDataImportJobResponse)
async def confirm_import_job(
    job_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    audit_ctx: AuditContext = Depends(get_audit_context),
) -> MasterDataImportJob:
    _ensure_execute(user)
    auth = AuthService(db)
    service = MasterDataImportService(db)
    job = await service.get_job(job_id, user.organization_id)
    await _ensure_job_station_access(auth, user, job)
    updated = await service.confirm(job=job, audit_ctx=audit_ctx)
    await db.commit()
    return updated


@router.post("/{job_id}/cancel", response_model=MasterDataImportJobResponse)
async def cancel_import_job(
    job_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    audit_ctx: AuditContext = Depends(get_audit_context),
) -> MasterDataImportJob:
    _ensure_execute(user)
    auth = AuthService(db)
    service = MasterDataImportService(db)
    job = await service.get_job(job_id, user.organization_id)
    await _ensure_job_station_access(auth, user, job)
    updated = await service.cancel(job=job, audit_ctx=audit_ctx)
    await db.commit()
    return updated
