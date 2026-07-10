"""Sprint 5 — integração XPERT, staging e sincronização."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0009_sprint5_xpert"
down_revision: str | None = "0008_sprint41_stabilization"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "erp_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(60), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("connector_type", sa.String(50), nullable=False, server_default="XPERT_SQLSERVER"),
        sa.Column("connector_mode", sa.String(30), nullable=False, server_default="DIRECT"),
        sa.Column("host", sa.String(255), nullable=False),
        sa.Column("port", sa.Integer(), nullable=False, server_default="1433"),
        sa.Column("database_name", sa.String(150), nullable=False),
        sa.Column("driver_name", sa.String(150), nullable=False),
        sa.Column("encrypt_connection", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("trust_server_certificate", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("secret_ref", sa.String(150), nullable=False),
        sa.Column("source_timezone", sa.String(80), nullable=False, server_default="America/Cuiaba"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("connection_status", sa.String(30), nullable=False, server_default="UNKNOWN"),
        sa.Column("last_tested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_test_result", postgresql.JSONB(), nullable=True),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("port >= 1 AND port <= 65535", name="ck_erp_sources_port_range"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"]),
        sa.UniqueConstraint("organization_id", "code", name="uq_erp_sources_org_code"),
    )
    op.create_index("ix_erp_sources_organization_id", "erp_sources", ["organization_id"])

    op.create_table(
        "erp_datasets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("erp_source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(60), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("query_file", sa.String(255), nullable=False),
        sa.Column("query_hash", sa.String(64), nullable=True),
        sa.Column("sync_mode", sa.String(40), nullable=False, server_default="FULL_SNAPSHOT_HASH"),
        sa.Column("checkpoint_type", sa.String(40), nullable=False, server_default="NONE"),
        sa.Column("source_timezone", sa.String(80), nullable=True),
        sa.Column("overlap_seconds", sa.Integer(), nullable=False, server_default="300"),
        sa.Column("batch_size", sa.Integer(), nullable=False, server_default="1000"),
        sa.Column("strict_mode", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("allow_partial_checkpoint", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("schedule_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("schedule_interval_minutes", sa.Integer(), nullable=True),
        sa.Column("next_scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("contract_status", sa.String(30), nullable=False, server_default="PENDING"),
        sa.Column("contract_result", postgresql.JSONB(), nullable=True),
        sa.Column("last_contract_validation_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("overlap_seconds >= 0", name="ck_erp_datasets_overlap_nonneg"),
        sa.CheckConstraint("batch_size > 0", name="ck_erp_datasets_batch_positive"),
        sa.ForeignKeyConstraint(["erp_source_id"], ["erp_sources.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("erp_source_id", "code", name="uq_erp_datasets_source_code"),
    )
    op.create_index("ix_erp_datasets_erp_source_id", "erp_datasets", ["erp_source_id"])
    op.create_index("ix_erp_datasets_next_scheduled_at", "erp_datasets", ["next_scheduled_at"])

    op.create_table(
        "erp_sync_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("erp_source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("erp_dataset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("station_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("trigger_type", sa.String(30), nullable=False),
        sa.Column("sync_mode", sa.String(40), nullable=False),
        sa.Column("status", sa.String(40), nullable=False, server_default="QUEUED"),
        sa.Column("checkpoint_before", sa.String(255), nullable=True),
        sa.Column("checkpoint_after", sa.String(255), nullable=True),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_upper_bound", sa.DateTime(timezone=True), nullable=True),
        sa.Column("query_hash", sa.String(64), nullable=True),
        sa.Column("worker_id", sa.String(150), nullable=True),
        sa.Column("rows_read", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rows_staged", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rows_valid", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rows_applied", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rows_inserted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rows_updated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rows_unchanged", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rows_quarantined", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rows_error", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rows_marked_inactive", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("current_batch", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_batches", sa.Integer(), nullable=True),
        sa.Column("error_code", sa.String(100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("error_details", postgresql.JSONB(), nullable=True),
        sa.Column("cancellation_requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retried_from_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("requested_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["erp_source_id"], ["erp_sources.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["erp_dataset_id"], ["erp_datasets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["station_id"], ["stations.id"]),
        sa.ForeignKeyConstraint(["requested_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["retried_from_run_id"], ["erp_sync_runs.id"]),
    )
    op.create_index("ix_erp_sync_runs_status", "erp_sync_runs", ["status"])
    op.create_index("ix_erp_sync_runs_created_at", "erp_sync_runs", ["created_at"])
    op.create_index("ix_erp_sync_runs_erp_dataset_id", "erp_sync_runs", ["erp_dataset_id"])
    op.create_index("ix_erp_sync_runs_station_id", "erp_sync_runs", ["station_id"])

    op.create_table(
        "erp_sync_checkpoints",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("erp_source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("erp_dataset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("station_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("checkpoint_type", sa.String(40), nullable=False, server_default="NONE"),
        sa.Column("watermark_value", sa.String(255), nullable=True),
        sa.Column("source_upper_bound", sa.String(255), nullable=True),
        sa.Column("last_success_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["erp_source_id"], ["erp_sources.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["erp_dataset_id"], ["erp_datasets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["station_id"], ["stations.id"]),
        sa.ForeignKeyConstraint(["last_success_run_id"], ["erp_sync_runs.id"]),
        sa.UniqueConstraint(
            "erp_source_id",
            "erp_dataset_id",
            "station_id",
            name="uq_erp_sync_checkpoints_source_dataset_station",
        ),
    )
    op.create_index("ix_erp_sync_checkpoints_erp_dataset_id", "erp_sync_checkpoints", ["erp_dataset_id"])
    op.create_index("ix_erp_sync_checkpoints_station_id", "erp_sync_checkpoints", ["station_id"])

    op.create_table(
        "erp_staging_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("sync_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("station_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("dataset_code", sa.String(60), nullable=False),
        sa.Column("source_key", sa.String(255), nullable=False),
        sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_active", sa.Boolean(), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=False),
        sa.Column("normalized_payload", postgresql.JSONB(), nullable=True),
        sa.Column("record_hash", sa.String(64), nullable=True),
        sa.Column("processing_status", sa.String(40), nullable=False, server_default="RECEIVED"),
        sa.Column("validation_errors", postgresql.JSONB(), nullable=True),
        sa.Column("applied_entity_type", sa.String(80), nullable=True),
        sa.Column("applied_entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["sync_run_id"], ["erp_sync_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["station_id"], ["stations.id"]),
        sa.UniqueConstraint("sync_run_id", "source_key", name="uq_erp_staging_records_run_source_key"),
    )
    op.create_index("ix_erp_staging_records_sync_run_id", "erp_staging_records", ["sync_run_id"])
    op.create_index("ix_erp_staging_records_processing_status", "erp_staging_records", ["processing_status"])
    op.create_index("ix_erp_staging_records_record_hash", "erp_staging_records", ["record_hash"])

    op.create_table(
        "erp_sync_errors",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("sync_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("staging_record_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("phase", sa.String(40), nullable=False),
        sa.Column("error_code", sa.String(100), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("field_name", sa.String(150), nullable=True),
        sa.Column("source_key", sa.String(255), nullable=True),
        sa.Column("details", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["sync_run_id"], ["erp_sync_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["staging_record_id"], ["erp_staging_records.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_erp_sync_errors_sync_run_id", "erp_sync_errors", ["sync_run_id"])
    op.create_index("ix_erp_sync_errors_error_code", "erp_sync_errors", ["error_code"])

    for table in ("erp_products", "erp_suppliers"):
        op.add_column(table, sa.Column("source_system", sa.String(50), nullable=True))
        op.add_column(table, sa.Column("source_record_hash", sa.String(64), nullable=True))
        op.add_column(table, sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=True))
        op.add_column(table, sa.Column("source_last_seen_at", sa.DateTime(timezone=True), nullable=True))
        op.add_column(table, sa.Column("source_active", sa.Boolean(), nullable=True))
        op.add_column(table, sa.Column("last_sync_run_id", postgresql.UUID(as_uuid=True), nullable=True))
        op.create_foreign_key(
            f"fk_{table}_last_sync_run_id",
            table,
            "erp_sync_runs",
            ["last_sync_run_id"],
            ["id"],
        )

    op.add_column("erp_suppliers", sa.Column("mapping_source", sa.String(30), nullable=True))


def downgrade() -> None:
    op.drop_column("erp_suppliers", "mapping_source")
    for table in ("erp_products", "erp_suppliers"):
        op.drop_constraint(f"fk_{table}_last_sync_run_id", table, type_="foreignkey")
        op.drop_column(table, "last_sync_run_id")
        op.drop_column(table, "source_active")
        op.drop_column(table, "source_last_seen_at")
        op.drop_column(table, "source_updated_at")
        op.drop_column(table, "source_record_hash")
        op.drop_column(table, "source_system")

    op.drop_table("erp_sync_errors")
    op.drop_table("erp_staging_records")
    op.drop_table("erp_sync_checkpoints")
    op.drop_table("erp_sync_runs")
    op.drop_table("erp_datasets")
    op.drop_table("erp_sources")
