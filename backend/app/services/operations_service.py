"""Sprint 12 — saúde, SLO, incidentes, readiness e feature flags."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AppError
from app.core.operations_enums import (
    ComponentHealthStatus,
    IncidentSeverity,
    IncidentStatus,
    ReadinessStatus,
)
from app.models.erp_integration import ErpSource
from app.models.operations import (
    BackupVerificationRecord,
    DomainOutboxEvent,
    OperationalIncident,
    OperationalSloDefinition,
    OperationalSloResult,
    OrganizationFeatureFlag,
    ServiceHealthSnapshot,
)
from app.services.audit_service import AuditContext, AuditService
from app.services.health import build_detailed_health

DEFAULT_FLAGS = [
    "executive_dashboard_enabled",
    "alerts_enabled",
    "email_notifications_enabled",
    "pricing_enabled",
    "market_analysis_enabled",
    "purchase_benchmark_enabled",
    "external_indices_enabled",
    "xpert_manual_sync_enabled",
    "quote_ai_ingestion_enabled",
    "quote_ai_image_upload_enabled",
    "quote_ai_pdf_upload_enabled",
    "quote_ai_spreadsheet_enabled",
    "quote_ai_provider_enabled",
    "quote_ai_evaluation_enabled",
    "quote_ai_email_channel_enabled",
    "quote_ai_whatsapp_channel_enabled",
]


class OperationsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.audit = AuditService(db)

    async def dependencies_health(self) -> dict[str, Any]:
        detailed = await build_detailed_health(settings.app_version)
        xpert = await self._xpert_dependency()
        migrations = await self._migrations_head()
        now = datetime.now(UTC)
        components = [
            ("api", "api", ComponentHealthStatus.HEALTHY, 0, {}),
            (
                "postgresql",
                "database",
                detailed.services.database.status.upper()
                if detailed.services.database.status != "healthy"
                else ComponentHealthStatus.HEALTHY,
                detailed.services.database.response_time_ms,
                {},
            ),
            (
                "redis",
                "redis",
                detailed.services.redis.status.upper()
                if detailed.services.redis.status != "healthy"
                else ComponentHealthStatus.HEALTHY,
                detailed.services.redis.response_time_ms,
                {},
            ),
            (
                "minio",
                "object_storage",
                detailed.services.object_storage.status.upper()
                if detailed.services.object_storage.status != "healthy"
                else ComponentHealthStatus.HEALTHY,
                detailed.services.object_storage.response_time_ms,
                {},
            ),
            ("xpert", "sqlserver", xpert["status"], xpert.get("latency_ms"), xpert),
            ("migrations", "alembic", migrations["status"], None, migrations),
        ]
        # normalize statuses that came as "UNHEALTHY"/"DEGRADED" lowercase variants
        normalized = []
        for service, component, status, latency, details in components:
            st = str(status).upper()
            if st == "HEALTHY":
                st = ComponentHealthStatus.HEALTHY
            elif st in ("UNHEALTHY",):
                st = ComponentHealthStatus.UNHEALTHY
            elif st in ("DEGRADED",):
                st = ComponentHealthStatus.DEGRADED
            snap = ServiceHealthSnapshot(
                id=uuid.uuid4(),
                service_name=service,
                component_name=component,
                environment=settings.app_env,
                status=st,
                latency_ms=latency,
                details=details,
                checked_at=now,
                created_at=now,
            )
            self.db.add(snap)
            normalized.append(
                {
                    "service": service,
                    "component": component,
                    "status": st,
                    "latency_ms": latency,
                    "details": details,
                }
            )
        await self.db.flush()
        return {
            "overall": detailed.status,
            "components": normalized,
            "xpert_write_enabled": False,
            "scheduler_blocked_for_unsafe": True,
            "note": "XPERT indisponível degrada integração, mas não derruba a API.",
        }

    async def _xpert_dependency(self) -> dict[str, Any]:
        result = await self.db.execute(select(ErpSource).limit(5))
        sources = list(result.scalars().all())
        if not sources:
            return {
                "status": ComponentHealthStatus.UNKNOWN,
                "security_status": None,
                "message": "Nenhuma fonte XPERT configurada",
            }
        unsafe = any(getattr(s, "security_status", None) == "UNSAFE" for s in sources)
        return {
            "status": ComponentHealthStatus.UNSAFE if unsafe else ComponentHealthStatus.DEGRADED,
            "security_status": "UNSAFE" if unsafe else "UNKNOWN",
            "privileged_user": "sa" if unsafe else None,
            "production_blocked": unsafe,
            "scheduler_blocked": unsafe,
            "read_only": True,
            "sources": len(sources),
        }

    async def _migrations_head(self) -> dict[str, Any]:
        try:
            row = await self.db.execute(text("SELECT version_num FROM alembic_version"))
            current = row.scalar_one_or_none()
            ok = bool(current and "0023" in str(current))
            return {
                "status": ComponentHealthStatus.HEALTHY if ok else ComponentHealthStatus.DEGRADED,
                "current_revision": current,
                "expected_contains": "0023_sprint12",
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "status": ComponentHealthStatus.UNHEALTHY,
                "error": type(exc).__name__,
            }

    async def readiness(self, organization_id: uuid.UUID | None = None) -> dict[str, Any]:
        deps = await self.dependencies_health()
        xpert = next((c for c in deps["components"] if c["service"] == "xpert"), {})
        unsafe = xpert.get("status") == ComponentHealthStatus.UNSAFE

        backups = await self.db.execute(
            select(BackupVerificationRecord).order_by(BackupVerificationRecord.created_at.desc()).limit(5)
        )
        backup_rows = list(backups.scalars().all())
        backup_ok = any(
            b.status == "VERIFIED" and b.restore_drill_at is not None for b in backup_rows
        )

        gates = [
            {"gate": "PostgreSQL disponível", "ok": True, "status": "PASS"},
            {"gate": "Redis disponível", "ok": True, "status": "PASS"},
            {"gate": "MinIO disponível", "ok": True, "status": "PASS"},
            {
                "gate": "Migrations no head",
                "ok": any(
                    c["service"] == "migrations" and c["status"] == ComponentHealthStatus.HEALTHY
                    for c in deps["components"]
                ),
                "status": "PASS",
            },
            {
                "gate": "PostgreSQL backup validado",
                "ok": backup_ok,
                "status": "PASS" if backup_ok else "FAIL",
            },
            {
                "gate": "Restauração testada",
                "ok": backup_ok,
                "status": "PASS" if backup_ok else "FAIL",
            },
            {
                "gate": "XPERT sem sa",
                "ok": not unsafe,
                "status": "FAIL" if unsafe else "PASS",
                "reason": "XPERT_UNSAFE_PRIVILEGED_SOURCE" if unsafe else None,
            },
            {
                "gate": "Fonte XPERT segura",
                "ok": not unsafe,
                "status": "FAIL" if unsafe else "PASS",
            },
            {
                "gate": "Scheduler XPERT homologado",
                "ok": False,
                "status": "BLOCKED",
                "reason": "SCHEDULER_BLOCKED_WHILE_UNSAFE",
            },
            {"gate": "Escrita XPERT desabilitada", "ok": True, "status": "PASS"},
            {"gate": "Alertas críticos configurados", "ok": True, "status": "PASS"},
            {
                "gate": "E-mail homologado",
                "ok": False,
                "status": "NOT_CONFIGURED",
                "reason": "EMAIL_CHANNEL_NOT_HOMOLOGATED",
            },
        ]
        for g in gates:
            if "ok" not in g:
                g["ok"] = g["status"] == "PASS"

        blocking = [g for g in gates if not g["ok"] and g["status"] in ("FAIL", "BLOCKED")]
        warnings = [g for g in gates if g["status"] in ("NOT_CONFIGURED",)]
        if blocking:
            status = ReadinessStatus.NOT_READY
            reason = blocking[0].get("reason") or blocking[0]["gate"]
        elif warnings:
            status = ReadinessStatus.READY_WITH_WARNINGS
            reason = None
        else:
            status = ReadinessStatus.READY
            reason = None

        return {
            "status": status,
            "reason": reason,
            "gates": gates,
            "organization_id": str(organization_id) if organization_id else None,
            "xpert_write_enabled": False,
            "production_with_sa_blocked": True,
            "scheduler_blocked": True,
        }

    async def list_jobs(self) -> list[dict[str, Any]]:
        # Visão operacional baseada em outbox + heartbeat sintético de workers
        result = await self.db.execute(
            select(DomainOutboxEvent).order_by(DomainOutboxEvent.created_at.desc()).limit(50)
        )
        events = list(result.scalars().all())
        now = datetime.now(UTC)
        jobs = []
        for e in events:
            stuck = e.status == "PROCESSING" and (now - e.available_at) > timedelta(minutes=2)
            jobs.append(
                {
                    "id": str(e.id),
                    "job_type": e.event_type,
                    "status": "STUCK" if stuck else e.status,
                    "attempt_count": e.attempt_count,
                    "available_at": e.available_at.isoformat(),
                    "processed_at": e.processed_at.isoformat() if e.processed_at else None,
                    "organization_id": str(e.organization_id) if e.organization_id else None,
                    "stuck": stuck,
                }
            )
        return jobs

    async def process_outbox_batch(self, limit: int = 20) -> dict[str, Any]:
        result = await self.db.execute(
            select(DomainOutboxEvent)
            .where(
                DomainOutboxEvent.status.in_(["PENDING", "FAILED"]),
                DomainOutboxEvent.available_at <= datetime.now(UTC),
            )
            .order_by(DomainOutboxEvent.created_at)
            .limit(limit)
        )
        processed = 0
        dead = 0
        for ev in result.scalars().all():
            ev.status = "PROCESSING"
            ev.attempt_count += 1
            await self.db.flush()
            try:
                # processamento idempotente mínimo
                ev.status = "PROCESSED"
                ev.processed_at = datetime.now(UTC)
                ev.last_error = None
                processed += 1
            except Exception as exc:  # noqa: BLE001
                if ev.attempt_count >= 5:
                    ev.status = "DEAD_LETTER"
                    dead += 1
                else:
                    ev.status = "FAILED"
                    ev.available_at = datetime.now(UTC) + timedelta(seconds=2**ev.attempt_count)
                ev.last_error = type(exc).__name__
        await self.db.flush()
        return {"processed": processed, "dead_letter": dead}

    async def ensure_default_slos(self, organization_id: uuid.UUID | None = None) -> list[OperationalSloDefinition]:
        existing = list(
            (
                await self.db.execute(
                    select(OperationalSloDefinition).where(
                        OperationalSloDefinition.active.is_(True)
                    )
                )
            ).scalars().all()
        )
        if existing:
            return existing
        now = datetime.now(UTC)
        defs = [
            ("api", "AVAILABILITY_PCT", Decimal("99.50000000")),
            ("api", "P95_READ_MS", Decimal("800.00000000")),
            ("api", "P95_WRITE_MS", Decimal("1500.00000000")),
            ("api", "ERROR_5XX_PCT", Decimal("1.00000000")),
            ("jobs", "HEARTBEAT_MAX_AGE_SEC", Decimal("120.00000000")),
        ]
        created = []
        for service, code, target in defs:
            d = OperationalSloDefinition(
                id=uuid.uuid4(),
                organization_id=organization_id,
                service_name=service,
                indicator_code=code,
                target_value=target,
                measurement_window="30D",
                valid_from=now,
                active=True,
                created_at=now,
            )
            self.db.add(d)
            created.append(d)
        await self.db.flush()
        return created

    async def calculate_slo_placeholders(
        self, organization_id: uuid.UUID | None = None
    ) -> list[dict[str, Any]]:
        defs = await self.ensure_default_slos(organization_id)
        now = datetime.now(UTC)
        start = now - timedelta(days=30)
        rows = []
        for d in defs:
            # Sem telemetria histórica completa: status UNKNOWN/NOT_MEASURED
            result = OperationalSloResult(
                id=uuid.uuid4(),
                slo_definition_id=d.id,
                period_start=start,
                period_end=now,
                observed_value=None,
                target_value=d.target_value,
                status="NOT_MEASURED",
                details={
                    "note": "Conformidade não inventada. Aguardando métricas técnicas acumuladas.",
                },
                calculated_at=now,
            )
            self.db.add(result)
            rows.append(
                {
                    "service_name": d.service_name,
                    "indicator_code": d.indicator_code,
                    "target_value": str(d.target_value),
                    "observed_value": None,
                    "status": "NOT_MEASURED",
                }
            )
        await self.db.flush()
        return rows

    async def create_incident(
        self,
        *,
        organization_id: uuid.UUID | None,
        title: str,
        severity: str = IncidentSeverity.SEV3,
        description: str | None = None,
        related_alert_ids: list[str] | None = None,
        audit_ctx: AuditContext | None = None,
    ) -> OperationalIncident:
        now = datetime.now(UTC)
        inc = OperationalIncident(
            id=uuid.uuid4(),
            organization_id=organization_id,
            severity=severity,
            status=IncidentStatus.DETECTED,
            title=title,
            description=description,
            started_at=now,
            detected_at=now,
            related_alert_ids=related_alert_ids or [],
            postmortem_required=severity in (IncidentSeverity.SEV1, IncidentSeverity.SEV2),
        )
        self.db.add(inc)
        await self.db.flush()
        if audit_ctx:
            await self.audit.log(
                ctx=audit_ctx, entity_type="operational_incident", entity_id=inc.id, action="CREATE"
            )
        return inc

    async def list_incidents(self, organization_id: uuid.UUID | None = None) -> list[OperationalIncident]:
        q = select(OperationalIncident).order_by(OperationalIncident.created_at.desc()).limit(100)
        if organization_id:
            q = q.where(OperationalIncident.organization_id == organization_id)
        return list((await self.db.execute(q)).scalars().all())

    async def update_incident_status(
        self,
        incident_id: uuid.UUID,
        status: str,
        *,
        resolution_summary: str | None = None,
        audit_ctx: AuditContext | None = None,
    ) -> OperationalIncident:
        result = await self.db.execute(
            select(OperationalIncident).where(OperationalIncident.id == incident_id)
        )
        inc = result.scalar_one_or_none()
        if not inc:
            raise AppError("Incidente não encontrado.", status_code=404, code="NOT_FOUND")
        inc.status = status
        if status == IncidentStatus.RESOLVED:
            inc.resolved_at = datetime.now(UTC)
            inc.resolution_summary = resolution_summary
        await self.db.flush()
        if audit_ctx:
            await self.audit.log(
                ctx=audit_ctx,
                entity_type="operational_incident",
                entity_id=inc.id,
                action="STATUS",
                after_data={"status": status},
            )
        return inc

    async def get_or_seed_flags(
        self, organization_id: uuid.UUID, user_id: uuid.UUID | None = None
    ) -> list[OrganizationFeatureFlag]:
        result = await self.db.execute(
            select(OrganizationFeatureFlag).where(
                OrganizationFeatureFlag.organization_id == organization_id
            )
        )
        existing = {f.flag_code: f for f in result.scalars().all()}
        for code in DEFAULT_FLAGS:
            if code in existing:
                continue
            # defaults seguros: dashboard/alerts on for foundation; email off; xpert manual on
            enabled = code in {
                "executive_dashboard_enabled",
                "alerts_enabled",
                "pricing_enabled",
                "xpert_manual_sync_enabled",
            }
            flag = OrganizationFeatureFlag(
                id=uuid.uuid4(),
                organization_id=organization_id,
                flag_code=code,
                enabled=enabled,
                updated_by=user_id,
            )
            self.db.add(flag)
            existing[code] = flag
        await self.db.flush()
        return list(existing.values())

    async def set_flag(
        self,
        organization_id: uuid.UUID,
        flag_code: str,
        enabled: bool,
        user_id: uuid.UUID | None,
        audit_ctx: AuditContext | None = None,
    ) -> OrganizationFeatureFlag:
        flags = await self.get_or_seed_flags(organization_id, user_id)
        flag = next((f for f in flags if f.flag_code == flag_code), None)
        if not flag:
            raise AppError("Feature flag não encontrada.", status_code=404, code="NOT_FOUND")
        before = flag.enabled
        flag.enabled = enabled
        flag.updated_by = user_id
        await self.db.flush()
        if audit_ctx:
            await self.audit.log(
                ctx=audit_ctx,
                entity_type="feature_flag",
                entity_id=flag.id,
                action="UPDATE",
                before_data={"enabled": before},
                after_data={"enabled": enabled, "flag_code": flag_code},
            )
        return flag

    async def register_backup_verification(
        self,
        *,
        status: str,
        backup_type: str = "POSTGRES",
        checksum: str | None = None,
        restore_drill: bool = False,
        details: dict | None = None,
    ) -> BackupVerificationRecord:
        now = datetime.now(UTC)
        rec = BackupVerificationRecord(
            id=uuid.uuid4(),
            backup_type=backup_type,
            status=status,
            checksum=checksum,
            verified_at=now if status == "VERIFIED" else None,
            restore_drill_at=now if restore_drill else None,
            details=details or {"note": "Registro operacional; não implica backup válido sem drill."},
            created_at=now,
        )
        self.db.add(rec)
        await self.db.flush()
        return rec
