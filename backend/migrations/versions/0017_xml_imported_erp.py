"""Sprint 7.1 — xml_imported_in_erp em notas de compra."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0017_xml_imported_erp"
down_revision: str | None = "0016_ap_invoice_link"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "fuel_purchase_invoices",
        sa.Column(
            "xml_imported_in_erp",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("fuel_purchase_invoices", "xml_imported_in_erp")
