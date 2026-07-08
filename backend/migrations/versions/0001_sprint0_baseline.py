"""Revisão inicial da Sprint 0 — sem tabelas de negócio.

Alembic fica operacional; models entram a partir da Sprint 1.
"""

from collections.abc import Sequence

revision: str = "0001_sprint0_baseline"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
