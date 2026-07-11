"""APIs Sprint 12 — executive, alerts, operations."""

from __future__ import annotations

import csv
import io
import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_audit_context, get_current_active_user
from app.core.exceptions import AppError
from app.core.permissions import Permission
from app.services.alert_engine_service import AlertEngineService
from app.services.audit_service import AuditContext
from app.services.auth_service import AuthenticatedUser
from app.services.executive_metrics_service import ExecutiveMetricsService
from app.services.operations_service import OperationsService

executive_router = APIRouter(prefix="/executive", tags=["executive"])
alerts_router = APIRouter(prefix="/alerts", tags=["alerts"])
alert_rules_router = APIRouter(prefix="/alert-rules", tags=["alert-rules"])
operations_router = APIRouter(prefix="/operations", tags=["operations"])
notifications_router = APIRouter(prefix="/notifications", tags=["notifications"])
notification_policies_router = APIRouter(
    prefix="/notification-policies", tags=["notification-policies"]
)


def _ensure(user: AuthenticatedUser, permission: Permission) -> None:
    if permission.value not in user.permissions:
        raise AppError(
            "Você não possui permissão para executar esta ação.",
            status_code=403,
            code="FORBIDDEN",
        )


class RuleCreate(BaseModel):
    code: str
    name: str
    metric_code: str
    operator: str
    threshold_value: str | None = None
    alert_type: str = "BUSINESS"
    severity: str = "WARNING"
    description: str | None = None
    cooldown_minutes: int = 30
    auto_resolve: bool = True
    station_id: uuid.UUID | None = None


class AlertAction(BaseModel):
    comment: str | None = None


class AssignBody(BaseModel):
    assigned_user_id: uuid.UUID | None = None
    assigned_role: str | None = None


class SnoozeBody(BaseModel):
    minutes: int = Field(default=60, ge=1, le=10080)


class ResolveBody(BaseModel):
    resolution_code: str = "FIXED"
    note: str | None = None


class IncidentCreate(BaseModel):
    title: str
    severity: str = "SEV3"
    description: str | None = None
    related_alert_ids: list[str] | None = None


class IncidentStatusBody(BaseModel):
    status: str
    resolution_summary: str | None = None


class FlagUpdate(BaseModel):
    enabled: bool


class SyntheticExecutiveBody(BaseModel):
    station_ids: list[uuid.UUID] | None = None


# ---- executive ----
@executive_router.get("/summary")
async def executive_summary(
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.EXECUTIVE_DASHBOARD_READ)
    data = await ExecutiveMetricsService(db).summary(user.organization_id)
    if Permission.EXECUTIVE_DASHBOARD_VIEW_FINANCIALS.value not in user.permissions:
        for c in data.get("cards", []):
            if c.get("unit") in ("BRL/L", "BRL"):
                c["value"] = None
                c["empty_reason"] = "PERMISSION_RESTRICTED"
    return data


@executive_router.get("/by-station")
async def executive_by_station(
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.EXECUTIVE_DASHBOARD_READ)
    return await ExecutiveMetricsService(db).by_station(user.organization_id)


@executive_router.get("/trends")
async def executive_trends(
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.EXECUTIVE_DASHBOARD_READ)
    return {
        "points": [],
        "empty_reason": "NO_DATA",
        "note": "Trends usam snapshots materializados; execute materialização/homologação sintética.",
    }


@executive_router.get("/data-quality")
async def executive_data_quality(
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.EXECUTIVE_DASHBOARD_READ)
    return await ExecutiveMetricsService(db).data_quality(user.organization_id)


@executive_router.get("/freshness")
async def executive_freshness(
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.EXECUTIVE_DASHBOARD_READ)
    return await ExecutiveMetricsService(db).freshness(user.organization_id)


@executive_router.get("/readiness")
async def executive_readiness(
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.OPERATIONS_VIEW_READINESS)
    return await OperationsService(db).readiness(user.organization_id)


@executive_router.post("/homologation/synthetic")
async def executive_synthetic(
    payload: SyntheticExecutiveBody,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
    audit_ctx: AuditContext = Depends(get_audit_context),
):
    _ensure(user, Permission.EXECUTIVE_DASHBOARD_READ)
    svc = ExecutiveMetricsService(db)
    station_ids = payload.station_ids or await svc.list_station_ids(user.organization_id)
    if len(station_ids) < 1:
        raise AppError("Nenhum posto disponível para homologação.", status_code=400, code="NO_STATIONS")
    data = await svc.build_synthetic_dashboard(user.organization_id, station_ids)
    return data


@executive_router.get("/export/csv")
async def executive_export_csv(
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.EXECUTIVE_DASHBOARD_EXPORT)
    data = await ExecutiveMetricsService(db).summary(user.organization_id)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["metric_code", "value", "quality", "freshness", "coverage", "updated_at"])
    for c in data.get("cards", []):
        w.writerow(
            [
                c.get("metric_code"),
                c.get("value"),
                c.get("quality_status"),
                c.get("freshness_status"),
                c.get("coverage_percentage"),
                c.get("updated_at"),
            ]
        )
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=executive-summary.csv"},
    )


@executive_router.get("/export/pdf")
async def executive_export_pdf(
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.EXECUTIVE_DASHBOARD_EXPORT)
    data = await ExecutiveMetricsService(db).summary(user.organization_id)
    lines = [
        "RELATÓRIO EXECUTIVO — INTELIGÊNCIA AUTO POSTOS",
        f"organization={user.organization_id}",
        data.get("disclaimer") or "",
        "xpert_write=false",
        "scheduler_blocked=true",
    ]
    for c in data.get("cards", []):
        lines.append(
            f"{c.get('metric_code')}={c.get('value')} quality={c.get('quality_status')} "
            f"freshness={c.get('freshness_status')} coverage={c.get('coverage_percentage')}"
        )
    return Response(
        content="\n".join(lines) + "\n",
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=executive-report.pdf"},
    )


# ---- alerts ----
@alerts_router.get("")
async def list_alerts(
    status: str | None = None,
    severity: str | None = None,
    station_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.ALERTS_READ)
    rows = await AlertEngineService(db).list_alerts(
        user.organization_id, status=status, severity=severity, station_id=station_id
    )
    return [
        {
            "id": str(a.id),
            "alert_code": a.alert_code,
            "alert_type": a.alert_type,
            "severity": a.severity,
            "priority": a.priority,
            "status": a.status,
            "title": a.title,
            "summary": a.summary,
            "station_id": str(a.station_id) if a.station_id else None,
            "occurrence_count": a.occurrence_count,
            "first_detected_at": a.first_detected_at,
            "last_detected_at": a.last_detected_at,
            "due_at": a.due_at,
            "assigned_user_id": str(a.assigned_user_id) if a.assigned_user_id else None,
            "deep_link": a.deep_link,
            "dismissible": a.dismissible,
        }
        for a in rows
    ]


@alerts_router.get("/summary")
async def alerts_summary(
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.ALERTS_READ)
    return await AlertEngineService(db).summary_cards(user.organization_id)


@alerts_router.get("/export/csv")
async def alerts_export_csv(
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.ALERTS_EXPORT)
    rows = await AlertEngineService(db).list_alerts(user.organization_id)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["id", "code", "severity", "status", "title", "station_id", "detected"])
    for a in rows:
        w.writerow(
            [a.id, a.alert_code, a.severity, a.status, a.title, a.station_id, a.last_detected_at]
        )
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=alerts.csv"},
    )


@alerts_router.post("/homologation/synthetic")
async def alerts_synthetic(
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.ALERTS_MANAGE_RULES)
    created = await AlertEngineService(db).create_synthetic_alerts(user.organization_id)
    return {"alerts": created, "xpert_write": False}


@alerts_router.get("/{alert_id}")
async def get_alert(
    alert_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.ALERTS_READ)
    a = await AlertEngineService(db).get_alert(alert_id, user.organization_id)
    return {
        "id": str(a.id),
        "alert_code": a.alert_code,
        "title": a.title,
        "summary": a.summary,
        "description": a.description,
        "severity": a.severity,
        "priority": a.priority,
        "status": a.status,
        "evidence_snapshot": a.evidence_snapshot,
        "deep_link": a.deep_link,
        "occurrence_count": a.occurrence_count,
        "dismissible": a.dismissible,
        "resolution_code": a.resolution_code,
        "resolution_note": a.resolution_note,
    }


@alerts_router.post("/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: uuid.UUID,
    payload: AlertAction,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
    audit_ctx: AuditContext = Depends(get_audit_context),
):
    _ensure(user, Permission.ALERTS_ACKNOWLEDGE)
    a = await AlertEngineService(db).acknowledge(
        alert_id, user.organization_id, user.id, payload.comment, audit_ctx=audit_ctx
    )
    return {"id": str(a.id), "status": a.status}


@alerts_router.post("/{alert_id}/assign")
async def assign_alert(
    alert_id: uuid.UUID,
    payload: AssignBody,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
    audit_ctx: AuditContext = Depends(get_audit_context),
):
    _ensure(user, Permission.ALERTS_ASSIGN)
    a = await AlertEngineService(db).assign(
        alert_id,
        user.organization_id,
        assigned_user_id=payload.assigned_user_id,
        assigned_role=payload.assigned_role,
        user_id=user.id,
        audit_ctx=audit_ctx,
    )
    return {"id": str(a.id), "status": a.status}


@alerts_router.post("/{alert_id}/snooze")
async def snooze_alert(
    alert_id: uuid.UUID,
    payload: SnoozeBody,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
    audit_ctx: AuditContext = Depends(get_audit_context),
):
    _ensure(user, Permission.ALERTS_ACKNOWLEDGE)
    a = await AlertEngineService(db).snooze(
        alert_id, user.organization_id, minutes=payload.minutes, user_id=user.id, audit_ctx=audit_ctx
    )
    return {"id": str(a.id), "status": a.status, "snoozed_until": a.snoozed_until}


@alerts_router.post("/{alert_id}/resolve")
async def resolve_alert(
    alert_id: uuid.UUID,
    payload: ResolveBody,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
    audit_ctx: AuditContext = Depends(get_audit_context),
):
    _ensure(user, Permission.ALERTS_RESOLVE)
    a = await AlertEngineService(db).resolve_alert(
        alert_id,
        user.organization_id,
        user_id=user.id,
        resolution_code=payload.resolution_code,
        note=payload.note,
        audit_ctx=audit_ctx,
    )
    return {"id": str(a.id), "status": a.status}


@alerts_router.post("/{alert_id}/reopen")
async def reopen_alert(
    alert_id: uuid.UUID,
    payload: AlertAction,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
    audit_ctx: AuditContext = Depends(get_audit_context),
):
    _ensure(user, Permission.ALERTS_RESOLVE)
    a = await AlertEngineService(db).reopen(
        alert_id, user.organization_id, user.id, payload.comment, audit_ctx=audit_ctx
    )
    return {"id": str(a.id), "status": a.status}


@alerts_router.post("/{alert_id}/comment")
async def comment_alert(
    alert_id: uuid.UUID,
    payload: AlertAction,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.ALERTS_ACKNOWLEDGE)
    if not payload.comment:
        raise AppError("Comentário obrigatório.", status_code=400, code="COMMENT_REQUIRED")
    ev = await AlertEngineService(db).comment(
        alert_id, user.organization_id, user.id, payload.comment
    )
    return {"id": str(ev.id), "event_type": ev.event_type}


# ---- rules ----
@alert_rules_router.get("")
async def list_rules(
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.ALERTS_READ)
    rows = await AlertEngineService(db).list_rules(user.organization_id)
    return [
        {
            "id": str(r.id),
            "code": r.code,
            "name": r.name,
            "severity": r.severity,
            "metric_code": r.metric_code,
            "operator": r.operator,
            "threshold_value": str(r.threshold_value) if r.threshold_value is not None else None,
            "active": r.active,
        }
        for r in rows
    ]


@alert_rules_router.post("", status_code=201)
async def create_rule(
    payload: RuleCreate,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
    audit_ctx: AuditContext = Depends(get_audit_context),
):
    _ensure(user, Permission.ALERTS_MANAGE_RULES)
    rule = await AlertEngineService(db).create_rule(
        organization_id=user.organization_id,
        user_id=user.id,
        data=payload.model_dump(mode="json"),
        audit_ctx=audit_ctx,
    )
    return {"id": str(rule.id), "code": rule.code}


@alert_rules_router.post("/{rule_id}/deactivate")
async def deactivate_rule(
    rule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
    audit_ctx: AuditContext = Depends(get_audit_context),
):
    _ensure(user, Permission.ALERTS_MANAGE_RULES)
    rule = await AlertEngineService(db).deactivate_rule(rule_id, user.organization_id, audit_ctx)
    return {"id": str(rule.id), "active": rule.active}


@alert_rules_router.post("/{rule_id}/test")
async def test_rule(
    rule_id: uuid.UUID,
    observed_value: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.ALERTS_MANAGE_RULES)
    svc = AlertEngineService(db)
    rule = await svc.get_rule(rule_id, user.organization_id)
    from decimal import Decimal

    alert = await svc.evaluate_rule(
        rule=rule,
        observed_value=Decimal(observed_value) if observed_value is not None else None,
        context={"source_module": "rule_test", "deep_link": "/executive/alerts"},
    )
    return {"matched": alert is not None, "alert_id": str(alert.id) if alert else None}


# ---- operations ----
@operations_router.get("/health")
async def operations_health(
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.OPERATIONS_READ_HEALTH)
    return await OperationsService(db).dependencies_health()


@operations_router.get("/jobs")
async def operations_jobs(
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.OPERATIONS_READ_JOBS)
    return await OperationsService(db).list_jobs()


@operations_router.post("/outbox/process")
async def process_outbox(
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.OPERATIONS_MANAGE_JOBS)
    return await OperationsService(db).process_outbox_batch()


@operations_router.get("/slo")
async def operations_slo(
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.OPERATIONS_READ_SLO)
    return await OperationsService(db).calculate_slo_placeholders(user.organization_id)


@operations_router.get("/incidents")
async def list_incidents(
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.OPERATIONS_MANAGE_INCIDENTS)
    rows = await OperationsService(db).list_incidents(user.organization_id)
    return [
        {
            "id": str(i.id),
            "title": i.title,
            "severity": i.severity,
            "status": i.status,
            "detected_at": i.detected_at,
            "postmortem_required": i.postmortem_required,
        }
        for i in rows
    ]


@operations_router.post("/incidents", status_code=201)
async def create_incident(
    payload: IncidentCreate,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
    audit_ctx: AuditContext = Depends(get_audit_context),
):
    _ensure(user, Permission.OPERATIONS_MANAGE_INCIDENTS)
    inc = await OperationsService(db).create_incident(
        organization_id=user.organization_id,
        title=payload.title,
        severity=payload.severity,
        description=payload.description,
        related_alert_ids=payload.related_alert_ids,
        audit_ctx=audit_ctx,
    )
    return {"id": str(inc.id), "status": inc.status}


@operations_router.post("/incidents/{incident_id}/status")
async def incident_status(
    incident_id: uuid.UUID,
    payload: IncidentStatusBody,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
    audit_ctx: AuditContext = Depends(get_audit_context),
):
    _ensure(user, Permission.OPERATIONS_MANAGE_INCIDENTS)
    inc = await OperationsService(db).update_incident_status(
        incident_id,
        payload.status,
        resolution_summary=payload.resolution_summary,
        audit_ctx=audit_ctx,
    )
    return {"id": str(inc.id), "status": inc.status}


@operations_router.get("/readiness")
async def operations_readiness(
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.OPERATIONS_VIEW_READINESS)
    return await OperationsService(db).readiness(user.organization_id)


@operations_router.get("/feature-flags")
async def list_flags(
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.OPERATIONS_VIEW_READINESS)
    flags = await OperationsService(db).get_or_seed_flags(user.organization_id, user.id)
    return [{"flag_code": f.flag_code, "enabled": f.enabled} for f in flags]


@operations_router.put("/feature-flags/{flag_code}")
async def update_flag(
    flag_code: str,
    payload: FlagUpdate,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
    audit_ctx: AuditContext = Depends(get_audit_context),
):
    _ensure(user, Permission.OPERATIONS_MANAGE_FEATURE_FLAGS)
    flag = await OperationsService(db).set_flag(
        user.organization_id, flag_code, payload.enabled, user.id, audit_ctx=audit_ctx
    )
    return {"flag_code": flag.flag_code, "enabled": flag.enabled}


@operations_router.post("/backups/verify")
async def verify_backup(
    restore_drill: bool = False,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.OPERATIONS_MANAGE_JOBS)
    rec = await OperationsService(db).register_backup_verification(
        status="VERIFIED" if restore_drill else "REGISTERED",
        restore_drill=restore_drill,
        checksum="synthetic-homologation",
        details={"homologation": True},
    )
    return {
        "id": str(rec.id),
        "status": rec.status,
        "restore_drill_at": rec.restore_drill_at,
        "note": "Não declarar backup válido sem drill de restauração.",
    }


@notifications_router.get("")
async def list_notifications(
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.ALERTS_READ)
    from sqlalchemy import select
    from app.models.operations import Notification

    result = await db.execute(
        select(Notification)
        .where(Notification.organization_id == user.organization_id)
        .order_by(Notification.created_at.desc())
        .limit(100)
    )
    rows = list(result.scalars().all())
    return [
        {
            "id": str(n.id),
            "channel": n.channel,
            "status": n.status,
            "subject": n.subject,
            "alert_id": str(n.alert_id) if n.alert_id else None,
            "created_at": n.created_at,
        }
        for n in rows
    ]


@notification_policies_router.get("")
async def list_notification_policies(
    user: AuthenticatedUser = Depends(get_current_active_user),
):
    _ensure(user, Permission.ALERTS_READ)
    return {
        "policies": [
            {
                "channel": "IN_APP",
                "minimum_severity": "WARNING",
                "delivery_mode": "IMMEDIATE",
                "active": True,
            },
            {
                "channel": "EMAIL",
                "minimum_severity": "CRITICAL",
                "delivery_mode": "IMMEDIATE",
                "active": False,
                "note": "E-mail não homologado — permanece desabilitado.",
            },
        ]
    }
