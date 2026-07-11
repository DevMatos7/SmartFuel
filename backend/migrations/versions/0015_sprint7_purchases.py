"""Sprint 7 — compras de combustíveis, NF-e e contas a pagar."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0015_sprint7_purchases"
down_revision: str | None = "0014_fuel_sales_orphan_product"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "fuel_purchase_invoices",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("station_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("stations.id"), nullable=False),
        sa.Column("source_invoice_id", sa.String(100), nullable=False),
        sa.Column("source_document_number", sa.String(100), nullable=False),
        sa.Column("source_series", sa.String(20), nullable=True),
        sa.Column("access_key", sa.String(44), nullable=True),
        sa.Column("erp_supplier_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("erp_suppliers.id"), nullable=True),
        sa.Column("distributor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("distributors.id"), nullable=True),
        sa.Column("source_supplier_id", sa.String(100), nullable=False),
        sa.Column("issue_date", sa.Date(), nullable=False),
        sa.Column("entry_date", sa.Date(), nullable=False),
        sa.Column("operation_type", sa.String(40), nullable=False, server_default="PURCHASE"),
        sa.Column("source_status", sa.String(80), nullable=False),
        sa.Column("is_cancelled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("gross_amount", sa.Numeric(22, 4), nullable=False, server_default="0"),
        sa.Column("discount_amount", sa.Numeric(22, 4), nullable=False, server_default="0"),
        sa.Column("freight_amount", sa.Numeric(22, 4), nullable=False, server_default="0"),
        sa.Column("insurance_amount", sa.Numeric(22, 4), nullable=False, server_default="0"),
        sa.Column("other_expenses_amount", sa.Numeric(22, 4), nullable=False, server_default="0"),
        sa.Column("tax_amount", sa.Numeric(22, 4), nullable=False, server_default="0"),
        sa.Column("total_amount", sa.Numeric(22, 4), nullable=False, server_default="0"),
        sa.Column("payment_condition_id", sa.String(100), nullable=True),
        sa.Column("source_base_id", sa.String(100), nullable=True),
        sa.Column("allocation_method", sa.String(40), nullable=True),
        sa.Column("metric_eligibility_status", sa.String(40), nullable=False, server_default="EXCLUDED"),
        sa.Column("metric_exclusion_reasons", postgresql.JSONB(), nullable=True),
        sa.Column("source_record_hash", sa.String(64), nullable=False),
        sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_sync_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("erp_sync_runs.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint(
            "organization_id", "station_id", "source_invoice_id",
            name="uq_fuel_purchase_invoices_natural_key",
        ),
    )
    op.create_index("ix_fuel_purchase_invoices_org", "fuel_purchase_invoices", ["organization_id"])
    op.create_index("ix_fuel_purchase_invoices_station_entry", "fuel_purchase_invoices", ["station_id", "entry_date"])
    op.create_index("ix_fuel_purchase_invoices_access_key", "fuel_purchase_invoices", ["access_key"])
    op.create_index(
        "uq_fuel_purchase_invoices_org_access_key",
        "fuel_purchase_invoices",
        ["organization_id", "access_key"],
        unique=True,
        postgresql_where=sa.text("access_key IS NOT NULL"),
    )

    op.create_table(
        "fuel_purchase_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("station_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("stations.id"), nullable=False),
        sa.Column(
            "purchase_invoice_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("fuel_purchase_invoices.id"),
            nullable=False,
        ),
        sa.Column("source_invoice_id", sa.String(100), nullable=False),
        sa.Column("source_invoice_item_id", sa.String(100), nullable=False),
        sa.Column("source_product_id", sa.String(100), nullable=False),
        sa.Column("erp_product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("erp_products.id"), nullable=True),
        sa.Column("canonical_product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("products.id"), nullable=True),
        sa.Column("source_description", sa.String(255), nullable=True),
        sa.Column("source_unit", sa.String(30), nullable=True),
        sa.Column("source_quantity", sa.Numeric(20, 6), nullable=False),
        sa.Column("volume_liters", sa.Numeric(20, 6), nullable=True),
        sa.Column("unit_price", sa.Numeric(20, 8), nullable=False, server_default="0"),
        sa.Column("gross_item_amount", sa.Numeric(22, 4), nullable=False, server_default="0"),
        sa.Column("gross_amount_source", sa.String(40), nullable=True),
        sa.Column("discount_amount", sa.Numeric(22, 4), nullable=False, server_default="0"),
        sa.Column("rebate_amount", sa.Numeric(22, 4), nullable=False, server_default="0"),
        sa.Column("allocated_freight_amount", sa.Numeric(22, 4), nullable=False, server_default="0"),
        sa.Column("allocated_insurance_amount", sa.Numeric(22, 4), nullable=False, server_default="0"),
        sa.Column("allocated_other_expenses", sa.Numeric(22, 4), nullable=False, server_default="0"),
        sa.Column("icms_amount", sa.Numeric(22, 4), nullable=True),
        sa.Column("icms_st_amount", sa.Numeric(22, 4), nullable=True),
        sa.Column("fcp_amount", sa.Numeric(22, 4), nullable=True),
        sa.Column("pis_amount", sa.Numeric(22, 4), nullable=True),
        sa.Column("cofins_amount", sa.Numeric(22, 4), nullable=True),
        sa.Column("erp_recorded_cost", sa.Numeric(22, 4), nullable=True),
        sa.Column("accounting_cost", sa.Numeric(22, 4), nullable=True),
        sa.Column("commercial_delivered_cost", sa.Numeric(22, 4), nullable=False, server_default="0"),
        sa.Column("delivered_cost_per_liter", sa.Numeric(20, 8), nullable=True),
        sa.Column("cfop", sa.String(20), nullable=True),
        sa.Column("ncm", sa.String(20), nullable=True),
        sa.Column("operation_type", sa.String(40), nullable=False, server_default="PURCHASE"),
        sa.Column("is_cancelled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("metric_eligibility_status", sa.String(40), nullable=False, server_default="EXCLUDED"),
        sa.Column("metric_exclusion_reasons", postgresql.JSONB(), nullable=True),
        sa.Column("source_record_hash", sa.String(64), nullable=False),
        sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_sync_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("erp_sync_runs.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint(
            "station_id", "source_invoice_id", "source_invoice_item_id",
            name="uq_fuel_purchase_items_natural_key",
        ),
    )
    op.create_index("ix_fuel_purchase_items_invoice", "fuel_purchase_items", ["purchase_invoice_id"])
    op.create_index("ix_fuel_purchase_items_product", "fuel_purchase_items", ["source_product_id"])
    op.create_index("ix_fuel_purchase_items_eligibility", "fuel_purchase_items", ["metric_eligibility_status"])

    op.create_table(
        "nfe_xml_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("station_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("stations.id"), nullable=False),
        sa.Column(
            "purchase_invoice_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("fuel_purchase_invoices.id"),
            nullable=True,
        ),
        sa.Column("access_key", sa.String(44), nullable=False),
        sa.Column("issuer_cnpj", sa.String(14), nullable=False),
        sa.Column("recipient_cnpj", sa.String(14), nullable=False),
        sa.Column("document_number", sa.String(100), nullable=False),
        sa.Column("series", sa.String(20), nullable=False),
        sa.Column("issue_datetime", sa.DateTime(timezone=True), nullable=False),
        sa.Column("total_amount", sa.Numeric(22, 4), nullable=False),
        sa.Column("xml_sha256", sa.String(64), nullable=False),
        sa.Column("xml_storage_key", sa.String(512), nullable=False),
        sa.Column("xml_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("parse_status", sa.String(30), nullable=False, server_default="PENDING"),
        sa.Column("parse_errors", postgresql.JSONB(), nullable=True),
        sa.Column("reconciliation_status", sa.String(40), nullable=False, server_default="PENDING"),
        sa.Column("reconciliation_details", postgresql.JSONB(), nullable=True),
        sa.Column("imported_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("organization_id", "access_key", name="uq_nfe_xml_documents_access_key"),
    )
    op.create_index("ix_nfe_xml_documents_station", "nfe_xml_documents", ["station_id"])
    op.create_index("ix_nfe_xml_documents_parse", "nfe_xml_documents", ["parse_status"])
    op.create_index("ix_nfe_xml_documents_recon", "nfe_xml_documents", ["reconciliation_status"])

    op.create_table(
        "accounts_payable_titles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("station_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("stations.id"), nullable=False),
        sa.Column("source_title_id", sa.String(100), nullable=False),
        sa.Column("source_invoice_id", sa.String(100), nullable=True),
        sa.Column(
            "purchase_invoice_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("fuel_purchase_invoices.id"),
            nullable=True,
        ),
        sa.Column("source_supplier_id", sa.String(100), nullable=False),
        sa.Column("erp_supplier_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("erp_suppliers.id"), nullable=True),
        sa.Column("distributor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("distributors.id"), nullable=True),
        sa.Column("installment_number", sa.Integer(), nullable=True),
        sa.Column("document_number", sa.String(100), nullable=True),
        sa.Column("issue_date", sa.Date(), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("payment_date", sa.Date(), nullable=True),
        sa.Column("original_amount", sa.Numeric(22, 4), nullable=False),
        sa.Column("paid_amount", sa.Numeric(22, 4), nullable=True),
        sa.Column("open_amount", sa.Numeric(22, 4), nullable=False),
        sa.Column("interest_amount", sa.Numeric(22, 4), nullable=True),
        sa.Column("penalty_amount", sa.Numeric(22, 4), nullable=True),
        sa.Column("discount_amount", sa.Numeric(22, 4), nullable=True),
        sa.Column("source_status", sa.String(80), nullable=False),
        sa.Column("normalized_status", sa.String(40), nullable=False, server_default="UNKNOWN"),
        sa.Column("is_cancelled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("payment_method", sa.String(80), nullable=True),
        sa.Column("source_record_hash", sa.String(64), nullable=False),
        sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_sync_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("erp_sync_runs.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("station_id", "source_title_id", name="uq_accounts_payable_titles_natural_key"),
    )
    op.create_index("ix_accounts_payable_titles_due", "accounts_payable_titles", ["due_date"])
    op.create_index("ix_accounts_payable_titles_status", "accounts_payable_titles", ["normalized_status"])
    op.create_index("ix_accounts_payable_titles_supplier", "accounts_payable_titles", ["source_supplier_id"])

    op.create_table(
        "fuel_purchase_daily_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("station_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("stations.id"), nullable=False),
        sa.Column("business_date", sa.Date(), nullable=False),
        sa.Column("canonical_product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("products.id"), nullable=True),
        sa.Column("distributor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("distributors.id"), nullable=True),
        sa.Column("invoice_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("item_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("purchased_volume_liters", sa.Numeric(22, 6), nullable=False, server_default="0"),
        sa.Column("gross_purchase_amount", sa.Numeric(24, 4), nullable=False, server_default="0"),
        sa.Column("discount_amount", sa.Numeric(24, 4), nullable=False, server_default="0"),
        sa.Column("freight_amount", sa.Numeric(24, 4), nullable=False, server_default="0"),
        sa.Column("other_expenses_amount", sa.Numeric(24, 4), nullable=False, server_default="0"),
        sa.Column("commercial_delivered_cost", sa.Numeric(24, 4), nullable=False, server_default="0"),
        sa.Column("average_delivered_cost_per_liter", sa.Numeric(20, 8), nullable=True),
        sa.Column("erp_recorded_cost", sa.Numeric(24, 4), nullable=True),
        sa.Column("unmapped_item_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unmapped_volume_liters", sa.Numeric(22, 6), nullable=False, server_default="0"),
        sa.Column("missing_cost_item_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_rebuilt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_sync_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("erp_sync_runs.id"), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.UniqueConstraint(
            "organization_id",
            "station_id",
            "business_date",
            "canonical_product_id",
            "distributor_id",
            name="uq_fuel_purchase_daily_metrics_key",
        ),
    )
    op.create_index(
        "ix_fuel_purchase_daily_metrics_station_date",
        "fuel_purchase_daily_metrics",
        ["station_id", "business_date"],
    )


def downgrade() -> None:
    op.drop_table("fuel_purchase_daily_metrics")
    op.drop_table("accounts_payable_titles")
    op.drop_table("nfe_xml_documents")
    op.drop_table("fuel_purchase_items")
    op.drop_index("uq_fuel_purchase_invoices_org_access_key", table_name="fuel_purchase_invoices")
    op.drop_table("fuel_purchase_invoices")
