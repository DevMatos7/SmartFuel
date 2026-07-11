"""Sprint 8 — purchase quote benchmarks."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0018_sprint8_benchmarks"
down_revision: str | None = "0017_xml_imported_erp"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "purchase_benchmark_parameters",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("absolute_tolerance_per_liter", sa.Numeric(20, 8), nullable=False, server_default="0"),
        sa.Column("percentage_tolerance", sa.Numeric(12, 8), nullable=False, server_default="0"),
        sa.Column("allow_low_confidence_reference", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("default_comparison_mode", sa.String(40), nullable=False, server_default="DELIVERED_COST"),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("organization_id", "valid_from", name="uq_purchase_benchmark_parameters_org_valid_from"),
    )
    op.create_index("ix_purchase_benchmark_parameters_valid_from", "purchase_benchmark_parameters", ["valid_from"])

    op.create_table(
        "purchase_quote_benchmark_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "purchase_invoice_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("fuel_purchase_invoices.id"),
            nullable=False,
        ),
        sa.Column("station_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("stations.id"), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("comparison_mode", sa.String(40), nullable=False),
        sa.Column("reference_datetime", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reference_source", sa.String(40), nullable=False, server_default="UNKNOWN"),
        sa.Column("reference_confidence", sa.String(20), nullable=False, server_default="UNAVAILABLE"),
        sa.Column("trigger_type", sa.String(30), nullable=False, server_default="MANUAL"),
        sa.Column("requested_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column(
            "reprocess_of_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("purchase_quote_benchmark_runs.id"),
            nullable=True,
        ),
        sa.Column("reprocess_reason", sa.Text(), nullable=True),
        sa.Column("input_snapshot", postgresql.JSONB(), nullable=True),
        sa.Column("output_snapshot", postgresql.JSONB(), nullable=True),
        sa.Column("snapshot_hash", sa.String(64), nullable=True),
        sa.Column("item_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("benchmarked_item_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("warning_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("actual_total_cost", sa.Numeric(24, 4), nullable=False, server_default="0"),
        sa.Column("benchmark_total_cost", sa.Numeric(24, 4), nullable=True),
        sa.Column("cost_variance_amount", sa.Numeric(24, 4), nullable=True),
        sa.Column("opportunity_amount", sa.Numeric(24, 4), nullable=True),
        sa.Column("actual_advantage_amount", sa.Numeric(24, 4), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_pqbr_org", "purchase_quote_benchmark_runs", ["organization_id"])
    op.create_index("ix_pqbr_invoice", "purchase_quote_benchmark_runs", ["purchase_invoice_id"])
    op.create_index("ix_pqbr_station", "purchase_quote_benchmark_runs", ["station_id"])
    op.create_index("ix_pqbr_status", "purchase_quote_benchmark_runs", ["status"])
    op.create_index("ix_pqbr_hash", "purchase_quote_benchmark_runs", ["snapshot_hash"])

    op.create_table(
        "purchase_quote_benchmark_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "benchmark_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("purchase_quote_benchmark_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("station_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("stations.id"), nullable=False),
        sa.Column(
            "purchase_invoice_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("fuel_purchase_invoices.id"),
            nullable=False,
        ),
        sa.Column("group_key", sa.String(200), nullable=False),
        sa.Column("canonical_product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("products.id"), nullable=True),
        sa.Column(
            "actual_distributor_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("distributors.id"),
            nullable=True,
        ),
        sa.Column("volume_liters", sa.Numeric(22, 6), nullable=False, server_default="0"),
        sa.Column("actual_delivered_cost", sa.Numeric(24, 4), nullable=False, server_default="0"),
        sa.Column("actual_delivered_cost_per_liter", sa.Numeric(20, 8), nullable=True),
        sa.Column("actual_financial_equivalent_cost", sa.Numeric(24, 4), nullable=True),
        sa.Column("actual_financial_equivalent_per_liter", sa.Numeric(20, 8), nullable=True),
        sa.Column("benchmark_status", sa.String(40), nullable=False),
        sa.Column("decision_result", sa.String(40), nullable=False),
        sa.Column("best_quote_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("best_quote_item_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("best_distributor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("distributors.id"), nullable=True),
        sa.Column("benchmark_cost_per_liter", sa.Numeric(20, 8), nullable=True),
        sa.Column("benchmark_total_cost", sa.Numeric(24, 4), nullable=True),
        sa.Column("cost_variance_per_liter", sa.Numeric(20, 8), nullable=True),
        sa.Column("cost_variance_amount", sa.Numeric(24, 4), nullable=True),
        sa.Column("opportunity_amount", sa.Numeric(24, 4), nullable=True),
        sa.Column("actual_advantage_amount", sa.Numeric(24, 4), nullable=True),
        sa.Column("actual_distributor_rank", sa.Integer(), nullable=True),
        sa.Column("candidate_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("eligible_candidate_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("exclusion_reasons", postgresql.JSONB(), nullable=True),
        sa.Column("warnings", postgresql.JSONB(), nullable=True),
        sa.Column("input_snapshot", postgresql.JSONB(), nullable=True),
        sa.Column("result_snapshot", postgresql.JSONB(), nullable=True),
        sa.Column("snapshot_hash", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_pqbi_run", "purchase_quote_benchmark_items", ["benchmark_run_id"])
    op.create_index("ix_pqbi_org", "purchase_quote_benchmark_items", ["organization_id"])
    op.create_index("ix_pqbi_status", "purchase_quote_benchmark_items", ["benchmark_status"])
    op.create_index("ix_pqbi_decision", "purchase_quote_benchmark_items", ["decision_result"])
    op.create_index("ix_pqbi_group", "purchase_quote_benchmark_items", ["group_key"])

    op.create_table(
        "purchase_quote_benchmark_candidates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "benchmark_item_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("purchase_quote_benchmark_items.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("quote_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quote_item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("distributor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("eligibility_status", sa.String(40), nullable=False),
        sa.Column("blocking_reasons", postgresql.JSONB(), nullable=True),
        sa.Column("warnings", postgresql.JSONB(), nullable=True),
        sa.Column("raw_price_per_liter", sa.Numeric(20, 8), nullable=True),
        sa.Column("delivered_cost_per_liter", sa.Numeric(20, 8), nullable=True),
        sa.Column("financial_equivalent_per_liter", sa.Numeric(20, 8), nullable=True),
        sa.Column("ranking_position", sa.Integer(), nullable=True),
        sa.Column("is_best", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("candidate_snapshot", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_pqbc_item", "purchase_quote_benchmark_candidates", ["benchmark_item_id"])
    op.create_index("ix_pqbc_quote", "purchase_quote_benchmark_candidates", ["quote_id"])

    op.create_table(
        "purchase_benchmark_overrides",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "purchase_invoice_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("fuel_purchase_invoices.id"),
            nullable=False,
        ),
        sa.Column("override_type", sa.String(40), nullable=False),
        sa.Column("previous_value", postgresql.JSONB(), nullable=True),
        sa.Column("new_value", postgresql.JSONB(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("deactivated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_pbo_org", "purchase_benchmark_overrides", ["organization_id"])
    op.create_index("ix_pbo_invoice", "purchase_benchmark_overrides", ["purchase_invoice_id"])
    op.create_index("ix_pbo_type", "purchase_benchmark_overrides", ["override_type"])


def downgrade() -> None:
    op.drop_table("purchase_benchmark_overrides")
    op.drop_table("purchase_quote_benchmark_candidates")
    op.drop_table("purchase_quote_benchmark_items")
    op.drop_table("purchase_quote_benchmark_runs")
    op.drop_table("purchase_benchmark_parameters")
