from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.xpert_sync_enums import ErpSyncRunStatus
from app.integrations.xpert.odbc_health import driver_available
from app.models.erp_integration import ErpSyncRun, XpertWorkerStatus

ACTIVE_PROCESSING = {
    ErpSyncRunStatus.CONNECTING,
    ErpSyncRunStatus.EXTRACTING,
    ErpSyncRunStatus.STAGING,
    ErpSyncRunStatus.VALIDATING,
    ErpSyncRunStatus.APPLYING,
    ErpSyncRunStatus.CANCELLATION_REQUESTED,
}


class XpertWorkerService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def record_heartbeat(self, worker_id: str, *, last_error: str | None = None) -> None:
        odbc_ok, _ = driver_available()
        row = await self.db.get(XpertWorkerStatus, worker_id)
        now = datetime.now(UTC)
        if row is None:
            self.db.add(
                XpertWorkerStatus(
                    worker_id=worker_id,
                    last_heartbeat_at=now,
                    odbc_available=odbc_ok,
                    driver_name=settings.xpert_odbc_driver,
                    last_error=last_error,
                )
            )
        else:
            row.last_heartbeat_at = now
            row.odbc_available = odbc_ok
            row.driver_name = settings.xpert_odbc_driver
            row.last_error = last_error
        await self.db.flush()

    async def touch_run_heartbeat(self, run_id) -> None:
        await self.db.execute(
            update(ErpSyncRun)
            .where(ErpSyncRun.id == run_id)
            .values(last_heartbeat_at=datetime.now(UTC))
        )

    async def recover_abandoned_runs(self) -> int:
        cutoff = datetime.now(UTC) - timedelta(seconds=settings.xpert_worker_heartbeat_timeout_seconds)
        result = await self.db.execute(
            select(ErpSyncRun).where(
                ErpSyncRun.status.in_(list(ACTIVE_PROCESSING)),
                ErpSyncRun.last_heartbeat_at.is_not(None),
                ErpSyncRun.last_heartbeat_at < cutoff,
            )
        )
        count = 0
        now = datetime.now(UTC)
        for run in result.scalars().all():
            run.status = ErpSyncRunStatus.FAILED
            run.error_code = "FAILED_WORKER_LOST"
            run.error_message = "Execução abandonada após perda de heartbeat do worker."
            run.finished_at = now
            count += 1
        await self.db.flush()
        return count

    async def latest_worker_status(self) -> XpertWorkerStatus | None:
        result = await self.db.execute(
            select(XpertWorkerStatus).order_by(XpertWorkerStatus.last_heartbeat_at.desc()).limit(1)
        )
        return result.scalar_one_or_none()
