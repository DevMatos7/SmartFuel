"""Sprint 11 — formação de preço, margem, aprovação e evidências."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0022_sprint11_pricing_decisions"
down_revision: str | None = "0021_sprint10_market_correlation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "pricing_policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("station_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("stations.id"), nullable=True),
        sa.Column(
            "canonical_product_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("products.id"),
            nullable=True,
        ),
        sa.Column("price_type", sa.String(40), nullable=False, server_default="POSTED_PRICE"),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="ACTIVE"),
        sa.Column("cost_basis_type", sa.String(60), nullable=False),
        sa.Column("weighted_cost_window_days", sa.Integer(), nullable=True),
        sa.Column("minimum_purchase_count", sa.Integer(), nullable=True),
        sa.Column("minimum_purchase_volume", sa.Numeric(22, 6), nullable=True),
        sa.Column("minimum_margin_per_liter", sa.Numeric(20, 8), nullable=True),
        sa.Column("minimum_margin_percentage", sa.Numeric(12, 8), nullable=True),
        sa.Column("minimum_markup_percentage", sa.Numeric(12, 8), nullable=True),
        sa.Column("target_margin_per_liter", sa.Numeric(20, 8), nullable=True),
        sa.Column("target_margin_percentage", sa.Numeric(12, 8), nullable=True),
        sa.Column("target_markup_percentage", sa.Numeric(12, 8), nullable=True),
        sa.Column("maximum_increase_per_liter", sa.Numeric(20, 8), nullable=True),
        sa.Column("maximum_decrease_per_liter", sa.Numeric(20, 8), nullable=True),
        sa.Column("maximum_increase_percentage", sa.Numeric(12, 8), nullable=True),
        sa.Column("maximum_decrease_percentage", sa.Numeric(12, 8), nullable=True),
        sa.Column("minimum_change_per_liter", sa.Numeric(20, 8), nullable=True),
        sa.Column("rounding_policy", sa.String(40), nullable=False, server_default="NEAREST_CENT"),
        sa.Column("rounding_increment", sa.Numeric(20, 8), nullable=True),
        sa.Column("default_scenario", sa.String(40), nullable=False, server_default="BALANCED"),
        sa.Column("allow_low_confidence_cost", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("require_market_signal", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("require_evidence_on_approve", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("allow_self_approval", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("required_approvals", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "implementation_tolerance_per_liter",
            sa.Numeric(20, 8),
            nullable=False,
            server_default="0.01000000",
        ),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_pricing_policies_organization_id", "pricing_policies", ["organization_id"])
    op.create_index("ix_pricing_policies_station_id", "pricing_policies", ["station_id"])
    op.create_index("ix_pricing_policies_product", "pricing_policies", ["canonical_product_id"])
    op.create_index("ix_pricing_policies_valid_from", "pricing_policies", ["valid_from"])
    op.create_index("ix_pricing_policies_active", "pricing_policies", ["active"])

    op.create_table(
        "pricing_recommendation_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("trigger_type", sa.String(30), nullable=False, server_default="MANUAL"),
        sa.Column("reference_datetime", sa.DateTime(timezone=True), nullable=False),
        sa.Column("station_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("stations.id"), nullable=True),
        sa.Column(
            "canonical_product_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("products.id"),
            nullable=True,
        ),
        sa.Column("price_type", sa.String(40), nullable=False, server_default="POSTED_PRICE"),
        sa.Column("requested_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column(
            "reprocess_of_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("pricing_recommendation_runs.id"),
            nullable=True,
        ),
        sa.Column("reprocess_reason", sa.Text(), nullable=True),
        sa.Column("item_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("recommendation_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("warning_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("input_snapshot", postgresql.JSONB(), nullable=True),
        sa.Column("output_snapshot", postgresql.JSONB(), nullable=True),
        sa.Column("snapshot_hash", sa.String(64), nullable=True),
        sa.Column(
            "interpretive_disclaimer",
            sa.Text(),
            nullable=False,
            server_default=(
                "Margem bruta comercial estimada. Não é lucro líquido. "
                "Recomendação não altera preço no ERP/XPERT."
            ),
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_pricing_runs_org", "pricing_recommendation_runs", ["organization_id"])
    op.create_index("ix_pricing_runs_status", "pricing_recommendation_runs", ["status"])
    op.create_index("ix_pricing_runs_station", "pricing_recommendation_runs", ["station_id"])
    op.create_index("ix_pricing_runs_product", "pricing_recommendation_runs", ["canonical_product_id"])
    op.create_index("ix_pricing_runs_hash", "pricing_recommendation_runs", ["snapshot_hash"])

    op.create_table(
        "pricing_recommendation_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "recommendation_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("pricing_recommendation_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("station_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("stations.id"), nullable=False),
        sa.Column(
            "canonical_product_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("products.id"),
            nullable=False,
        ),
        sa.Column("price_type", sa.String(40), nullable=False),
        sa.Column("reference_datetime", sa.DateTime(timezone=True), nullable=False),
        sa.Column("current_price", sa.Numeric(20, 8), nullable=True),
        sa.Column("current_price_source", sa.String(60), nullable=True),
        sa.Column("current_price_datetime", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cost_basis_type", sa.String(60), nullable=False),
        sa.Column("cost_per_liter", sa.Numeric(20, 8), nullable=True),
        sa.Column("cost_datetime", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cost_confidence", sa.String(20), nullable=False),
        sa.Column("current_margin_per_liter", sa.Numeric(20, 8), nullable=True),
        sa.Column("current_margin_percentage", sa.Numeric(12, 8), nullable=True),
        sa.Column("current_markup_percentage", sa.Numeric(12, 8), nullable=True),
        sa.Column("commercial_floor_price", sa.Numeric(20, 8), nullable=True),
        sa.Column("target_price", sa.Numeric(20, 8), nullable=True),
        sa.Column("raw_recommended_price", sa.Numeric(20, 8), nullable=True),
        sa.Column("recommended_price", sa.Numeric(20, 8), nullable=True),
        sa.Column("recommended_change_per_liter", sa.Numeric(20, 8), nullable=True),
        sa.Column("recommended_change_percentage", sa.Numeric(12, 8), nullable=True),
        sa.Column("recommendation_status", sa.String(40), nullable=False),
        sa.Column("quality_status", sa.String(40), nullable=False),
        sa.Column("guardrail_applied", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("rounding_policy", sa.String(40), nullable=True),
        sa.Column("reasons", postgresql.JSONB(), nullable=True),
        sa.Column("warnings", postgresql.JSONB(), nullable=True),
        sa.Column("input_snapshot", postgresql.JSONB(), nullable=True),
        sa.Column("result_snapshot", postgresql.JSONB(), nullable=True),
        sa.Column("snapshot_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_pricing_items_run", "pricing_recommendation_items", ["recommendation_run_id"])
    op.create_index("ix_pricing_items_org", "pricing_recommendation_items", ["organization_id"])
    op.create_index("ix_pricing_items_station", "pricing_recommendation_items", ["station_id"])
    op.create_index("ix_pricing_items_product", "pricing_recommendation_items", ["canonical_product_id"])
    op.create_index("ix_pricing_items_status", "pricing_recommendation_items", ["recommendation_status"])
    op.create_index("ix_pricing_items_quality", "pricing_recommendation_items", ["quality_status"])

    op.create_table(
        "pricing_recommendation_scenarios",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "recommendation_item_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("pricing_recommendation_items.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("scenario_type", sa.String(40), nullable=False),
        sa.Column("cost_per_liter", sa.Numeric(20, 8), nullable=False),
        sa.Column("margin_per_liter", sa.Numeric(20, 8), nullable=False),
        sa.Column("margin_percentage", sa.Numeric(12, 8), nullable=True),
        sa.Column("markup_percentage", sa.Numeric(12, 8), nullable=True),
        sa.Column("calculated_price", sa.Numeric(20, 8), nullable=False),
        sa.Column("rounded_price", sa.Numeric(20, 8), nullable=False),
        sa.Column("details", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_pricing_scenarios_item", "pricing_recommendation_scenarios", ["recommendation_item_id"])

    op.create_table(
        "pricing_decisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "recommendation_item_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("pricing_recommendation_items.id"),
            nullable=False,
        ),
        sa.Column("status", sa.String(60), nullable=False),
        sa.Column("selected_scenario", sa.String(40), nullable=True),
        sa.Column("recommended_price", sa.Numeric(20, 8), nullable=False),
        sa.Column("approved_price", sa.Numeric(20, 8), nullable=True),
        sa.Column("decision_reason", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_pricing_decisions_org", "pricing_decisions", ["organization_id"])
    op.create_index("ix_pricing_decisions_item", "pricing_decisions", ["recommendation_item_id"])
    op.create_index("ix_pricing_decisions_status", "pricing_decisions", ["status"])

    op.create_table(
        "pricing_decision_approvals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "pricing_decision_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("pricing_decisions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("approval_level", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(30), nullable=False, server_default="PENDING"),
        sa.Column("decision", sa.String(30), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("assigned_role", sa.String(40), nullable=True),
        sa.Column("assigned_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("decided_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_pricing_approvals_decision", "pricing_decision_approvals", ["pricing_decision_id"])

    op.create_table(
        "pricing_decision_evidence",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "pricing_decision_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("pricing_decisions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("evidence_type", sa.String(60), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("storage_key", sa.String(500), nullable=True),
        sa.Column("sha256", sa.String(64), nullable=True),
        sa.Column("content_type", sa.String(120), nullable=True),
        sa.Column("size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("original_filename", sa.String(255), nullable=True),
        sa.Column("structured_payload", postgresql.JSONB(), nullable=True),
        sa.Column("uploaded_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_pricing_evidence_decision", "pricing_decision_evidence", ["pricing_decision_id"])

    op.create_table(
        "pricing_implementation_checks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "pricing_decision_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("pricing_decisions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("check_type", sa.String(40), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("approved_price", sa.Numeric(20, 8), nullable=False),
        sa.Column("implemented_price", sa.Numeric(20, 8), nullable=True),
        sa.Column("implementation_variance", sa.Numeric(20, 8), nullable=True),
        sa.Column("price_snapshot_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("implemented_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("evidence_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("details", postgresql.JSONB(), nullable=True),
        sa.Column("checked_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index(
        "ix_pricing_impl_checks_decision", "pricing_implementation_checks", ["pricing_decision_id"]
    )


def downgrade() -> None:
    op.drop_table("pricing_implementation_checks")
    op.drop_table("pricing_decision_evidence")
    op.drop_table("pricing_decision_approvals")
    op.drop_table("pricing_decisions")
    op.drop_table("pricing_recommendation_scenarios")
    op.drop_table("pricing_recommendation_items")
    op.drop_table("pricing_recommendation_runs")
    op.drop_table("pricing_policies")
