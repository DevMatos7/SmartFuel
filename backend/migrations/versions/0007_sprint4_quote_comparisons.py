"""Sprint 4 — parâmetros financeiros e comparação de cotações."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007_sprint4_comparisons"
down_revision: str | None = "0006_sprint31_quotes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "financial_parameters",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("annual_effective_rate", sa.Numeric(12, 8), nullable=False),
        sa.Column("day_count_basis", sa.Integer(), nullable=False, server_default="365"),
        sa.Column("methodology_version", sa.String(50), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("annual_effective_rate >= 0", name="ck_financial_parameters_rate_nonneg"),
        sa.CheckConstraint("day_count_basis > 0", name="ck_financial_parameters_day_basis_positive"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"]),
    )
    op.create_index("ix_financial_parameters_organization_id", "financial_parameters", ["organization_id"])
    op.create_index("ix_financial_parameters_valid_from", "financial_parameters", ["valid_from"])
    op.create_index("ix_financial_parameters_valid_until", "financial_parameters", ["valid_until"])

    op.create_table(
        "quote_comparison_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("station_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("requested_volume_liters", sa.Numeric(16, 3), nullable=False),
        sa.Column("comparison_datetime", sa.DateTime(timezone=True), nullable=False),
        sa.Column("required_delivery_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ranking_mode", sa.String(40), nullable=False),
        sa.Column("ranking_scope", sa.String(40), nullable=False),
        sa.Column("financial_parameter_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("methodology_version", sa.String(50), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="PROCESSING"),
        sa.Column("reprocessed_from_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("eligible_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("warning_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ineligible_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("distributor_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("best_cost_per_liter", sa.Numeric(18, 8), nullable=True),
        sa.Column("highest_cost_per_liter", sa.Numeric(18, 8), nullable=True),
        sa.Column("average_cost_per_liter", sa.Numeric(18, 8), nullable=True),
        sa.Column("spread_absolute", sa.Numeric(18, 8), nullable=True),
        sa.Column("spread_percent", sa.Numeric(18, 8), nullable=True),
        sa.Column("input_snapshot", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("summary_snapshot", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("calculation_hash", sa.String(64), nullable=True),
        sa.Column("processing_duration_ms", sa.Integer(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("requested_volume_liters > 0", name="ck_quote_comparison_runs_volume_positive"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["station_id"], ["stations.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.ForeignKeyConstraint(["financial_parameter_id"], ["financial_parameters.id"]),
        sa.ForeignKeyConstraint(["reprocessed_from_run_id"], ["quote_comparison_runs.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
    )
    op.create_index("ix_quote_comparison_runs_organization_id", "quote_comparison_runs", ["organization_id"])
    op.create_index("ix_quote_comparison_runs_station_id", "quote_comparison_runs", ["station_id"])
    op.create_index("ix_quote_comparison_runs_product_id", "quote_comparison_runs", ["product_id"])
    op.create_index("ix_quote_comparison_runs_comparison_datetime", "quote_comparison_runs", ["comparison_datetime"])
    op.create_index("ix_quote_comparison_runs_created_at", "quote_comparison_runs", ["created_at"])
    op.create_index("ix_quote_comparison_runs_created_by", "quote_comparison_runs", ["created_by"])
    op.create_index("ix_quote_comparison_runs_status", "quote_comparison_runs", ["status"])

    op.create_table(
        "quote_comparison_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("comparison_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quote_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quote_item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("distributor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("distribution_base_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("payment_term_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("eligibility_status", sa.String(40), nullable=False),
        sa.Column("eligibility_reasons", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("raw_price_per_liter", sa.Numeric(18, 8), nullable=False),
        sa.Column("discount_per_liter", sa.Numeric(18, 8), nullable=False),
        sa.Column("rebate_per_liter", sa.Numeric(18, 8), nullable=False),
        sa.Column("freight_per_liter", sa.Numeric(18, 8), nullable=False),
        sa.Column("other_cost_per_liter", sa.Numeric(18, 8), nullable=False),
        sa.Column("delivered_cost_per_liter", sa.Numeric(18, 8), nullable=False),
        sa.Column("delivered_total", sa.Numeric(20, 4), nullable=False),
        sa.Column("financial_days", sa.Integer(), nullable=True),
        sa.Column("annual_effective_rate", sa.Numeric(12, 8), nullable=True),
        sa.Column("daily_rate", sa.Numeric(18, 12), nullable=True),
        sa.Column("financial_equivalent_cost_per_liter", sa.Numeric(18, 8), nullable=True),
        sa.Column("financial_equivalent_total", sa.Numeric(20, 4), nullable=True),
        sa.Column("ranking_cost_per_liter", sa.Numeric(18, 8), nullable=True),
        sa.Column("rank_position", sa.Integer(), nullable=True),
        sa.Column("is_best_for_distributor", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_best_overall", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("difference_per_liter", sa.Numeric(18, 8), nullable=True),
        sa.Column("difference_total", sa.Numeric(20, 4), nullable=True),
        sa.Column("effective_valid_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("delivery_expected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("input_snapshot", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("calculation_snapshot", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "rank_position IS NULL OR rank_position > 0",
            name="ck_quote_comparison_results_rank_positive",
        ),
        sa.ForeignKeyConstraint(["comparison_run_id"], ["quote_comparison_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["quote_id"], ["quotes.id"]),
        sa.ForeignKeyConstraint(["quote_item_id"], ["quote_items.id"]),
        sa.ForeignKeyConstraint(["distributor_id"], ["distributors.id"]),
        sa.ForeignKeyConstraint(["distribution_base_id"], ["distribution_bases.id"]),
        sa.ForeignKeyConstraint(["payment_term_id"], ["payment_terms.id"]),
    )
    op.create_index(
        "ix_quote_comparison_results_comparison_run_id",
        "quote_comparison_results",
        ["comparison_run_id"],
    )
    op.create_index(
        "ix_quote_comparison_results_distributor_id",
        "quote_comparison_results",
        ["distributor_id"],
    )
    op.create_index(
        "ix_quote_comparison_results_eligibility_status",
        "quote_comparison_results",
        ["eligibility_status"],
    )
    op.create_index(
        "ix_quote_comparison_results_rank_position",
        "quote_comparison_results",
        ["rank_position"],
    )
    op.create_index(
        "ix_quote_comparison_results_quote_item_id",
        "quote_comparison_results",
        ["quote_item_id"],
    )


def downgrade() -> None:
    op.drop_table("quote_comparison_results")
    op.drop_table("quote_comparison_runs")
    op.drop_table("financial_parameters")
