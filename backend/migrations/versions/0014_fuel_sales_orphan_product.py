"""Permite fatos com referência ERP de produto ausente (histórico)."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0014_fuel_sales_orphan_product"
down_revision = "0013_fuel_sales_sync_versions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "fuel_sales_facts",
        sa.Column("source_product_id", sa.String(length=100), nullable=True),
    )
    op.create_index("ix_fuel_sales_facts_source_product_id", "fuel_sales_facts", ["source_product_id"])
    op.alter_column(
        "fuel_sales_facts",
        "erp_product_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "fuel_sales_facts",
        "erp_product_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
    op.drop_index("ix_fuel_sales_facts_source_product_id", table_name="fuel_sales_facts")
    op.drop_column("fuel_sales_facts", "source_product_id")
