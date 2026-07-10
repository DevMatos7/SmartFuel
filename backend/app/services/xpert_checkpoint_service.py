from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.xpert_sync_enums import ErpCheckpointType, ErpSyncRunStatus
from app.models.erp_integration import ErpDataset, ErpSource, ErpSyncCheckpoint, ErpSyncRun


class XpertCheckpointService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_or_create(
        self,
        *,
        source: ErpSource,
        dataset: ErpDataset,
        station_id: uuid.UUID | None,
    ) -> ErpSyncCheckpoint:
        result = await self.db.execute(
            select(ErpSyncCheckpoint).where(
                ErpSyncCheckpoint.erp_source_id == source.id,
                ErpSyncCheckpoint.erp_dataset_id == dataset.id,
                ErpSyncCheckpoint.station_id == station_id,
            )
        )
        checkpoint = result.scalar_one_or_none()
        if checkpoint is not None:
            return checkpoint
        checkpoint = ErpSyncCheckpoint(
            erp_source_id=source.id,
            erp_dataset_id=dataset.id,
            station_id=station_id,
            checkpoint_type=dataset.checkpoint_type,
        )
        self.db.add(checkpoint)
        await self.db.flush()
        return checkpoint

    def compute_window(
        self,
        *,
        dataset: ErpDataset,
        checkpoint: ErpSyncCheckpoint,
        source_upper_bound: datetime,
    ) -> tuple[datetime | None, datetime]:
        overlap = timedelta(seconds=dataset.overlap_seconds)
        if checkpoint.watermark_value:
            try:
                start = datetime.fromisoformat(checkpoint.watermark_value.replace("Z", "+00:00"))
                if start.tzinfo is None:
                    start = start.replace(tzinfo=UTC)
                return start - overlap, source_upper_bound
            except ValueError:
                pass
        return None, source_upper_bound

    async def advance_after_success(
        self,
        *,
        checkpoint: ErpSyncCheckpoint,
        run: ErpSyncRun,
        new_watermark: str | None,
        source_upper_bound: datetime | None,
    ) -> None:
        checkpoint.watermark_value = new_watermark
        if source_upper_bound is not None:
            checkpoint.source_upper_bound = source_upper_bound.isoformat()
        checkpoint.last_success_run_id = run.id
        checkpoint.last_success_at = datetime.now(UTC)
        checkpoint.updated_at = datetime.now(UTC)
        run.checkpoint_after = new_watermark

    async def reset(
        self,
        *,
        checkpoint: ErpSyncCheckpoint,
        mode: str,
        new_value: str | None,
    ) -> None:
        if mode == "CLEAR":
            checkpoint.watermark_value = None
            checkpoint.source_upper_bound = None
        else:
            checkpoint.watermark_value = new_value
        checkpoint.last_success_run_id = None
        checkpoint.last_success_at = None
        checkpoint.updated_at = datetime.now(UTC)

    def watermark_for_run(self, run: ErpSyncRun, dataset: ErpDataset) -> str | None:
        if dataset.checkpoint_type == ErpCheckpointType.TIMESTAMP and run.source_upper_bound:
            return run.source_upper_bound.isoformat()
        if dataset.checkpoint_type == ErpCheckpointType.MONOTONIC_ID and run.checkpoint_after:
            return run.checkpoint_after
        if run.source_upper_bound:
            return run.source_upper_bound.isoformat()
        return datetime.now(UTC).isoformat()

    def should_advance(self, run: ErpSyncRun, dataset: ErpDataset) -> bool:
        if run.status not in (ErpSyncRunStatus.COMPLETED,):
            return False
        if run.rows_error > 0 or run.rows_quarantined > 0:
            return dataset.allow_partial_checkpoint
        return True
