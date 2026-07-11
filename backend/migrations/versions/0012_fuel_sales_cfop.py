"""Adiciona CFOP aos fatos de venda."""

from alembic import op
import sqlalchemy as sa

revision = "0012_fuel_sales_cfop"
down_revision = "0011_sprint6_fuel_sales"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("fuel_sales_facts", sa.Column("source_cfop", sa.String(length=20), nullable=True))
    op.add_column("fuel_sales_facts", sa.Column("cfop_classification", sa.String(length=40), nullable=True))
    op.create_index("ix_fuel_sales_facts_source_cfop", "fuel_sales_facts", ["source_cfop"])
    op.create_index("ix_fuel_sales_facts_cfop_classification", "fuel_sales_facts", ["cfop_classification"])


def downgrade() -> None:
    op.drop_index("ix_fuel_sales_facts_cfop_classification", table_name="fuel_sales_facts")
    op.drop_index("ix_fuel_sales_facts_source_cfop", table_name="fuel_sales_facts")
    op.drop_column("fuel_sales_facts", "cfop_classification")
    op.drop_column("fuel_sales_facts", "source_cfop")
