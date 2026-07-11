"""APIs Sprint 9 — índices externos."""

from __future__ import annotations

import json
import uuid
from datetime import date

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_audit_context, get_current_active_user
from app.core.exceptions import AppError
from app.core.permissions import Permission
from app.schemas.external_data import (
    ExternalSeriesCreate,
    ExternalSeriesResponse,
    ExternalSourceCreate,
    ExternalSourceResponse,
    ImportConfirmRequest,
    ManualObservationCreate,
    QualityIssueResponse,
    RunResponse,
    SchedulerToggleRequest,
    observation_to_response,
)
from app.services.audit_service import AuditContext
from app.services.auth_service import AuthenticatedUser
from app.services.external_data.freshness_service import ExternalFreshnessService
from app.services.external_data_service import ExternalDataService

data_router = APIRouter(prefix="/external-data", tags=["external-data"])
analytics_router = APIRouter(prefix="/analytics/external-indices", tags=["external-indices-analytics"])


def _ensure(user: AuthenticatedUser, permission: Permission) -> None:
    if permission.value not in user.permissions:
        raise AppError(
            "Você não possui permissão para executar esta ação.",
            status_code=403,
            code="FORBIDDEN",
        )


@data_router.post("/bootstrap-catalog")
async def bootstrap_catalog(
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
    audit_ctx: AuditContext = Depends(get_audit_context),
):
    _ensure(user, Permission.EXTERNAL_DATA_MANAGE_SOURCES)
    service = ExternalDataService(db)
    return await service.seed_default_catalog(
        organization_id=user.organization_id,
        user_id=user.id,
        audit_ctx=audit_ctx,
    )


@data_router.get("/sources", response_model=list[ExternalSourceResponse])
async def list_sources(
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.EXTERNAL_DATA_READ)
    return await ExternalDataService(db).list_sources(user.organization_id)


@data_router.post("/sources", response_model=ExternalSourceResponse, status_code=201)
async def create_source(
    payload: ExternalSourceCreate,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
    audit_ctx: AuditContext = Depends(get_audit_context),
):
    _ensure(user, Permission.EXTERNAL_DATA_MANAGE_SOURCES)
    return await ExternalDataService(db).create_source(
        organization_id=user.organization_id,
        user_id=user.id,
        data=payload.model_dump(),
        audit_ctx=audit_ctx,
    )


@data_router.get("/sources/{source_id}", response_model=ExternalSourceResponse)
async def get_source(
    source_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.EXTERNAL_DATA_READ)
    return await ExternalDataService(db).get_source(source_id, user.organization_id)


@data_router.post("/sources/{source_id}/test")
async def test_source(
    source_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.EXTERNAL_DATA_MANAGE_SOURCES)
    return await ExternalDataService(db).test_source(source_id, user.organization_id)


@data_router.post("/sources/{source_id}/scheduler")
async def toggle_scheduler(
    source_id: uuid.UUID,
    payload: SchedulerToggleRequest,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.EXTERNAL_DATA_MANAGE_SCHEDULE)
    return await ExternalDataService(db).enable_scheduler_guard(
        source_id, user.organization_id, payload.enabled
    )


@data_router.get("/series", response_model=list[ExternalSeriesResponse])
async def list_series(
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.EXTERNAL_DATA_READ)
    return await ExternalDataService(db).list_series(user.organization_id)


@data_router.post("/series", response_model=ExternalSeriesResponse, status_code=201)
async def create_series(
    payload: ExternalSeriesCreate,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
    audit_ctx: AuditContext = Depends(get_audit_context),
):
    _ensure(user, Permission.EXTERNAL_DATA_MANAGE_SERIES)
    return await ExternalDataService(db).create_series(
        organization_id=user.organization_id,
        data=payload.model_dump(),
        audit_ctx=audit_ctx,
    )


@data_router.get("/series/{series_id}", response_model=ExternalSeriesResponse)
async def get_series(
    series_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.EXTERNAL_DATA_READ)
    return await ExternalDataService(db).get_series(series_id, user.organization_id)


@data_router.get("/series/{series_id}/observations")
async def list_observations(
    series_id: uuid.UUID,
    date_from: date | None = None,
    date_to: date | None = None,
    current_only: bool = True,
    limit: int = Query(500, ge=1, le=5000),
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.EXTERNAL_DATA_READ)
    rows = await ExternalDataService(db).list_observations(
        series_id=series_id,
        organization_id=user.organization_id,
        date_from=date_from,
        date_to=date_to,
        current_only=current_only,
        limit=limit,
    )
    return [observation_to_response(r) for r in rows]


@data_router.get("/series/{series_id}/freshness")
async def series_freshness(
    series_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.EXTERNAL_DATA_READ)
    series = await ExternalDataService(db).get_series(series_id, user.organization_id)
    result = await ExternalFreshnessService(db).evaluate_series(series)
    return {
        "series_id": result.series_id,
        "series_code": result.series_code,
        "status": result.status.value,
        "last_observation_datetime": result.last_observation_datetime,
        "last_published_at": result.last_published_at,
        "last_fetched_at": result.last_fetched_at,
        "expected_by": result.expected_by,
        "grace_minutes": result.grace_minutes,
        "frequency": result.frequency,
    }


@data_router.post("/series/{series_id}/observations")
async def create_manual_observation(
    series_id: uuid.UUID,
    payload: ManualObservationCreate,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
    audit_ctx: AuditContext = Depends(get_audit_context),
):
    _ensure(user, Permission.EXTERNAL_DATA_IMPORT)
    return await ExternalDataService(db).create_manual_observation(
        series_id=series_id,
        organization_id=user.organization_id,
        user_id=user.id,
        data=payload.model_dump(),
        audit_ctx=audit_ctx,
    )


@data_router.post("/import/preview")
async def import_preview(
    series_id: uuid.UUID = Form(...),
    date_column: str = Form("date"),
    value_column: str = Form("value"),
    date_format: str | None = Form(None),
    timezone: str = Form("America/Sao_Paulo"),
    unit: str | None = Form(None),
    currency: str | None = Form(None),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
    audit_ctx: AuditContext = Depends(get_audit_context),
):
    _ensure(user, Permission.EXTERNAL_DATA_IMPORT)
    content = await file.read()
    return await ExternalDataService(db).preview_csv_import(
        organization_id=user.organization_id,
        user_id=user.id,
        series_id=series_id,
        filename=file.filename or "import.csv",
        content=content,
        mapping={
            "date_column": date_column,
            "value_column": value_column,
            "date_format": date_format,
            "timezone": timezone,
            "unit": unit,
            "currency": currency,
        },
        audit_ctx=audit_ctx,
    )


@data_router.post("/import/confirm")
async def import_confirm(
    payload: ImportConfirmRequest,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
    audit_ctx: AuditContext = Depends(get_audit_context),
):
    _ensure(user, Permission.EXTERNAL_DATA_IMPORT)
    return await ExternalDataService(db).confirm_csv_import(
        organization_id=user.organization_id,
        user_id=user.id,
        import_file_id=payload.import_file_id,
        audit_ctx=audit_ctx,
    )


@data_router.get("/runs", response_model=list[RunResponse])
async def list_runs(
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.EXTERNAL_DATA_READ)
    return await ExternalDataService(db).list_runs(user.organization_id)


@data_router.get("/quality-issues", response_model=list[QualityIssueResponse])
async def list_quality_issues(
    open_only: bool = True,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.EXTERNAL_DATA_READ)
    return await ExternalDataService(db).list_quality_issues(user.organization_id, open_only=open_only)


@analytics_router.get("/summary")
async def analytics_summary(
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.EXTERNAL_DATA_READ)
    return await ExternalDataService(db).analytics_summary(user.organization_id)


@analytics_router.get("/series")
async def analytics_series(
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.EXTERNAL_DATA_READ)
    rows = await ExternalDataService(db).list_series(user.organization_id)
    return [ExternalSeriesResponse.model_validate(r) for r in rows]


@analytics_router.get("/freshness")
async def analytics_freshness(
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.EXTERNAL_DATA_READ)
    service = ExternalDataService(db)
    series_list = await service.list_series(user.organization_id)
    out = []
    for series in series_list:
        r = await ExternalFreshnessService(db).evaluate_series(series)
        out.append(
            {
                "series_id": r.series_id,
                "series_code": r.series_code,
                "status": r.status.value,
                "last_observation_datetime": r.last_observation_datetime,
                "expected_by": r.expected_by,
                "frequency": r.frequency,
            }
        )
    return out


@analytics_router.get("/data-quality")
async def analytics_data_quality(
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.EXTERNAL_DATA_READ)
    issues = await ExternalDataService(db).list_quality_issues(user.organization_id, open_only=False)
    return [QualityIssueResponse.model_validate(i) for i in issues]


@analytics_router.get("/export/csv")
async def export_csv(
    series_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.EXTERNAL_DATA_EXPORT)
    rows = await ExternalDataService(db).list_observations(
        series_id=series_id,
        organization_id=user.organization_id,
        limit=5000,
    )
    lines = [
        "observation_datetime,canonical_value,canonical_unit,currency,published_at,fetched_at,revision_number,revision_status"
    ]
    for r in rows:
        lines.append(
            ",".join(
                [
                    r.observation_datetime.isoformat(),
                    str(r.canonical_value),
                    r.canonical_unit,
                    r.currency or "",
                    r.published_at.isoformat() if r.published_at else "",
                    r.fetched_at.isoformat(),
                    str(r.revision_number),
                    r.revision_status,
                ]
            )
        )
    return Response(
        content="\n".join(lines) + "\n",
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="external-series-{series_id}.csv"'},
    )


@analytics_router.get("/export/pdf")
async def export_pdf_placeholder(
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.EXTERNAL_DATA_EXPORT)
    summary = await ExternalDataService(db).analytics_summary(user.organization_id)
    # PDF executivo mínimo em texto estruturado (sem previsão/recomendação)
    body = {
        "title": "Relatório de índices externos",
        "disclaimer": summary["disclaimer"],
        "cards": summary["cards"],
        "stale_series_count": summary["stale_series_count"],
        "open_quality_issues": summary["open_quality_issues"],
    }
    return Response(
        content=json.dumps(body, ensure_ascii=False, indent=2, default=str).encode("utf-8"),
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="external-indices-report.json"'},
    )
