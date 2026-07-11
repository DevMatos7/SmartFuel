"""Sprint 8.3 — origem de cotação e elegibilidade analítica."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0019_sprint83_quote_origin"
down_revision: str | None = "0018_sprint8_benchmarks"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "quotes",
        sa.Column(
            "origin",
            sa.String(40),
            nullable=False,
            server_default="MANUAL_OPERATIONAL",
        ),
    )
    op.add_column(
        "quotes",
        sa.Column(
            "analytics_eligible",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )
    op.create_index("ix_quotes_origin", "quotes", ["origin"])
    op.create_index("ix_quotes_analytics_eligible", "quotes", ["analytics_eligible"])


def downgrade() -> None:
    op.drop_index("ix_quotes_analytics_eligible", table_name="quotes")
    op.drop_index("ix_quotes_origin", table_name="quotes")
    op.drop_column("quotes", "analytics_eligible")
    op.drop_column("quotes", "origin")
