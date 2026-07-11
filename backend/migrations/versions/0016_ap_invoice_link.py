"""Sprint 7.1 — link_status em títulos a pagar."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0016_ap_invoice_link"
down_revision: str | None = "0015_sprint7_purchases"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "accounts_payable_titles",
        sa.Column(
            "invoice_link_status",
            sa.String(40),
            nullable=False,
            server_default="PENDING_INVOICE_LINK",
        ),
    )
    op.create_index(
        "ix_accounts_payable_titles_link_status",
        "accounts_payable_titles",
        ["invoice_link_status"],
    )


def downgrade() -> None:
    op.drop_index("ix_accounts_payable_titles_link_status", table_name="accounts_payable_titles")
    op.drop_column("accounts_payable_titles", "invoice_link_status")
