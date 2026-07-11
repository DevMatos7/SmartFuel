"""Sprint 10 — correlação, defasagem e índice de repasse."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0021_sprint10_market_correlation"
down_revision: str | None = "0020_sprint9_external_indices"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "market_analysis_parameters",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("minimum_sample_size", sa.Integer(), nullable=False, server_default="10"),
        sa.Column(
            "maximum_missing_percentage",
            sa.Numeric(8, 4),
            nullable=False,
            server_default="30.0000",
        ),
        sa.Column("maximum_carry_forward_age", sa.Integer(), nullable=False, server_default="7"),
        sa.Column("minimum_lag", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("maximum_lag", sa.Integer(), nullable=False, server_default="14"),
        sa.Column("lag_unit", sa.String(20), nullable=False, server_default="DAYS"),
        sa.Column(
            "minimum_reference_change",
            sa.Numeric(20, 10),
            nullable=False,
            server_default="0.0001000000",
        ),
        sa.Column("default_frequency", sa.String(20), nullable=False, server_default="DAILY"),
        sa.Column(
            "default_transformation",
            sa.String(40),
            nullable=False,
            server_default="PERCENTAGE_CHANGE",
        ),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint(
            "organization_id", "valid_from", name="uq_market_analysis_parameters_org_valid_from"
        ),
    )
    op.create_index("ix_market_analysis_parameters_organization_id", "market_analysis_parameters", ["organization_id"])
    op.create_index("ix_market_analysis_parameters_valid_from", "market_analysis_parameters", ["valid_from"])

    op.create_table(
        "internal_market_series_points",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("series_type", sa.String(80), nullable=False),
        sa.Column("station_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("stations.id"), nullable=True),
        sa.Column("canonical_product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("products.id"), nullable=True),
        sa.Column("distributor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("distributors.id"), nullable=True),
        sa.Column("observation_datetime", sa.DateTime(timezone=True), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("value", sa.Numeric(28, 10), nullable=False),
        sa.Column("unit", sa.String(40), nullable=False),
        sa.Column("volume_weight", sa.Numeric(22, 6), nullable=True),
        sa.Column("source_entity_type", sa.String(80), nullable=False),
        sa.Column("source_entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_record_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint(
            "organization_id",
            "series_type",
            "observation_datetime",
            "station_id",
            "canonical_product_id",
            "distributor_id",
            name="uq_internal_market_series_point_natural",
        ),
    )
    op.create_index("ix_imsp_org", "internal_market_series_points", ["organization_id"])
    op.create_index("ix_imsp_series_type", "internal_market_series_points", ["series_type"])
    op.create_index("ix_imsp_obs_dt", "internal_market_series_points", ["observation_datetime"])
    op.create_index("ix_imsp_available_at", "internal_market_series_points", ["available_at"])
    op.create_index("ix_imsp_station", "internal_market_series_points", ["station_id"])
    op.create_index("ix_imsp_product", "internal_market_series_points", ["canonical_product_id"])

    op.create_table(
        "market_analysis_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("analysis_type", sa.String(40), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column(
            "external_series_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("external_series.id"),
            nullable=True,
        ),
        sa.Column("external_series_code", sa.String(80), nullable=True),
        sa.Column("internal_series_type", sa.String(80), nullable=False),
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
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("frequency", sa.String(20), nullable=False),
        sa.Column("transformation", sa.String(40), nullable=False),
        sa.Column("alignment_policy", sa.String(60), nullable=False),
        sa.Column("lag_min", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("lag_max", sa.Integer(), nullable=False, server_default="14"),
        sa.Column("selected_lag", sa.Integer(), nullable=True),
        sa.Column("input_snapshot", postgresql.JSONB(), nullable=True),
        sa.Column("output_snapshot", postgresql.JSONB(), nullable=True),
        sa.Column("snapshot_hash", sa.String(64), nullable=True),
        sa.Column("sample_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("aligned_pair_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("warning_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "interpretive_disclaimer",
            sa.Text(),
            nullable=False,
            server_default=(
                "Resultados exploratórios de associação observada. "
                "Correlação e defasagem não constituem prova de causalidade."
            ),
        ),
        sa.Column("trigger_type", sa.String(30), nullable=False, server_default="MANUAL"),
        sa.Column("requested_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column(
            "reprocess_of_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("market_analysis_runs.id"),
            nullable=True,
        ),
        sa.Column("reprocess_reason", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_mar_org", "market_analysis_runs", ["organization_id"])
    op.create_index("ix_mar_status", "market_analysis_runs", ["status"])
    op.create_index("ix_mar_external_series", "market_analysis_runs", ["external_series_id"])
    op.create_index("ix_mar_station", "market_analysis_runs", ["station_id"])
    op.create_index("ix_mar_product", "market_analysis_runs", ["canonical_product_id"])
    op.create_index("ix_mar_hash", "market_analysis_runs", ["snapshot_hash"])

    op.create_table(
        "market_analysis_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "analysis_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("market_analysis_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("metric_type", sa.String(60), nullable=False),
        sa.Column("coefficient", sa.Numeric(20, 10), nullable=True),
        sa.Column("p_value", sa.Numeric(20, 10), nullable=True),
        sa.Column("lag_value", sa.Integer(), nullable=True),
        sa.Column("sample_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("coverage_percentage", sa.Numeric(12, 8), nullable=True),
        sa.Column("pass_through_ratio", sa.Numeric(20, 10), nullable=True),
        sa.Column("pass_through_elasticity", sa.Numeric(20, 10), nullable=True),
        sa.Column("quality_status", sa.String(40), nullable=False),
        sa.Column("warnings", postgresql.JSONB(), nullable=True),
        sa.Column("details", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_mares_run", "market_analysis_results", ["analysis_run_id"])
    op.create_index("ix_mares_metric", "market_analysis_results", ["metric_type"])

    op.create_table(
        "market_aligned_observations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "analysis_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("market_analysis_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("period_datetime", sa.DateTime(timezone=True), nullable=False),
        sa.Column("external_observation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("external_value", sa.Numeric(28, 10), nullable=False),
        sa.Column("external_change", sa.Numeric(28, 10), nullable=True),
        sa.Column("internal_entity_type", sa.String(80), nullable=True),
        sa.Column("internal_entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("internal_value", sa.Numeric(28, 10), nullable=False),
        sa.Column("internal_change", sa.Numeric(28, 10), nullable=True),
        sa.Column("lag_applied", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("carry_forward", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("carry_forward_age", sa.Integer(), nullable=True),
        sa.Column("included", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("exclusion_reason", sa.String(120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_mao_run", "market_aligned_observations", ["analysis_run_id"])
    op.create_index("ix_mao_period", "market_aligned_observations", ["period_datetime"])

    op.create_table(
        "market_pass_through_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "analysis_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("market_analysis_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(40), nullable=False),
        sa.Column("event_direction", sa.String(20), nullable=False),
        sa.Column("reference_event_datetime", sa.DateTime(timezone=True), nullable=False),
        sa.Column("target_event_datetime", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lag_value", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reference_change", sa.Numeric(28, 10), nullable=False),
        sa.Column("target_change", sa.Numeric(28, 10), nullable=False),
        sa.Column("pass_through_ratio", sa.Numeric(20, 10), nullable=True),
        sa.Column("pass_through_elasticity", sa.Numeric(20, 10), nullable=True),
        sa.Column("quality_status", sa.String(40), nullable=False),
        sa.Column("details", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_mpte_run", "market_pass_through_events", ["analysis_run_id"])


def downgrade() -> None:
    op.drop_table("market_pass_through_events")
    op.drop_table("market_aligned_observations")
    op.drop_table("market_analysis_results")
    op.drop_table("market_analysis_runs")
    op.drop_table("internal_market_series_points")
    op.drop_table("market_analysis_parameters")
