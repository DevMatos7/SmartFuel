"""Sprint 4.1 — estabilização do motor de comparação."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008_sprint41_stabilization"
down_revision: str | None = "0007_sprint4_comparisons"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
    op.execute(
        """
        ALTER TABLE financial_parameters
        ADD CONSTRAINT ex_financial_parameters_no_overlap
        EXCLUDE USING gist (
            organization_id WITH =,
            tstzrange(valid_from, COALESCE(valid_until, 'infinity'::timestamptz), '[)') WITH &&
        )
        WHERE (active = true)
        """
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE financial_parameters DROP CONSTRAINT IF EXISTS ex_financial_parameters_no_overlap"
    )
