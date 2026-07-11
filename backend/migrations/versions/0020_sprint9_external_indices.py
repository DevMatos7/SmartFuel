"""Sprint 9 — índices externos e séries de mercado."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0020_sprint9_external_indices"
down_revision: str | None = "0019_sprint83_quote_origin"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "external_data_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("code", sa.String(80), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("source_type", sa.String(40), nullable=False),
        sa.Column("status", sa.String(40), nullable=False, server_default="MISCONFIGURED"),
        sa.Column("base_url", sa.String(500), nullable=True),
        sa.Column("secret_ref", sa.String(200), nullable=True),
        sa.Column("requires_credentials", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("supports_scheduling", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("scheduler_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("terms_review_status", sa.String(40), nullable=False, server_default="PENDING"),
        sa.Column("connector_status", sa.String(40), nullable=False, server_default="MISCONFIGURED"),
        sa.Column("capabilities", postgresql.JSONB(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_failure_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_test_result", postgresql.JSONB(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("organization_id", "code", name="uq_external_data_sources_org_code"),
    )
    op.create_index("ix_external_data_sources_organization_id", "external_data_sources", ["organization_id"])
    op.create_index("ix_external_data_sources_code", "external_data_sources", ["code"])
    op.create_index("ix_external_data_sources_status", "external_data_sources", ["status"])

    op.create_table(
        "external_series",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "source_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("external_data_sources.id"),
            nullable=False,
        ),
        sa.Column("code", sa.String(80), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("frequency", sa.String(30), nullable=False),
        sa.Column("source_unit", sa.String(40), nullable=False),
        sa.Column("canonical_unit", sa.String(40), nullable=False),
        sa.Column("currency", sa.String(10), nullable=True),
        sa.Column("timezone", sa.String(64), nullable=False, server_default="UTC"),
        sa.Column("calendar_type", sa.String(40), nullable=False, server_default="CALENDAR_DAYS"),
        sa.Column("freshness_grace_minutes", sa.Integer(), nullable=False, server_default="1440"),
        sa.Column("expected_publish_time", sa.String(16), nullable=True),
        sa.Column("conversion_policy", postgresql.JSONB(), nullable=True),
        sa.Column("outlier_pct_threshold", sa.Numeric(12, 6), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("organization_id", "code", name="uq_external_series_org_code"),
    )
    op.create_index("ix_external_series_organization_id", "external_series", ["organization_id"])
    op.create_index("ix_external_series_source_id", "external_series", ["source_id"])
    op.create_index("ix_external_series_code", "external_series", ["code"])

    op.create_table(
        "external_ingestion_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "source_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("external_data_sources.id"),
            nullable=False,
        ),
        sa.Column(
            "series_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("external_series.id"),
            nullable=True,
        ),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("trigger_type", sa.String(30), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("records_read", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_inserted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_revised", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_unchanged", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_rejected", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("requested_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("error_summary", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_external_ingestion_runs_source_id", "external_ingestion_runs", ["source_id"])
    op.create_index("ix_external_ingestion_runs_series_id", "external_ingestion_runs", ["series_id"])
    op.create_index("ix_external_ingestion_runs_organization_id", "external_ingestion_runs", ["organization_id"])
    op.create_index("ix_external_ingestion_runs_status", "external_ingestion_runs", ["status"])

    op.create_table(
        "external_observations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "series_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("external_series.id"),
            nullable=False,
        ),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("observation_datetime", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reference_period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reference_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_value", sa.Numeric(28, 10), nullable=False),
        sa.Column("canonical_value", sa.Numeric(28, 10), nullable=False),
        sa.Column("source_unit", sa.String(40), nullable=False),
        sa.Column("canonical_unit", sa.String(40), nullable=False),
        sa.Column("currency", sa.String(10), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("revision_status", sa.String(30), nullable=False, server_default="CURRENT"),
        sa.Column("external_identifier", sa.String(200), nullable=True),
        sa.Column("source_record_hash", sa.String(64), nullable=False),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=True),
        sa.Column(
            "ingestion_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("external_ingestion_runs.id"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint(
            "series_id",
            "observation_datetime",
            "revision_number",
            name="uq_external_observations_series_obs_rev",
        ),
    )
    op.create_index("ix_external_observations_series_id", "external_observations", ["series_id"])
    op.create_index("ix_external_observations_organization_id", "external_observations", ["organization_id"])
    op.create_index("ix_external_observations_observation_datetime", "external_observations", ["observation_datetime"])
    op.create_index("ix_external_observations_revision_status", "external_observations", ["revision_status"])
    op.create_index("ix_external_observations_source_record_hash", "external_observations", ["source_record_hash"])
    op.create_index("ix_external_observations_ingestion_run_id", "external_observations", ["ingestion_run_id"])
    op.create_index(
        "ix_external_obs_series_dt_current",
        "external_observations",
        ["series_id", "observation_datetime"],
        postgresql_where=sa.text("revision_status = 'CURRENT'"),
    )

    op.create_table(
        "external_import_files",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "ingestion_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("external_ingestion_runs.id"),
            nullable=False,
        ),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "series_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("external_series.id"),
            nullable=True,
        ),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("storage_key", sa.String(500), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("parse_status", sa.String(30), nullable=False, server_default="PENDING"),
        sa.Column("column_mapping", postgresql.JSONB(), nullable=True),
        sa.Column("preview_payload", postgresql.JSONB(), nullable=True),
        sa.Column("parse_errors", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_external_import_files_ingestion_run_id", "external_import_files", ["ingestion_run_id"])
    op.create_index("ix_external_import_files_organization_id", "external_import_files", ["organization_id"])

    op.create_table(
        "external_quality_issues",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "source_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("external_data_sources.id"),
            nullable=False,
        ),
        sa.Column(
            "series_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("external_series.id"),
            nullable=True,
        ),
        sa.Column(
            "observation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("external_observations.id"),
            nullable=True,
        ),
        sa.Column(
            "ingestion_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("external_ingestion_runs.id"),
            nullable=True,
        ),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("issue_code", sa.String(60), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("details", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("resolution_status", sa.String(30), nullable=False, server_default="OPEN"),
        sa.Column("resolved_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_external_quality_issues_source_id", "external_quality_issues", ["source_id"])
    op.create_index("ix_external_quality_issues_series_id", "external_quality_issues", ["series_id"])
    op.create_index("ix_external_quality_issues_observation_id", "external_quality_issues", ["observation_id"])
    op.create_index("ix_external_quality_issues_issue_code", "external_quality_issues", ["issue_code"])
    op.create_index("ix_external_quality_issues_resolution_status", "external_quality_issues", ["resolution_status"])
    op.create_index("ix_external_quality_issues_organization_id", "external_quality_issues", ["organization_id"])


def downgrade() -> None:
    op.drop_table("external_quality_issues")
    op.drop_table("external_import_files")
    op.drop_table("external_observations")
    op.drop_table("external_ingestion_runs")
    op.drop_table("external_series")
    op.drop_table("external_data_sources")
