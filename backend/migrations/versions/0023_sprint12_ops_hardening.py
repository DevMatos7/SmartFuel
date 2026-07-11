"""Sprint 12 â€” centro executivo, alertas, observabilidade e hardening."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0023_sprint12_ops_hardening"
down_revision: str | None = "0022_sprint11_pricing_decisions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "executive_metric_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("station_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("stations.id"), nullable=True),
        sa.Column("metric_code", sa.String(80), nullable=False),
        sa.Column("dimension_key", sa.String(200), nullable=False, server_default="ORG"),
        sa.Column("dimension_payload", postgresql.JSONB(), nullable=True),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reference_datetime", sa.DateTime(timezone=True), nullable=False),
        sa.Column("value_numeric", sa.Numeric(28, 10), nullable=True),
        sa.Column("value_text", sa.String(255), nullable=True),
        sa.Column("unit", sa.String(40), nullable=True),
        sa.Column("coverage_percentage", sa.Numeric(12, 8), nullable=True),
        sa.Column("quality_status", sa.String(40), nullable=False),
        sa.Column("freshness_status", sa.String(40), nullable=False),
        sa.Column("source_modules", postgresql.JSONB(), nullable=True),
        sa.Column("source_snapshot_ids", postgresql.JSONB(), nullable=True),
        sa.Column("snapshot_hash", sa.String(64), nullable=False),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint(
            "organization_id",
            "metric_code",
            "dimension_key",
            "period_start",
            "period_end",
            name="uq_executive_metric_snapshot_natural",
        ),
    )
    op.create_index("ix_exec_metrics_org", "executive_metric_snapshots", ["organization_id"])
    op.create_index("ix_exec_metrics_code", "executive_metric_snapshots", ["metric_code"])
    op.create_index("ix_exec_metrics_station", "executive_metric_snapshots", ["station_id"])
    op.create_index("ix_exec_metrics_hash", "executive_metric_snapshots", ["snapshot_hash"])

    op.create_table(
        "alert_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("station_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("stations.id"), nullable=True),
        sa.Column(
            "canonical_product_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("products.id"),
            nullable=True,
        ),
        sa.Column("code", sa.String(80), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("alert_type", sa.String(40), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("priority", sa.String(10), nullable=False, server_default="P3"),
        sa.Column("metric_code", sa.String(80), nullable=False),
        sa.Column("operator", sa.String(40), nullable=False),
        sa.Column("threshold_value", sa.Numeric(28, 10), nullable=True),
        sa.Column("threshold_payload", postgresql.JSONB(), nullable=True),
        sa.Column("evaluation_window_minutes", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("minimum_occurrences", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("cooldown_minutes", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("auto_resolve", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("assigned_role", sa.String(40), nullable=True),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_alert_rules_org", "alert_rules", ["organization_id"])
    op.create_index("ix_alert_rules_code", "alert_rules", ["code"])

    op.create_table(
        "alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("station_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("stations.id"), nullable=True),
        sa.Column(
            "canonical_product_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("products.id"),
            nullable=True,
        ),
        sa.Column(
            "distributor_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("distributors.id"),
            nullable=True,
        ),
        sa.Column("rule_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("alert_rules.id"), nullable=True),
        sa.Column("alert_code", sa.String(80), nullable=False),
        sa.Column("alert_type", sa.String(40), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("priority", sa.String(10), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("summary", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("source_module", sa.String(60), nullable=False),
        sa.Column("source_entity_type", sa.String(80), nullable=True),
        sa.Column("source_entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("metric_name", sa.String(80), nullable=True),
        sa.Column("observed_value", sa.Numeric(28, 10), nullable=True),
        sa.Column("threshold_value", sa.Numeric(28, 10), nullable=True),
        sa.Column("dimension_hash", sa.String(64), nullable=False),
        sa.Column("deduplication_key", sa.String(255), nullable=False),
        sa.Column("occurrence_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("first_detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("snoozed_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("assigned_role", sa.String(40), nullable=True),
        sa.Column("assigned_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("quality_status", sa.String(40), nullable=True),
        sa.Column("deep_link", sa.String(500), nullable=True),
        sa.Column("evidence_snapshot", postgresql.JSONB(), nullable=True),
        sa.Column("resolution_code", sa.String(40), nullable=True),
        sa.Column("resolution_note", sa.Text(), nullable=True),
        sa.Column("dismissible", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_alerts_org", "alerts", ["organization_id"])
    op.create_index("ix_alerts_code", "alerts", ["alert_code"])
    op.create_index("ix_alerts_status", "alerts", ["status"])
    op.create_index("ix_alerts_severity", "alerts", ["severity"])
    op.create_index("ix_alerts_dedup", "alerts", ["deduplication_key"])
    op.create_index("ix_alerts_station", "alerts", ["station_id"])
    op.create_index(
        "ix_alerts_active_dedup",
        "alerts",
        ["organization_id", "deduplication_key", "status"],
    )

    op.create_table(
        "alert_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "alert_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("alerts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(40), nullable=False),
        sa.Column("previous_status", sa.String(30), nullable=True),
        sa.Column("new_status", sa.String(30), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_alert_events_alert", "alert_events", ["alert_id"])

    op.create_table(
        "notification_policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("alert_type", sa.String(40), nullable=True),
        sa.Column("minimum_severity", sa.String(20), nullable=False, server_default="HIGH"),
        sa.Column("delivery_mode", sa.String(30), nullable=False, server_default="IMMEDIATE"),
        sa.Column("digest_frequency", sa.String(30), nullable=True),
        sa.Column("recipient_roles", postgresql.JSONB(), nullable=True),
        sa.Column("recipient_users", postgresql.JSONB(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_notif_policies_org", "notification_policies", ["organization_id"])

    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("alert_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("alerts.id"), nullable=True),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("recipient_type", sa.String(30), nullable=False),
        sa.Column("recipient_id", sa.String(100), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("subject", sa.String(255), nullable=False),
        sa.Column("body_snapshot", sa.Text(), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_code", sa.String(80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_notifications_org", "notifications", ["organization_id"])
    op.create_index("ix_notifications_status", "notifications", ["status"])

    op.create_table(
        "service_health_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("service_name", sa.String(80), nullable=False),
        sa.Column("component_name", sa.String(80), nullable=False),
        sa.Column("environment", sa.String(40), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("details", postgresql.JSONB(), nullable=True),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_svc_health_name", "service_health_snapshots", ["service_name"])

    op.create_table(
        "operational_slo_definitions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("service_name", sa.String(80), nullable=False),
        sa.Column("indicator_code", sa.String(80), nullable=False),
        sa.Column("target_value", sa.Numeric(16, 8), nullable=False),
        sa.Column("measurement_window", sa.String(40), nullable=False, server_default="30D"),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_slo_def_org", "operational_slo_definitions", ["organization_id"])

    op.create_table(
        "operational_slo_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "slo_definition_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("operational_slo_definitions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("observed_value", sa.Numeric(16, 8), nullable=True),
        sa.Column("target_value", sa.Numeric(16, 8), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("details", postgresql.JSONB(), nullable=True),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_slo_results_def", "operational_slo_results", ["slo_definition_id"])

    op.create_table(
        "operational_incidents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("severity", sa.String(10), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("commander_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("affected_components", postgresql.JSONB(), nullable=True),
        sa.Column("related_alert_ids", postgresql.JSONB(), nullable=True),
        sa.Column("root_cause", sa.Text(), nullable=True),
        sa.Column("resolution_summary", sa.Text(), nullable=True),
        sa.Column("postmortem_required", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_incidents_org", "operational_incidents", ["organization_id"])
    op.create_index("ix_incidents_status", "operational_incidents", ["status"])

    op.create_table(
        "domain_outbox_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.String(80), nullable=False),
        sa.Column("aggregate_type", sa.String(80), nullable=False),
        sa.Column("aggregate_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="PENDING"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_outbox_status", "domain_outbox_events", ["status"])
    op.create_index("ix_outbox_event_type", "domain_outbox_events", ["event_type"])
    op.create_index("ix_outbox_org", "domain_outbox_events", ["organization_id"])

    op.create_table(
        "organization_feature_flags",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("flag_code", sa.String(80), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("organization_id", "flag_code", name="uq_org_feature_flag"),
    )
    op.create_index("ix_feature_flags_org", "organization_feature_flags", ["organization_id"])

    op.create_table(
        "backup_verification_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("backup_type", sa.String(40), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("storage_location", sa.String(500), nullable=True),
        sa.Column("checksum", sa.String(64), nullable=True),
        sa.Column("size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("restore_drill_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("details", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("backup_verification_records")
    op.drop_table("organization_feature_flags")
    op.drop_table("domain_outbox_events")
    op.drop_table("operational_incidents")
    op.drop_table("operational_slo_results")
    op.drop_table("operational_slo_definitions")
    op.drop_table("service_health_snapshots")
    op.drop_table("notifications")
    op.drop_table("notification_policies")
    op.drop_table("alert_events")
    op.drop_table("alerts")
    op.drop_table("alert_rules")
    op.drop_table("executive_metric_snapshots")
