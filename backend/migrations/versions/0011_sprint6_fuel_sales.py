"""Sprint 6 — vendas combustível, preços, margem e security_status."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0011_sprint6_fuel_sales"
down_revision: str | None = "0010_sprint51"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "erp_sources",
        sa.Column("security_status", sa.String(30), nullable=False, server_default="UNKNOWN"),
    )

    op.create_table(
        "erp_payment_methods",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("station_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("stations.id"), nullable=True),
        sa.Column("source_payment_method_id", sa.String(100), nullable=False),
        sa.Column("source_code", sa.String(100), nullable=True),
        sa.Column("source_name", sa.String(255), nullable=False),
        sa.Column("normalized_group", sa.String(40), nullable=False, server_default="UNMAPPED"),
        sa.Column("mapping_status", sa.String(30), nullable=False, server_default="PENDING"),
        sa.Column("source_active", sa.Boolean(), nullable=True),
        sa.Column("source_record_hash", sa.String(64), nullable=True),
        sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_sync_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("erp_sync_runs.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("station_id", "source_payment_method_id", name="uq_erp_payment_methods_station_source"),
    )
    op.create_index("ix_erp_payment_methods_org", "erp_payment_methods", ["organization_id"])
    op.create_index("ix_erp_payment_methods_group", "erp_payment_methods", ["normalized_group"])
    op.create_index("ix_erp_payment_methods_status", "erp_payment_methods", ["mapping_status"])

    op.create_table(
        "fuel_sales_facts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("station_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("stations.id"), nullable=False),
        sa.Column("source_sale_id", sa.String(100), nullable=False),
        sa.Column("source_sale_item_id", sa.String(100), nullable=False),
        sa.Column("source_document_number", sa.String(100), nullable=True),
        sa.Column("sold_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("business_date", sa.Date(), nullable=False),
        sa.Column("erp_product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("erp_products.id"), nullable=False),
        sa.Column("canonical_product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("products.id"), nullable=True),
        sa.Column("erp_payment_method_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("erp_payment_methods.id"), nullable=True),
        sa.Column("payment_method_group", sa.String(40), nullable=True),
        sa.Column("operation_type", sa.String(30), nullable=False, server_default="SALE"),
        sa.Column("is_cancelled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("source_unit", sa.String(30), nullable=True),
        sa.Column("quantity_source", sa.Numeric(18, 6), nullable=True),
        sa.Column("volume_liters", sa.Numeric(18, 6), nullable=True),
        sa.Column("unit_price", sa.Numeric(18, 8), nullable=True),
        sa.Column("gross_amount", sa.Numeric(20, 4), nullable=False, server_default="0"),
        sa.Column("discount_amount", sa.Numeric(20, 4), nullable=False, server_default="0"),
        sa.Column("surcharge_amount", sa.Numeric(20, 4), nullable=False, server_default="0"),
        sa.Column("net_amount", sa.Numeric(20, 4), nullable=False, server_default="0"),
        sa.Column("cost_per_liter", sa.Numeric(18, 8), nullable=True),
        sa.Column("total_cost_amount", sa.Numeric(20, 4), nullable=True),
        sa.Column("cost_source", sa.String(40), nullable=True),
        sa.Column("margin_status", sa.String(30), nullable=False, server_default="UNAVAILABLE"),
        sa.Column("realized_price_per_liter", sa.Numeric(18, 8), nullable=True),
        sa.Column("gross_margin_amount", sa.Numeric(20, 4), nullable=True),
        sa.Column("gross_margin_per_liter", sa.Numeric(18, 8), nullable=True),
        sa.Column("gross_margin_percent", sa.Numeric(18, 8), nullable=True),
        sa.Column("metric_eligibility_status", sa.String(40), nullable=False, server_default="EXCLUDED"),
        sa.Column("metric_exclusion_reasons", postgresql.JSONB(), nullable=True),
        sa.Column("source_record_hash", sa.String(64), nullable=False),
        sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_sync_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("erp_sync_runs.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint(
            "organization_id", "station_id", "source_sale_id", "source_sale_item_id",
            name="uq_fuel_sales_facts_natural_key",
        ),
    )
    op.create_index("ix_fuel_sales_facts_station_date", "fuel_sales_facts", ["station_id", "business_date"])
    op.create_index("ix_fuel_sales_facts_product_date", "fuel_sales_facts", ["canonical_product_id", "business_date"])
    op.create_index("ix_fuel_sales_facts_eligibility", "fuel_sales_facts", ["metric_eligibility_status"])
    op.create_index("ix_fuel_sales_facts_updated", "fuel_sales_facts", ["source_updated_at"])

    op.create_table(
        "fuel_retail_price_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("station_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("stations.id"), nullable=False),
        sa.Column("erp_product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("erp_products.id"), nullable=False),
        sa.Column("canonical_product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("products.id"), nullable=True),
        sa.Column("erp_payment_method_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("erp_payment_methods.id"), nullable=False),
        sa.Column("payment_method_group", sa.String(40), nullable=True),
        sa.Column("price_per_liter", sa.Numeric(18, 8), nullable=False),
        sa.Column("history_source", sa.String(40), nullable=False, server_default="OBSERVED_BY_SYNC"),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("source_record_hash", sa.String(64), nullable=False),
        sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_sync_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("erp_sync_runs.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint(
            "station_id", "erp_product_id", "erp_payment_method_id", "effective_from",
            name="uq_fuel_retail_price_snapshots_key",
        ),
    )

    op.create_table(
        "fuel_sales_daily_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("station_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("stations.id"), nullable=False),
        sa.Column("business_date", sa.Date(), nullable=False),
        sa.Column("canonical_product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("payment_method_group", sa.String(40), nullable=True),
        sa.Column("sales_item_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("net_volume_liters", sa.Numeric(20, 6), nullable=False, server_default="0"),
        sa.Column("gross_sales_amount", sa.Numeric(22, 4), nullable=False, server_default="0"),
        sa.Column("discount_amount", sa.Numeric(22, 4), nullable=False, server_default="0"),
        sa.Column("net_sales_amount", sa.Numeric(22, 4), nullable=False, server_default="0"),
        sa.Column("total_cost_amount", sa.Numeric(22, 4), nullable=True),
        sa.Column("cost_available_volume_liters", sa.Numeric(20, 6), nullable=False, server_default="0"),
        sa.Column("realized_price_per_liter", sa.Numeric(18, 8), nullable=True),
        sa.Column("gross_margin_amount", sa.Numeric(22, 4), nullable=True),
        sa.Column("gross_margin_per_liter", sa.Numeric(18, 8), nullable=True),
        sa.Column("gross_margin_percent", sa.Numeric(18, 8), nullable=True),
        sa.Column("negative_margin_item_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unmapped_item_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unmapped_volume_liters", sa.Numeric(20, 6), nullable=False, server_default="0"),
        sa.Column("last_rebuilt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_sync_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("erp_sync_runs.id"), nullable=True),
        sa.UniqueConstraint(
            "organization_id", "station_id", "business_date", "canonical_product_id", "payment_method_group",
            name="uq_fuel_sales_daily_metrics_key",
        ),
    )
    op.create_index("ix_fuel_sales_daily_metrics_station_date", "fuel_sales_daily_metrics", ["station_id", "business_date"])

    op.create_table(
        "sales_mapping_reconciliation_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="QUEUED"),
        sa.Column("erp_product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("erp_products.id"), nullable=True),
        sa.Column("affected_facts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("affected_dates", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("requested_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("sales_mapping_reconciliation_runs")
    op.drop_index("ix_fuel_sales_daily_metrics_station_date", table_name="fuel_sales_daily_metrics")
    op.drop_table("fuel_sales_daily_metrics")
    op.drop_table("fuel_retail_price_snapshots")
    op.drop_index("ix_fuel_sales_facts_updated", table_name="fuel_sales_facts")
    op.drop_index("ix_fuel_sales_facts_eligibility", table_name="fuel_sales_facts")
    op.drop_index("ix_fuel_sales_facts_product_date", table_name="fuel_sales_facts")
    op.drop_index("ix_fuel_sales_facts_station_date", table_name="fuel_sales_facts")
    op.drop_table("fuel_sales_facts")
    op.drop_index("ix_erp_payment_methods_status", table_name="erp_payment_methods")
    op.drop_index("ix_erp_payment_methods_group", table_name="erp_payment_methods")
    op.drop_index("ix_erp_payment_methods_org", table_name="erp_payment_methods")
    op.drop_table("erp_payment_methods")
    op.drop_column("erp_sources", "security_status")
