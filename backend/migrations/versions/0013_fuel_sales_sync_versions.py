"""Versões de normalização/hash em erp_sync_runs."""

from alembic import op
import sqlalchemy as sa

revision = "0013_fuel_sales_sync_versions"
down_revision = "0012_fuel_sales_cfop"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "erp_sync_runs",
        sa.Column("normalization_version", sa.String(length=40), nullable=True),
    )
    op.add_column(
        "erp_sync_runs",
        sa.Column("hash_schema_version", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("erp_sync_runs", "hash_schema_version")
    op.drop_column("erp_sync_runs", "normalization_version")
