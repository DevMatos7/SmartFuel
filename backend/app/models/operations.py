"""Models Sprint 12 — dashboard executivo, alertas, ops e outbox."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class ExecutiveMetricSnapshot(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "executive_metric_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "metric_code",
            "dimension_key",
            "period_start",
            "period_end",
            name="uq_executive_metric_snapshot_natural",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    station_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stations.id"), nullable=True, index=True
    )
    metric_code: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    dimension_key: Mapped[str] = mapped_column(String(200), nullable=False, default="ORG")
    dimension_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reference_datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    value_numeric: Mapped[Decimal | None] = mapped_column(Numeric(28, 10), nullable=True)
    value_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(40), nullable=True)
    coverage_percentage: Mapped[Decimal | None] = mapped_column(Numeric(12, 8), nullable=True)
    quality_status: Mapped[str] = mapped_column(String(40), nullable=False)
    freshness_status: Mapped[str] = mapped_column(String(40), nullable=False)
    source_modules: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    source_snapshot_ids: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AlertRule(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "alert_rules"

    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    station_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stations.id"), nullable=True, index=True
    )
    canonical_product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id"), nullable=True, index=True
    )
    code: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    alert_type: Mapped[str] = mapped_column(String(40), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    priority: Mapped[str] = mapped_column(String(10), nullable=False, default="P3")
    metric_code: Mapped[str] = mapped_column(String(80), nullable=False)
    operator: Mapped[str] = mapped_column(String(40), nullable=False)
    threshold_value: Mapped[Decimal | None] = mapped_column(Numeric(28, 10), nullable=True)
    threshold_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    evaluation_window_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    minimum_occurrences: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    cooldown_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    auto_resolve: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    assigned_role: Mapped[str | None] = mapped_column(String(40), nullable=True)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )


class Alert(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "alerts"

    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    station_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stations.id"), nullable=True, index=True
    )
    canonical_product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id"), nullable=True, index=True
    )
    distributor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("distributors.id"), nullable=True, index=True
    )
    rule_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("alert_rules.id"), nullable=True, index=True
    )
    alert_code: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    alert_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    priority: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_module: Mapped[str] = mapped_column(String(60), nullable=False)
    source_entity_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    source_entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    metric_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    observed_value: Mapped[Decimal | None] = mapped_column(Numeric(28, 10), nullable=True)
    threshold_value: Mapped[Decimal | None] = mapped_column(Numeric(28, 10), nullable=True)
    dimension_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    deduplication_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    occurrence_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    first_detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    snoozed_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    assigned_role: Mapped[str | None] = mapped_column(String(40), nullable=True)
    assigned_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    quality_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    deep_link: Mapped[str | None] = mapped_column(String(500), nullable=True)
    evidence_snapshot: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    resolution_code: Mapped[str | None] = mapped_column(String(40), nullable=True)
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    dismissible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class AlertEvent(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "alert_events"

    alert_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    previous_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    new_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    event_metadata: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class NotificationPolicy(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "notification_policies"

    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    alert_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    minimum_severity: Mapped[str] = mapped_column(String(20), nullable=False, default="HIGH")
    delivery_mode: Mapped[str] = mapped_column(String(30), nullable=False, default="IMMEDIATE")
    digest_frequency: Mapped[str | None] = mapped_column(String(30), nullable=True)
    recipient_roles: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    recipient_users: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )


class Notification(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "notifications"

    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    alert_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("alerts.id"), nullable=True, index=True
    )
    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    recipient_type: Mapped[str] = mapped_column(String(30), nullable=False)
    recipient_id: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    body_snapshot: Mapped[str] = mapped_column(Text, nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ServiceHealthSnapshot(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "service_health_snapshots"

    service_name: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    component_name: Mapped[str] = mapped_column(String(80), nullable=False)
    environment: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class OperationalSloDefinition(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "operational_slo_definitions"

    organization_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    service_name: Mapped[str] = mapped_column(String(80), nullable=False)
    indicator_code: Mapped[str] = mapped_column(String(80), nullable=False)
    target_value: Mapped[Decimal] = mapped_column(Numeric(16, 8), nullable=False)
    measurement_window: Mapped[str] = mapped_column(String(40), nullable=False, default="30D")
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class OperationalSloResult(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "operational_slo_results"

    slo_definition_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("operational_slo_definitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    observed_value: Mapped[Decimal | None] = mapped_column(Numeric(16, 8), nullable=True)
    target_value: Mapped[Decimal] = mapped_column(Numeric(16, 8), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class OperationalIncident(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "operational_incidents"

    organization_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    severity: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    commander_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    affected_components: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    related_alert_ids: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    root_cause: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolution_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    postmortem_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class DomainOutboxEvent(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "domain_outbox_events"

    organization_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    aggregate_type: Mapped[str] = mapped_column(String(80), nullable=False)
    aggregate_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, index=True, default="PENDING")
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class OrganizationFeatureFlag(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "organization_feature_flags"
    __table_args__ = (
        UniqueConstraint("organization_id", "flag_code", name="uq_org_feature_flag"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    flag_code: Mapped[str] = mapped_column(String(80), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )


class BackupVerificationRecord(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "backup_verification_records"

    organization_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    backup_type: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    storage_location: Mapped[str | None] = mapped_column(String(500), nullable=True)
    checksum: Mapped[str | None] = mapped_column(String(64), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    restore_drill_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
