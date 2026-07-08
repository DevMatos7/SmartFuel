"""Sprint 2.1 — configuração de compra por organização."""

from collections.abc import Sequence
from decimal import Decimal

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_sprint21_org_settings"
down_revision: str | None = "0003_sprint2_master_data"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "organization_business_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id"),
            nullable=False,
        ),
        sa.Column("default_supplier_allowed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "default_minimum_volume_liters",
            sa.Numeric(16, 3),
            nullable=False,
            server_default="5000.000",
        ),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("organization_id", name="uq_org_business_settings_org"),
        sa.CheckConstraint(
            "default_minimum_volume_liters > 0",
            name="ck_org_business_settings_min_volume",
        ),
    )
    op.create_index(
        "ix_organization_business_settings_organization_id",
        "organization_business_settings",
        ["organization_id"],
    )

    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            INSERT INTO organization_business_settings (
                id, organization_id, default_supplier_allowed, default_minimum_volume_liters,
                created_at, updated_at
            )
            SELECT gen_random_uuid(), o.id, false, 5000.000, now(), now()
            FROM organizations o
            WHERE NOT EXISTS (
                SELECT 1 FROM organization_business_settings s WHERE s.organization_id = o.id
            )
            """
        )
    )


def downgrade() -> None:
    op.drop_table("organization_business_settings")
