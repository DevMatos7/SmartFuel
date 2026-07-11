"""Sprint 12 — motor de alertas com deduplicação e lifecycle."""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.core.operations_enums import (
    AlertCode,
    AlertSeverity,
    AlertStatus,
    AlertType,
    NotificationChannel,
    NotificationStatus,
    ResolutionCode,
)
from app.models.operations import (
    Alert,
    AlertEvent,
    AlertRule,
    DomainOutboxEvent,
    Notification,
)
from app.services.audit_service import AuditContext, AuditService

ACTIVE_STATUSES = {
    AlertStatus.OPEN,
    AlertStatus.ACKNOWLEDGED,
    AlertStatus.ASSIGNED,
    AlertStatus.IN_PROGRESS,
    AlertStatus.SNOOZED,
}


def _dec(v: Any) -> Decimal | None:
    if v is None:
        return None
    if isinstance(v, Decimal):
        return v
    return Decimal(str(v))


def _severity_to_priority(severity: str) -> str:
    return {
        AlertSeverity.CRITICAL: "P1",
        AlertSeverity.HIGH: "P2",
        AlertSeverity.WARNING: "P3",
        AlertSeverity.INFO: "P4",
    }.get(severity, "P3")


def build_dedup_key(
    *,
    organization_id: uuid.UUID,
    station_id: uuid.UUID | None,
    alert_code: str,
    source_entity_type: str | None,
    source_entity_id: uuid.UUID | None,
    dimension_payload: dict | None = None,
) -> tuple[str, str]:
    raw = "|".join(
        [
            str(organization_id),
            str(station_id or ""),
            alert_code,
            source_entity_type or "",
            str(source_entity_id or ""),
            str(sorted((dimension_payload or {}).items())),
        ]
    )
    digest = hashlib.sha256(raw.encode()).hexdigest()
    return digest, digest[:64]


def evaluate_condition(
    operator: str,
    observed: Decimal | None,
    threshold: Decimal | None,
    *,
    status_value: str | None = None,
    status_list: list[str] | None = None,
) -> bool:
    if operator == "MISSING":
        return observed is None
    if operator == "STALE":
        return status_value == "STALE"
    if operator == "STATUS_IN":
        return bool(status_list and status_value in status_list)
    if observed is None or threshold is None:
        return False
    if operator == "GT":
        return observed > threshold
    if operator == "GTE":
        return observed >= threshold
    if operator == "LT":
        return observed < threshold
    if operator == "LTE":
        return observed <= threshold
    if operator == "EQ":
        return observed == threshold
    if operator == "NE":
        return observed != threshold
    return False


class AlertEngineService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.audit = AuditService(db)

    async def create_rule(
        self,
        *,
        organization_id: uuid.UUID,
        user_id: uuid.UUID | None,
        data: dict[str, Any],
        audit_ctx: AuditContext | None = None,
    ) -> AlertRule:
        rule = AlertRule(
            id=uuid.uuid4(),
            organization_id=organization_id,
            station_id=data.get("station_id"),
            canonical_product_id=data.get("canonical_product_id"),
            code=data["code"],
            name=data["name"],
            description=data.get("description"),
            alert_type=data.get("alert_type", AlertType.BUSINESS),
            severity=data.get("severity", AlertSeverity.WARNING),
            priority=data.get("priority") or _severity_to_priority(data.get("severity", "WARNING")),
            metric_code=data["metric_code"],
            operator=data["operator"],
            threshold_value=_dec(data.get("threshold_value")),
            threshold_payload=data.get("threshold_payload"),
            evaluation_window_minutes=int(data.get("evaluation_window_minutes", 60)),
            minimum_occurrences=int(data.get("minimum_occurrences", 1)),
            cooldown_minutes=int(data.get("cooldown_minutes", 30)),
            auto_resolve=bool(data.get("auto_resolve", True)),
            assigned_role=data.get("assigned_role"),
            valid_from=data.get("valid_from") or datetime.now(UTC),
            valid_until=data.get("valid_until"),
            active=True,
            created_by=user_id,
        )
        self.db.add(rule)
        await self.db.flush()
        if audit_ctx:
            await self.audit.log(
                ctx=audit_ctx,
                entity_type="alert_rule",
                entity_id=rule.id,
                action="CREATE",
                after_data={"code": rule.code},
            )
        return rule

    async def list_rules(self, organization_id: uuid.UUID) -> list[AlertRule]:
        result = await self.db.execute(
            select(AlertRule)
            .where(AlertRule.organization_id == organization_id)
            .order_by(AlertRule.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_rule(self, rule_id: uuid.UUID, organization_id: uuid.UUID) -> AlertRule:
        result = await self.db.execute(
            select(AlertRule).where(
                AlertRule.id == rule_id, AlertRule.organization_id == organization_id
            )
        )
        rule = result.scalar_one_or_none()
        if not rule:
            raise AppError("Regra não encontrada.", status_code=404, code="NOT_FOUND")
        return rule

    async def deactivate_rule(
        self, rule_id: uuid.UUID, organization_id: uuid.UUID, audit_ctx: AuditContext | None = None
    ) -> AlertRule:
        rule = await self.get_rule(rule_id, organization_id)
        rule.active = False
        rule.valid_until = datetime.now(UTC)
        await self.db.flush()
        if audit_ctx:
            await self.audit.log(
                ctx=audit_ctx, entity_type="alert_rule", entity_id=rule.id, action="DEACTIVATE"
            )
        return rule

    async def upsert_alert(
        self,
        *,
        organization_id: uuid.UUID,
        alert_code: str,
        title: str,
        summary: str,
        description: str | None = None,
        alert_type: str = AlertType.BUSINESS,
        severity: str = AlertSeverity.WARNING,
        station_id: uuid.UUID | None = None,
        product_id: uuid.UUID | None = None,
        distributor_id: uuid.UUID | None = None,
        rule_id: uuid.UUID | None = None,
        source_module: str = "operations",
        source_entity_type: str | None = None,
        source_entity_id: uuid.UUID | None = None,
        metric_name: str | None = None,
        observed_value: Decimal | None = None,
        threshold_value: Decimal | None = None,
        quality_status: str | None = None,
        deep_link: str | None = None,
        evidence: dict | None = None,
        dismissible: bool = True,
        assigned_role: str | None = None,
        audit_ctx: AuditContext | None = None,
    ) -> Alert:
        now = datetime.now(UTC)
        dedup, dim_hash = build_dedup_key(
            organization_id=organization_id,
            station_id=station_id,
            alert_code=alert_code,
            source_entity_type=source_entity_type,
            source_entity_id=source_entity_id,
            dimension_payload=evidence,
        )
        result = await self.db.execute(
            select(Alert).where(
                Alert.organization_id == organization_id,
                Alert.deduplication_key == dedup,
                Alert.status.in_(list(ACTIVE_STATUSES)),
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.last_detected_at = now
            existing.occurrence_count += 1
            existing.observed_value = observed_value
            existing.evidence_snapshot = evidence
            existing.summary = summary
            await self.db.flush()
            await self._add_event(
                existing.id,
                "REDETECTED",
                previous_status=existing.status,
                new_status=existing.status,
                comment=f"occurrence={existing.occurrence_count}",
            )
            return existing

        alert = Alert(
            id=uuid.uuid4(),
            organization_id=organization_id,
            station_id=station_id,
            canonical_product_id=product_id,
            distributor_id=distributor_id,
            rule_id=rule_id,
            alert_code=alert_code,
            alert_type=alert_type,
            severity=severity,
            priority=_severity_to_priority(severity),
            status=AlertStatus.OPEN,
            title=title,
            summary=summary,
            description=description,
            source_module=source_module,
            source_entity_type=source_entity_type,
            source_entity_id=source_entity_id,
            metric_name=metric_name,
            observed_value=observed_value,
            threshold_value=threshold_value,
            dimension_hash=dim_hash,
            deduplication_key=dedup,
            occurrence_count=1,
            first_detected_at=now,
            last_detected_at=now,
            assigned_role=assigned_role,
            quality_status=quality_status,
            deep_link=deep_link,
            evidence_snapshot=evidence,
            dismissible=dismissible,
        )
        self.db.add(alert)
        await self.db.flush()
        await self._add_event(alert.id, "OPENED", new_status=AlertStatus.OPEN)
        await self._notify_in_app(alert)
        await self._enqueue_outbox(alert)
        if audit_ctx:
            await self.audit.log(
                ctx=audit_ctx,
                entity_type="alert",
                entity_id=alert.id,
                action="OPEN",
                after_data={"alert_code": alert_code, "severity": severity},
            )
        return alert

    async def ensure_unsafe_xpert_alert(
        self, organization_id: uuid.UUID, details: dict | None = None
    ) -> Alert:
        return await self.upsert_alert(
            organization_id=organization_id,
            alert_code=AlertCode.UNSAFE_XPERT_SOURCE,
            title="Fonte XPERT UNSAFE (usuário privilegiado)",
            summary="Fonte XPERT com usuário sa. Produção e agenda bloqueadas.",
            description=(
                "A fonte XPERT permanece UNSAFE. Não habilitar scheduler. "
                "Não liberar produção até migração para conta somente leitura."
            ),
            alert_type=AlertType.SECURITY,
            severity=AlertSeverity.CRITICAL,
            source_module="xpert",
            source_entity_type="erp_source",
            deep_link="/integrations/xpert",
            evidence=details or {"security_status": "UNSAFE", "user": "sa"},
            dismissible=False,
            assigned_role="ADMIN",
        )

    async def evaluate_rule(
        self,
        *,
        rule: AlertRule,
        observed_value: Decimal | None,
        status_value: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> Alert | None:
        ctx = context or {}
        matched = evaluate_condition(
            rule.operator,
            observed_value,
            rule.threshold_value,
            status_value=status_value,
            status_list=(rule.threshold_payload or {}).get("statuses"),
        )
        if not matched:
            if rule.auto_resolve:
                await self._auto_resolve_by_rule(rule)
            return None
        return await self.upsert_alert(
            organization_id=rule.organization_id,
            alert_code=rule.code,
            title=rule.name,
            summary=f"{rule.metric_code} {rule.operator} {rule.threshold_value}",
            description=rule.description,
            alert_type=rule.alert_type,
            severity=rule.severity,
            station_id=rule.station_id or ctx.get("station_id"),
            product_id=rule.canonical_product_id or ctx.get("canonical_product_id"),
            rule_id=rule.id,
            source_module=ctx.get("source_module", "rules"),
            source_entity_type=ctx.get("source_entity_type"),
            source_entity_id=ctx.get("source_entity_id"),
            metric_name=rule.metric_code,
            observed_value=observed_value,
            threshold_value=rule.threshold_value,
            deep_link=ctx.get("deep_link"),
            evidence=ctx.get("evidence"),
            assigned_role=rule.assigned_role,
        )

    async def _auto_resolve_by_rule(self, rule: AlertRule) -> None:
        result = await self.db.execute(
            select(Alert).where(
                Alert.organization_id == rule.organization_id,
                Alert.rule_id == rule.id,
                Alert.status.in_(list(ACTIVE_STATUSES)),
            )
        )
        for alert in result.scalars().all():
            if alert.alert_code == AlertCode.UNSAFE_XPERT_SOURCE and not alert.dismissible:
                continue
            await self.resolve_alert(
                alert.id,
                alert.organization_id,
                user_id=None,
                resolution_code=ResolutionCode.FIXED,
                note="Auto-resolve: condição deixou de existir",
            )

    async def list_alerts(
        self,
        organization_id: uuid.UUID,
        *,
        status: str | None = None,
        severity: str | None = None,
        station_id: uuid.UUID | None = None,
    ) -> list[Alert]:
        q = select(Alert).where(Alert.organization_id == organization_id)
        if status:
            q = q.where(Alert.status == status)
        if severity:
            q = q.where(Alert.severity == severity)
        if station_id:
            q = q.where(Alert.station_id == station_id)
        q = q.order_by(Alert.last_detected_at.desc()).limit(200)
        return list((await self.db.execute(q)).scalars().all())

    async def get_alert(self, alert_id: uuid.UUID, organization_id: uuid.UUID) -> Alert:
        result = await self.db.execute(
            select(Alert).where(Alert.id == alert_id, Alert.organization_id == organization_id)
        )
        alert = result.scalar_one_or_none()
        if not alert:
            raise AppError("Alerta não encontrado.", status_code=404, code="NOT_FOUND")
        return alert

    async def acknowledge(
        self,
        alert_id: uuid.UUID,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        comment: str | None = None,
        audit_ctx: AuditContext | None = None,
    ) -> Alert:
        alert = await self.get_alert(alert_id, organization_id)
        prev = alert.status
        alert.status = AlertStatus.ACKNOWLEDGED
        alert.acknowledged_at = datetime.now(UTC)
        await self.db.flush()
        await self._add_event(
            alert.id, "ACKNOWLEDGE", previous_status=prev, new_status=alert.status, comment=comment, user_id=user_id
        )
        if audit_ctx:
            await self.audit.log(
                ctx=audit_ctx, entity_type="alert", entity_id=alert.id, action="ACKNOWLEDGE"
            )
        return alert

    async def assign(
        self,
        alert_id: uuid.UUID,
        organization_id: uuid.UUID,
        *,
        assigned_user_id: uuid.UUID | None,
        assigned_role: str | None = None,
        user_id: uuid.UUID | None = None,
        audit_ctx: AuditContext | None = None,
    ) -> Alert:
        alert = await self.get_alert(alert_id, organization_id)
        prev = alert.status
        alert.assigned_user_id = assigned_user_id
        alert.assigned_role = assigned_role
        alert.status = AlertStatus.ASSIGNED
        await self.db.flush()
        await self._add_event(
            alert.id,
            "ASSIGN",
            previous_status=prev,
            new_status=alert.status,
            comment=f"user={assigned_user_id} role={assigned_role}",
            user_id=user_id,
        )
        if audit_ctx:
            await self.audit.log(ctx=audit_ctx, entity_type="alert", entity_id=alert.id, action="ASSIGN")
        return alert

    async def snooze(
        self,
        alert_id: uuid.UUID,
        organization_id: uuid.UUID,
        *,
        minutes: int,
        user_id: uuid.UUID | None = None,
        audit_ctx: AuditContext | None = None,
    ) -> Alert:
        alert = await self.get_alert(alert_id, organization_id)
        prev = alert.status
        alert.status = AlertStatus.SNOOZED
        alert.snoozed_until = datetime.now(UTC) + timedelta(minutes=minutes)
        await self.db.flush()
        await self._add_event(
            alert.id,
            "SNOOZE",
            previous_status=prev,
            new_status=alert.status,
            comment=f"minutes={minutes}",
            user_id=user_id,
        )
        if audit_ctx:
            await self.audit.log(ctx=audit_ctx, entity_type="alert", entity_id=alert.id, action="SNOOZE")
        return alert

    async def resolve_alert(
        self,
        alert_id: uuid.UUID,
        organization_id: uuid.UUID,
        *,
        user_id: uuid.UUID | None,
        resolution_code: str,
        note: str | None = None,
        audit_ctx: AuditContext | None = None,
    ) -> Alert:
        alert = await self.get_alert(alert_id, organization_id)
        if not alert.dismissible and alert.alert_code == AlertCode.UNSAFE_XPERT_SOURCE:
            raise AppError(
                "Alerta UNSAFE_XPERT_SOURCE não pode ser resolvido enquanto a fonte usar sa.",
                status_code=400,
                code="ALERT_NOT_DISMISSIBLE",
            )
        prev = alert.status
        alert.status = AlertStatus.RESOLVED
        alert.resolved_at = datetime.now(UTC)
        alert.resolution_code = resolution_code
        alert.resolution_note = note
        await self.db.flush()
        await self._add_event(
            alert.id,
            "RESOLVE",
            previous_status=prev,
            new_status=alert.status,
            comment=note,
            user_id=user_id,
        )
        if audit_ctx:
            await self.audit.log(ctx=audit_ctx, entity_type="alert", entity_id=alert.id, action="RESOLVE")
        return alert

    async def reopen(
        self,
        alert_id: uuid.UUID,
        organization_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
        comment: str | None = None,
        audit_ctx: AuditContext | None = None,
    ) -> Alert:
        alert = await self.get_alert(alert_id, organization_id)
        if alert.status not in (AlertStatus.RESOLVED, AlertStatus.DISMISSED, AlertStatus.EXPIRED):
            raise AppError("Somente alertas encerrados podem ser reabertos.", status_code=400, code="INVALID_STATUS")
        prev = alert.status
        alert.status = AlertStatus.OPEN
        alert.resolved_at = None
        alert.resolution_code = None
        await self.db.flush()
        await self._add_event(
            alert.id, "REOPEN", previous_status=prev, new_status=alert.status, comment=comment, user_id=user_id
        )
        if audit_ctx:
            await self.audit.log(ctx=audit_ctx, entity_type="alert", entity_id=alert.id, action="REOPEN")
        return alert

    async def comment(
        self,
        alert_id: uuid.UUID,
        organization_id: uuid.UUID,
        user_id: uuid.UUID | None,
        comment: str,
    ) -> AlertEvent:
        await self.get_alert(alert_id, organization_id)
        return await self._add_event(alert_id, "COMMENT", comment=comment, user_id=user_id)

    async def summary_cards(self, organization_id: uuid.UUID) -> dict[str, Any]:
        alerts = await self.list_alerts(organization_id)
        now = datetime.now(UTC)
        return {
            "critical": sum(1 for a in alerts if a.severity == AlertSeverity.CRITICAL and a.status in ACTIVE_STATUSES),
            "high": sum(1 for a in alerts if a.severity == AlertSeverity.HIGH and a.status in ACTIVE_STATUSES),
            "unacknowledged": sum(1 for a in alerts if a.status == AlertStatus.OPEN),
            "overdue": sum(
                1 for a in alerts if a.due_at and a.due_at < now and a.status in ACTIVE_STATUSES
            ),
            "assigned_open": sum(1 for a in alerts if a.status == AlertStatus.ASSIGNED),
            "resolved_today": sum(
                1
                for a in alerts
                if a.status == AlertStatus.RESOLVED
                and a.resolved_at
                and a.resolved_at.date() == now.date()
            ),
            "recurring": sum(1 for a in alerts if a.occurrence_count > 1 and a.status in ACTIVE_STATUSES),
        }

    async def create_synthetic_alerts(
        self, organization_id: uuid.UUID, station_id: uuid.UUID | None = None
    ) -> list[dict[str, Any]]:
        scenarios = [
            {
                "alert_code": AlertCode.NEGATIVE_GROSS_MARGIN,
                "title": "Margem bruta comercial negativa",
                "summary": "Produto com margem/L < 0 (estimativa comercial).",
                "severity": AlertSeverity.HIGH,
                "alert_type": AlertType.FINANCIAL,
                "observed": Decimal("-0.05"),
                "threshold": Decimal("0"),
                "deep_link": "/pricing",
            },
            {
                "alert_code": AlertCode.SYNC_FAILED,
                "title": "Sincronização XPERT falhou",
                "summary": "Run de sync com status FAILED.",
                "severity": AlertSeverity.HIGH,
                "alert_type": AlertType.INTEGRATION,
                "deep_link": "/integrations/xpert",
            },
            {
                "alert_code": AlertCode.MISSING_MAPPING,
                "title": "Produto sem mapeamento",
                "summary": "Item de compra sem produto canônico.",
                "severity": AlertSeverity.WARNING,
                "alert_type": AlertType.DATA_QUALITY,
                "deep_link": "/erp-products",
            },
            {
                "alert_code": AlertCode.APPROVED_PRICE_NOT_IMPLEMENTED,
                "title": "Preço aprovado não implantado",
                "summary": "Decisão aprovada aguardando implantação externa.",
                "severity": AlertSeverity.WARNING,
                "alert_type": AlertType.WORKFLOW,
                "deep_link": "/pricing/implementations",
            },
            {
                "alert_code": AlertCode.IMPLEMENTED_PRICE_DIFFERENT,
                "title": "Implantação divergente",
                "summary": "Preço implantado difere do aprovado.",
                "severity": AlertSeverity.HIGH,
                "alert_type": AlertType.WORKFLOW,
                "deep_link": "/pricing/implementations",
            },
        ]
        created = []
        unsafe = await self.ensure_unsafe_xpert_alert(organization_id)
        created.append({"id": str(unsafe.id), "alert_code": unsafe.alert_code})
        for sc in scenarios:
            alert = await self.upsert_alert(
                organization_id=organization_id,
                station_id=station_id,
                alert_code=sc["alert_code"],
                title=sc["title"],
                summary=sc["summary"],
                severity=sc["severity"],
                alert_type=sc["alert_type"],
                source_module="synthetic",
                observed_value=sc.get("observed"),
                threshold_value=sc.get("threshold"),
                deep_link=sc.get("deep_link"),
                evidence={"synthetic": True},
            )
            created.append({"id": str(alert.id), "alert_code": alert.alert_code})
        return created

    async def _add_event(
        self,
        alert_id: uuid.UUID,
        event_type: str,
        *,
        previous_status: str | None = None,
        new_status: str | None = None,
        comment: str | None = None,
        user_id: uuid.UUID | None = None,
        metadata: dict | None = None,
    ) -> AlertEvent:
        ev = AlertEvent(
            id=uuid.uuid4(),
            alert_id=alert_id,
            event_type=event_type,
            previous_status=previous_status,
            new_status=new_status,
            comment=comment,
            event_metadata=metadata,
            created_by=user_id,
            created_at=datetime.now(UTC),
        )
        self.db.add(ev)
        await self.db.flush()
        return ev

    async def _notify_in_app(self, alert: Alert) -> Notification:
        n = Notification(
            id=uuid.uuid4(),
            organization_id=alert.organization_id,
            alert_id=alert.id,
            channel=NotificationChannel.IN_APP,
            recipient_type="ROLE",
            recipient_id=alert.assigned_role or "GESTOR",
            status=NotificationStatus.SENT,
            subject=alert.title,
            body_snapshot=alert.summary,
            attempt_count=1,
            last_attempt_at=datetime.now(UTC),
            sent_at=datetime.now(UTC),
            created_at=datetime.now(UTC),
        )
        self.db.add(n)
        await self.db.flush()
        return n

    async def _enqueue_outbox(self, alert: Alert) -> DomainOutboxEvent:
        ev = DomainOutboxEvent(
            id=uuid.uuid4(),
            organization_id=alert.organization_id,
            event_type="ALERT_OPENED",
            aggregate_type="alert",
            aggregate_id=alert.id,
            payload={
                "alert_code": alert.alert_code,
                "severity": alert.severity,
                "organization_id": str(alert.organization_id),
            },
            status="PENDING",
            attempt_count=0,
            available_at=datetime.now(UTC),
            created_at=datetime.now(UTC),
        )
        self.db.add(ev)
        await self.db.flush()
        return ev
