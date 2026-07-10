"""Sprint 3.1 — estabilização de cotações (contador, source_evidence_id)."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006_sprint31_quotes"
down_revision: str | None = "0005_sprint3_quotes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "organization_quote_counters",
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("next_number", sa.BigInteger(), nullable=False, server_default="1"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
    )

    op.add_column(
        "quote_evidences",
        sa.Column("source_evidence_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_quote_evidences_source_evidence_id",
        "quote_evidences",
        "quote_evidences",
        ["source_evidence_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_quote_evidences_source_evidence_id",
        "quote_evidences",
        ["source_evidence_id"],
    )

    op.execute(
        """
        INSERT INTO organization_quote_counters (organization_id, next_number)
        SELECT organization_id, COALESCE(MAX(quote_number), 0) + 1
        FROM quotes
        GROUP BY organization_id
        ON CONFLICT (organization_id) DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_index("ix_quote_evidences_source_evidence_id", table_name="quote_evidences")
    op.drop_constraint("fk_quote_evidences_source_evidence_id", "quote_evidences", type_="foreignkey")
    op.drop_column("quote_evidences", "source_evidence_id")
    op.drop_table("organization_quote_counters")
