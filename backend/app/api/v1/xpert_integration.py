import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_audit_context, get_current_active_user
from app.core.exceptions import AppError
from app.core.permissions import Permission
from app.core.xpert_sync_enums import ErpDatasetCode, ErpStagingStatus, ErpSyncTrigger
from app.models.erp_integration import ErpDataset, ErpStagingRecord, ErpSyncCheckpoint, ErpSyncError, ErpSyncRun
from app.models.station import Station
from app.schemas.xpert_integration import (
    XpertCheckpointReset,
    XpertCheckpointResponse,
    XpertConnectionTestResponse,
    XpertDatasetResponse,
    XpertDatasetUpdate,
    XpertIntegrationSummary,
    XpertSourceCreate,
    XpertSourceResponse,
    XpertSourceUpdate,
    XpertStagingRecordResponse,
    XpertSupplierDocumentDiagnosticsResponse,
    XpertSyncErrorResponse,
    XpertSyncRunCreate,
    XpertSyncRunCreateResponse,
    XpertSyncRunListResponse,
    XpertSyncRunResponse,
    XpertWorkerStatusResponse,
)
from app.services.xpert_worker_service import XpertWorkerService
from app.services.audit_service import AuditContext
from app.services.auth_service import AuthenticatedUser
from app.services.xpert_checkpoint_service import XpertCheckpointService
from app.services.xpert_source_service import XpertSourceService
from app.services.xpert_sync_service import XpertSyncService
from app.utils.brazilian_document import DocumentDiagnostic, SupplierDocumentType, classify_supplier_document

router = APIRouter(prefix="/integrations/xpert", tags=["xpert-integration"])


def _ensure(user: AuthenticatedUser, permission: Permission) -> None:
    if permission.value not in user.permissions:
        raise AppError("Você não possui permissão para executar esta ação.", status_code=403, code="FORBIDDEN")


@router.get("", response_model=XpertIntegrationSummary)
async def get_integration_summary(
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> XpertIntegrationSummary:
    _ensure(user, Permission.ERP_INTEGRATION_READ)
    service = XpertSourceService(db)
    summary = await service.get_summary(user.organization_id)
    return XpertIntegrationSummary(**summary)


@router.get("/worker-status", response_model=XpertWorkerStatusResponse)
async def get_worker_status(
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> XpertWorkerStatusResponse:
    _ensure(user, Permission.ERP_INTEGRATION_READ)
    from datetime import timedelta

    from app.core.config import settings as app_settings
    from app.integrations.xpert.odbc_health import driver_available

    worker = XpertWorkerService(db)
    row = await worker.latest_worker_status()
    odbc_ok, _ = driver_available()
    if row is None:
        return XpertWorkerStatusResponse(odbc_available=odbc_ok, healthy=False)
    healthy = row.last_heartbeat_at >= datetime.now(UTC) - timedelta(
        seconds=app_settings.xpert_worker_heartbeat_timeout_seconds
    )
    return XpertWorkerStatusResponse(
        worker_id=row.worker_id,
        last_heartbeat_at=row.last_heartbeat_at,
        odbc_available=odbc_ok and row.odbc_available,
        driver_name=row.driver_name,
        healthy=healthy and odbc_ok,
        last_error=row.last_error,
    )


@router.get("/sources", response_model=list[XpertSourceResponse])
async def list_sources(
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> list[XpertSourceResponse]:
    _ensure(user, Permission.ERP_INTEGRATION_READ)
    service = XpertSourceService(db)
    sources = await service.list_sources(user.organization_id)
    return [XpertSourceResponse.model_validate(s) for s in sources]


@router.post("/sources", response_model=XpertSourceResponse, status_code=status.HTTP_201_CREATED)
async def create_source(
    payload: XpertSourceCreate,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    audit_ctx: AuditContext = Depends(get_audit_context),
) -> XpertSourceResponse:
    _ensure(user, Permission.ERP_INTEGRATION_MANAGE)
    service = XpertSourceService(db)
    source = await service.create_source(
        organization_id=user.organization_id,
        user_id=user.id,
        data=payload.model_dump(),
        audit_ctx=audit_ctx,
    )
    await db.commit()
    await db.refresh(source)
    return XpertSourceResponse.model_validate(source)


@router.get("/sources/{source_id}", response_model=XpertSourceResponse)
async def get_source(
    source_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> XpertSourceResponse:
    _ensure(user, Permission.ERP_INTEGRATION_READ)
    service = XpertSourceService(db)
    source = await service.get_source(user.organization_id, source_id)
    return XpertSourceResponse.model_validate(source)


@router.patch("/sources/{source_id}", response_model=XpertSourceResponse)
async def update_source(
    source_id: uuid.UUID,
    payload: XpertSourceUpdate,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    audit_ctx: AuditContext = Depends(get_audit_context),
) -> XpertSourceResponse:
    _ensure(user, Permission.ERP_INTEGRATION_MANAGE)
    service = XpertSourceService(db)
    source = await service.get_source(user.organization_id, source_id)
    source = await service.update_source(
        source=source,
        data=payload.model_dump(exclude_unset=True),
        user_id=user.id,
        audit_ctx=audit_ctx,
    )
    await db.commit()
    await db.refresh(source)
    return XpertSourceResponse.model_validate(source)


@router.post("/sources/{source_id}/test-connection", response_model=XpertConnectionTestResponse)
async def test_connection(
    source_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    audit_ctx: AuditContext = Depends(get_audit_context),
) -> XpertConnectionTestResponse:
    _ensure(user, Permission.ERP_INTEGRATION_TEST)
    service = XpertSourceService(db)
    source = await service.get_source(user.organization_id, source_id)
    result = await service.test_connection(source=source, audit_ctx=audit_ctx)
    await db.commit()
    return XpertConnectionTestResponse(**result)


@router.get("/datasets", response_model=list[XpertDatasetResponse])
async def list_datasets(
    source_id: uuid.UUID | None = None,
    enabled: bool | None = None,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> list[XpertDatasetResponse]:
    _ensure(user, Permission.ERP_INTEGRATION_READ)
    from app.models.erp_integration import ErpSource

    query = (
        select(ErpDataset)
        .join(ErpSource, ErpDataset.erp_source_id == ErpSource.id)
        .where(ErpSource.organization_id == user.organization_id)
    )
    if source_id:
        query = query.where(ErpDataset.erp_source_id == source_id)
    if enabled is not None:
        query = query.where(ErpDataset.enabled == enabled)
    result = await db.execute(query.order_by(ErpDataset.code))
    return [XpertDatasetResponse.model_validate(d) for d in result.scalars().all()]


@router.patch("/datasets/{dataset_id}", response_model=XpertDatasetResponse)
async def update_dataset(
    dataset_id: uuid.UUID,
    payload: XpertDatasetUpdate,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    audit_ctx: AuditContext = Depends(get_audit_context),
) -> XpertDatasetResponse:
    _ensure(user, Permission.ERP_INTEGRATION_MANAGE)
    result = await db.execute(
        select(ErpDataset).join(ErpDataset.source).where(
            ErpDataset.id == dataset_id,
            ErpDataset.source.has(organization_id=user.organization_id),
        )
    )
    dataset = result.scalar_one_or_none()
    if dataset is None:
        raise AppError("Dataset não encontrado.", status_code=404, code="XPERT_DATASET_NOT_FOUND")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(dataset, field, value)
    dataset.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(dataset)
    return XpertDatasetResponse.model_validate(dataset)


@router.post("/datasets/{dataset_id}/validate-contract")
async def validate_contract(
    dataset_id: uuid.UUID,
    station_id: uuid.UUID | None = None,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    audit_ctx: AuditContext = Depends(get_audit_context),
) -> dict:
    _ensure(user, Permission.ERP_INTEGRATION_TEST)
    result = await db.execute(
        select(ErpDataset).join(ErpDataset.source).where(
            ErpDataset.id == dataset_id,
            ErpDataset.source.has(organization_id=user.organization_id),
        )
    )
    dataset = result.scalar_one_or_none()
    if dataset is None:
        raise AppError("Dataset não encontrado.", status_code=404, code="XPERT_DATASET_NOT_FOUND")
    source_service = XpertSourceService(db)
    source = await source_service.get_source(user.organization_id, dataset.erp_source_id)
    station = None
    if station_id:
        station = await db.get(Station, station_id)
    result = await source_service.validate_dataset_contract(
        source=source, dataset=dataset, audit_ctx=audit_ctx, station=station
    )
    await db.commit()
    return result


@router.post("/sync-runs", response_model=XpertSyncRunCreateResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_sync_runs(
    payload: XpertSyncRunCreate,
    user: AuthenticatedUser = Depends(get_current_active_user),
    audit_ctx: AuditContext = Depends(get_audit_context),
    db: AsyncSession = Depends(get_db),
) -> XpertSyncRunCreateResponse:
    _ensure(user, Permission.ERP_SYNC_RUN)
    service = XpertSourceService(db)
    source = await service.get_source(user.organization_id, payload.source_id)
    if source.security_status == "UNSAFE" and "ADMIN" not in user.role_codes:
        raise AppError(
            "Somente ADMIN pode sincronizar fonte UNSAFE.",
            status_code=403,
            code="UNSAFE_SOURCE_ADMIN_ONLY",
        )
    runs = await service.enqueue_sync_runs(
        organization_id=user.organization_id,
        source=source,
        dataset_codes=payload.dataset_codes,
        station_ids=payload.station_ids,
        sync_mode=payload.sync_mode,
        trigger_type=ErpSyncTrigger.MANUAL,
        requested_by=user.id,
        unsafe_homologation_acknowledged=payload.unsafe_homologation_acknowledged,
        audit_ctx=audit_ctx,
        history_start_date=payload.history_start_date,
        history_end_date=payload.history_end_date,
    )
    await db.commit()
    for run in runs:
        await db.refresh(run)
    return XpertSyncRunCreateResponse(
        runs=[XpertSyncRunResponse.model_validate(r) for r in runs]
    )


@router.get("/sync-runs", response_model=XpertSyncRunListResponse)
async def list_sync_runs(
    source_id: uuid.UUID | None = None,
    dataset_id: uuid.UUID | None = None,
    station_id: uuid.UUID | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    sync_mode: str | None = None,
    trigger_type: str | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    sort_by: str = Query(default="created_at"),
    sort_dir: str = Query(default="desc", pattern="^(asc|desc)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> XpertSyncRunListResponse:
    _ensure(user, Permission.ERP_SYNC_READ)
    query = select(ErpSyncRun).where(ErpSyncRun.organization_id == user.organization_id)
    if source_id:
        query = query.where(ErpSyncRun.erp_source_id == source_id)
    if dataset_id:
        query = query.where(ErpSyncRun.erp_dataset_id == dataset_id)
    if station_id:
        query = query.where(ErpSyncRun.station_id == station_id)
    if status_filter:
        query = query.where(ErpSyncRun.status == status_filter)
    if sync_mode:
        query = query.where(ErpSyncRun.sync_mode == sync_mode)
    if trigger_type:
        query = query.where(ErpSyncRun.trigger_type == trigger_type)
    if created_from:
        query = query.where(ErpSyncRun.created_at >= created_from)
    if created_to:
        query = query.where(ErpSyncRun.created_at <= created_to)
    total = await db.scalar(select(func.count()).select_from(query.subquery()))
    sort_column = ErpSyncRun.started_at if sort_by == "started_at" else ErpSyncRun.created_at
    order = sort_column.asc() if sort_dir == "asc" else sort_column.desc()
    result = await db.execute(query.order_by(order).offset((page - 1) * page_size).limit(page_size))
    items = [XpertSyncRunResponse.model_validate(r) for r in result.scalars().all()]
    return XpertSyncRunListResponse(items=items, total=total or 0, page=page, page_size=page_size)


@router.get("/sync-runs/{run_id}", response_model=XpertSyncRunResponse)
async def get_sync_run(
    run_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> XpertSyncRunResponse:
    _ensure(user, Permission.ERP_SYNC_READ)
    run = await db.get(ErpSyncRun, run_id)
    if run is None or run.organization_id != user.organization_id:
        raise AppError("Execução não encontrada.", status_code=404, code="XPERT_SYNC_RUN_NOT_FOUND")
    return XpertSyncRunResponse.model_validate(run)


@router.post("/sync-runs/{run_id}/cancel", response_model=XpertSyncRunResponse)
async def cancel_sync_run(
    run_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> XpertSyncRunResponse:
    _ensure(user, Permission.ERP_SYNC_CANCEL)
    run = await db.get(ErpSyncRun, run_id)
    if run is None or run.organization_id != user.organization_id:
        raise AppError("Execução não encontrada.", status_code=404, code="XPERT_SYNC_RUN_NOT_FOUND")
    sync = XpertSyncService(db)
    run = await sync.request_cancel(run)
    await db.commit()
    await db.refresh(run)
    return XpertSyncRunResponse.model_validate(run)


@router.post("/sync-runs/{run_id}/retry", response_model=XpertSyncRunCreateResponse, status_code=status.HTTP_202_ACCEPTED)
async def retry_sync_run(
    run_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> XpertSyncRunCreateResponse:
    _ensure(user, Permission.ERP_SYNC_RETRY)
    run = await db.get(ErpSyncRun, run_id)
    if run is None or run.organization_id != user.organization_id:
        raise AppError("Execução não encontrada.", status_code=404, code="XPERT_SYNC_RUN_NOT_FOUND")
    dataset = await db.get(ErpDataset, run.erp_dataset_id)
    service = XpertSourceService(db)
    source = await service.get_source(user.organization_id, run.erp_source_id)
    runs = await service.enqueue_sync_runs(
        organization_id=user.organization_id,
        source=source,
        dataset_codes=[dataset.code] if dataset else [],
        station_ids=[run.station_id] if run.station_id else [],
        sync_mode=run.sync_mode,
        trigger_type=ErpSyncTrigger.RETRY,
        requested_by=user.id,
        retried_from_run_id=run.id,
    )
    await db.commit()
    for item in runs:
        await db.refresh(item)
    return XpertSyncRunCreateResponse(runs=[XpertSyncRunResponse.model_validate(r) for r in runs])


@router.get("/sync-runs/{run_id}/supplier-document-diagnostics", response_model=XpertSupplierDocumentDiagnosticsResponse)
async def supplier_document_diagnostics(
    run_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> XpertSupplierDocumentDiagnosticsResponse:
    _ensure(user, Permission.ERP_SYNC_VIEW_ERRORS)
    run = await db.get(ErpSyncRun, run_id)
    if run is None or run.organization_id != user.organization_id:
        raise AppError("Execução não encontrada.", status_code=404, code="XPERT_SYNC_RUN_NOT_FOUND")
    dataset = await db.get(ErpDataset, run.erp_dataset_id)
    if dataset is None or dataset.code != ErpDatasetCode.SUPPLIERS:
        raise AppError(
            "Diagnóstico disponível apenas para execuções de fornecedores.",
            status_code=400,
            code="XPERT_DIAGNOSTICS_NOT_SUPPLIERS",
        )
    result = await db.execute(
        select(ErpStagingRecord).where(ErpStagingRecord.sync_run_id == run_id)
    )
    rows = list(result.scalars().all())
    classifications = []
    quarantined = 0
    applied = 0
    invalid_reasons: dict[str, int] = {
        DocumentDiagnostic.EMPTY.value: 0,
        DocumentDiagnostic.FEWER_THAN_14_DIGITS.value: 0,
        DocumentDiagnostic.CPF_11_DIGITS.value: 0,
        DocumentDiagnostic.REPEATED_DIGITS.value: 0,
        DocumentDiagnostic.CHECK_DIGIT_INVALID.value: 0,
        DocumentDiagnostic.OTHER_FORMAT.value: 0,
    }
    for row in rows:
        payload = row.normalized_payload or row.raw_payload or {}
        raw_doc = payload.get("source_cnpj_raw") or payload.get("source_cnpj")
        classification = classify_supplier_document(raw_doc if isinstance(raw_doc, str) else None)
        classifications.append(classification)
        if row.processing_status == ErpStagingStatus.QUARANTINED:
            quarantined += 1
            reason = payload.get("document_diagnostic") or (
                classification.diagnostic.value if classification.diagnostic else DocumentDiagnostic.OTHER_FORMAT.value
            )
            if classification.document_type == SupplierDocumentType.INVALID:
                invalid_reasons[reason] = invalid_reasons.get(reason, 0) + 1
        elif row.processing_status in (ErpStagingStatus.APPLIED, ErpStagingStatus.SKIPPED_UNCHANGED):
            applied += 1
        if classification.document_type == SupplierDocumentType.CPF:
            invalid_reasons[DocumentDiagnostic.CPF_11_DIGITS.value] += 1
        elif classification.document_type == SupplierDocumentType.NONE:
            invalid_reasons[DocumentDiagnostic.EMPTY.value] += 1
    grouped = {key: value for key, value in invalid_reasons.items() if value > 0}
    return XpertSupplierDocumentDiagnosticsResponse(
        run_id=run_id,
        total_staged=len(rows),
        applied=applied,
        quarantined_invalid_document=quarantined,
        by_reason=grouped,
    )


@router.get("/sync-runs/{run_id}/errors", response_model=list[XpertSyncErrorResponse])
async def list_sync_errors(
    run_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> list[XpertSyncErrorResponse]:
    _ensure(user, Permission.ERP_SYNC_VIEW_ERRORS)
    run = await db.get(ErpSyncRun, run_id)
    if run is None or run.organization_id != user.organization_id:
        raise AppError("Execução não encontrada.", status_code=404, code="XPERT_SYNC_RUN_NOT_FOUND")
    result = await db.execute(
        select(ErpSyncError).where(ErpSyncError.sync_run_id == run_id).order_by(ErpSyncError.created_at.desc())
    )
    return [XpertSyncErrorResponse.model_validate(e) for e in result.scalars().all()]


@router.get("/sync-runs/{run_id}/staging", response_model=list[XpertStagingRecordResponse])
async def list_staging(
    run_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> list[XpertStagingRecordResponse]:
    _ensure(user, Permission.ERP_SYNC_VIEW_STAGING)
    run = await db.get(ErpSyncRun, run_id)
    if run is None or run.organization_id != user.organization_id:
        raise AppError("Execução não encontrada.", status_code=404, code="XPERT_SYNC_RUN_NOT_FOUND")
    result = await db.execute(
        select(ErpStagingRecord).where(ErpStagingRecord.sync_run_id == run_id).order_by(ErpStagingRecord.created_at)
    )
    return [XpertStagingRecordResponse.model_validate(r) for r in result.scalars().all()]


@router.get("/checkpoints", response_model=list[XpertCheckpointResponse])
async def list_checkpoints(
    source_id: uuid.UUID | None = None,
    dataset_id: uuid.UUID | None = None,
    station_id: uuid.UUID | None = None,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> list[XpertCheckpointResponse]:
    _ensure(user, Permission.ERP_SYNC_READ)
    query = select(ErpSyncCheckpoint).where(
        ErpSyncCheckpoint.erp_source_id.in_(
            select(ErpDataset.erp_source_id).join(ErpDataset.source).where(
                ErpDataset.source.has(organization_id=user.organization_id)
            )
        )
    )
    if source_id:
        query = query.where(ErpSyncCheckpoint.erp_source_id == source_id)
    if dataset_id:
        query = query.where(ErpSyncCheckpoint.erp_dataset_id == dataset_id)
    if station_id:
        query = query.where(ErpSyncCheckpoint.station_id == station_id)
    result = await db.execute(query)
    return [XpertCheckpointResponse.model_validate(c) for c in result.scalars().all()]


@router.post("/checkpoints/{checkpoint_id}/reset", response_model=XpertCheckpointResponse)
async def reset_checkpoint(
    checkpoint_id: uuid.UUID,
    payload: XpertCheckpointReset,
    user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    audit_ctx: AuditContext = Depends(get_audit_context),
) -> XpertCheckpointResponse:
    _ensure(user, Permission.ERP_SYNC_RESET_CHECKPOINT)
    checkpoint = await db.get(ErpSyncCheckpoint, checkpoint_id)
    if checkpoint is None:
        raise AppError("Checkpoint não encontrado.", status_code=404, code="XPERT_CHECKPOINT_NOT_FOUND")
    service = XpertCheckpointService(db)
    await service.reset(checkpoint=checkpoint, mode=payload.mode, new_value=payload.new_value)
    await db.commit()
    await db.refresh(checkpoint)
    return XpertCheckpointResponse.model_validate(checkpoint)
