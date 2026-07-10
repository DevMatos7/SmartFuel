"""Sprint 5.1 — estabilização XPERT: checkpoints, heartbeat e worker status."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0010_sprint51"
down_revision: str | None = "0009_sprint5_xpert"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "erp_sync_runs",
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_erp_sync_runs_last_heartbeat_at", "erp_sync_runs", ["last_heartbeat_at"])

    op.create_table(
        "xpert_worker_status",
        sa.Column("worker_id", sa.String(150), primary_key=True, nullable=False),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("odbc_available", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("driver_name", sa.String(150), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
    )
    op.create_index("ix_xpert_worker_status_last_heartbeat_at", "xpert_worker_status", ["last_heartbeat_at"])

    op.drop_constraint(
        "uq_erp_sync_checkpoints_source_dataset_station",
        "erp_sync_checkpoints",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_erp_sync_checkpoints_source_dataset_station",
        "erp_sync_checkpoints",
        ["erp_source_id", "erp_dataset_id", "station_id"],
        postgresql_nulls_not_distinct=True,
    )

    op.create_index(
        "ix_erp_sync_runs_active_lookup",
        "erp_sync_runs",
        ["erp_source_id", "erp_dataset_id", "station_id", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_erp_sync_runs_active_lookup", table_name="erp_sync_runs")
    op.drop_constraint(
        "uq_erp_sync_checkpoints_source_dataset_station",
        "erp_sync_checkpoints",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_erp_sync_checkpoints_source_dataset_station",
        "erp_sync_checkpoints",
        ["erp_source_id", "erp_dataset_id", "station_id"],
    )
    op.drop_index("ix_xpert_worker_status_last_heartbeat_at", table_name="xpert_worker_status")
    op.drop_table("xpert_worker_status")
    op.drop_index("ix_erp_sync_runs_last_heartbeat_at", table_name="erp_sync_runs")
    op.drop_column("erp_sync_runs", "last_heartbeat_at")
