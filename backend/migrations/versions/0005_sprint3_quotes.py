"""Sprint 3 — central de cotações manual, evidências e histórico."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_sprint3_quotes"
down_revision: str | None = "0004_sprint21_org_settings"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "quotes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("station_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("stations.id"), nullable=False),
        sa.Column("distributor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("distributors.id"), nullable=False),
        sa.Column(
            "distribution_base_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("distribution_bases.id"),
            nullable=True,
        ),
        sa.Column("quote_number", sa.BigInteger(), nullable=False),
        sa.Column("quoted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_channel", sa.String(30), nullable=False),
        sa.Column("entry_method", sa.String(30), nullable=False, server_default="MANUAL"),
        sa.Column("seller_name", sa.String(150), nullable=True),
        sa.Column("seller_contact", sa.String(150), nullable=True),
        sa.Column("external_reference", sa.String(150), nullable=True),
        sa.Column("source_description", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="DRAFT"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("replaces_quote_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("quotes.id"), nullable=True),
        sa.Column(
            "duplicated_from_quote_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("quotes.id"),
            nullable=True,
        ),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("activated_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("cancellation_reason", sa.Text(), nullable=True),
        sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "superseded_by_quote_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("quotes.id"),
            nullable=True,
        ),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("organization_id", "quote_number", name="uq_quotes_org_number"),
        sa.CheckConstraint("version >= 1", name="ck_quotes_version_min"),
        sa.CheckConstraint("valid_until > quoted_at", name="ck_quotes_valid_until_after_quoted_at"),
    )
    op.create_index("ix_quotes_organization_id", "quotes", ["organization_id"])
    op.create_index("ix_quotes_station_id", "quotes", ["station_id"])
    op.create_index("ix_quotes_distributor_id", "quotes", ["distributor_id"])
    op.create_index("ix_quotes_status", "quotes", ["status"])
    op.create_index("ix_quotes_quoted_at", "quotes", ["quoted_at"])
    op.create_index("ix_quotes_valid_until", "quotes", ["valid_until"])
    op.create_index("ix_quotes_quote_number", "quotes", ["quote_number"])
    op.create_index("ix_quotes_replaces_quote_id", "quotes", ["replaces_quote_id"])

    op.create_table(
        "quote_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "quote_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("quotes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("products.id"), nullable=False),
        sa.Column(
            "distribution_base_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("distribution_bases.id"),
            nullable=True,
        ),
        sa.Column("sequence", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("quoted_price_per_liter", sa.Numeric(14, 4), nullable=False),
        sa.Column(
            "payment_term_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("payment_terms.id"),
            nullable=False,
        ),
        sa.Column("payment_type_snapshot", sa.String(30), nullable=False),
        sa.Column("payment_term_days_snapshot", sa.Integer(), nullable=False),
        sa.Column("payment_term_name_snapshot", sa.String(120), nullable=False),
        sa.Column("freight_type", sa.String(20), nullable=False, server_default="CIF"),
        sa.Column("freight_calculation_type", sa.String(20), nullable=False, server_default="NONE"),
        sa.Column("freight_value_total", sa.Numeric(18, 2), nullable=True),
        sa.Column("freight_value_per_liter", sa.Numeric(14, 4), nullable=True),
        sa.Column("discount_per_liter", sa.Numeric(14, 4), nullable=False, server_default="0"),
        sa.Column("rebate_per_liter", sa.Numeric(14, 4), nullable=False, server_default="0"),
        sa.Column("other_cost_per_liter", sa.Numeric(14, 4), nullable=False, server_default="0"),
        sa.Column("other_cost_description", sa.Text(), nullable=True),
        sa.Column("minimum_volume_liters", sa.Numeric(16, 3), nullable=False),
        sa.Column("available_volume_liters", sa.Numeric(16, 3), nullable=True),
        sa.Column("delivery_expected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("quoted_price_per_liter > 0", name="ck_quote_items_price_positive"),
        sa.CheckConstraint("minimum_volume_liters > 0", name="ck_quote_items_min_volume_positive"),
        sa.CheckConstraint(
            "available_volume_liters IS NULL OR available_volume_liters >= 0",
            name="ck_quote_items_available_volume_nonneg",
        ),
        sa.CheckConstraint("discount_per_liter >= 0", name="ck_quote_items_discount_nonneg"),
        sa.CheckConstraint("rebate_per_liter >= 0", name="ck_quote_items_rebate_nonneg"),
        sa.CheckConstraint("other_cost_per_liter >= 0", name="ck_quote_items_other_cost_nonneg"),
    )
    op.create_index("ix_quote_items_quote_id", "quote_items", ["quote_id"])
    op.create_index("ix_quote_items_product_id", "quote_items", ["product_id"])
    op.create_index("ix_quote_items_payment_term_id", "quote_items", ["payment_term_id"])
    op.create_index("ix_quote_items_valid_until", "quote_items", ["valid_until"])

    op.create_table(
        "quote_evidences",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "quote_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("quotes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("category", sa.String(30), nullable=False),
        sa.Column("original_file_name", sa.String(255), nullable=False),
        sa.Column("stored_file_name", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(120), nullable=False),
        sa.Column("file_extension", sa.String(20), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("storage_key", sa.String(500), nullable=False),
        sa.Column("is_supplemental", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("uploaded_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deactivated_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("deactivated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deactivation_reason", sa.Text(), nullable=True),
    )
    op.create_index("ix_quote_evidences_quote_id", "quote_evidences", ["quote_id"])
    op.create_index("ix_quote_evidences_sha256", "quote_evidences", ["sha256"])
    op.create_index("ix_quote_evidences_active", "quote_evidences", ["active"])

    op.create_table(
        "quote_change_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "quote_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("quotes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "quote_item_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("quote_items.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "quote_evidence_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("quote_evidences.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("changed_fields", postgresql.JSONB(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_quote_change_history_quote_id", "quote_change_history", ["quote_id"])
    op.create_index("ix_quote_change_history_created_at", "quote_change_history", ["created_at"])


def downgrade() -> None:
    op.drop_table("quote_change_history")
    op.drop_table("quote_evidences")
    op.drop_table("quote_items")
    op.drop_table("quotes")
