"""Worker dedicado de sincronização XPERT (Sprint 5 / 5.1)."""

from __future__ import annotations

import asyncio
import socket
import sys
import uuid

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.logging import configure_logging, get_logger
from app.integrations.xpert.odbc_health import driver_available
from app.services.xpert_sync_service import XpertSyncService
from app.services.xpert_worker_service import XpertWorkerService

logger = get_logger(__name__)


def _worker_id() -> str:
    return f"{socket.gethostname()}-{uuid.uuid4().hex[:8]}"


async def run_once(worker_id: str) -> dict[str, int]:
    odbc_ok, odbc_msg = driver_available()
    if not odbc_ok:
        logger.warning("xpert_sync_worker_odbc_missing message=%s", odbc_msg)

    async with AsyncSessionLocal() as session:
        worker = XpertWorkerService(session)
        await worker.record_heartbeat(worker_id, last_error=None if odbc_ok else odbc_msg)
        abandoned = await worker.recover_abandoned_runs()

        if not odbc_ok:
            await session.commit()
            return {"scheduled": 0, "processed": 0, "abandoned": abandoned, "odbc": 0}

        sync = XpertSyncService(session)
        scheduled = await sync.create_scheduled_runs()
        run = await sync.claim_next_run(worker_id)
        if run is None:
            await session.commit()
            return {"scheduled": scheduled, "processed": 0, "abandoned": abandoned, "odbc": 1}
        logger.info(
            "xpert_sync_processing run_id=%s dataset_id=%s station_id=%s",
            run.id,
            run.erp_dataset_id,
            run.station_id,
        )
        try:
            await sync.process_run(run.id)
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        return {"scheduled": scheduled, "processed": 1, "abandoned": abandoned, "odbc": 1}


async def main() -> None:
    configure_logging()
    worker_id = _worker_id()
    interval = max(5, settings.xpert_sync_poll_interval_seconds)
    logger.info("xpert_sync_worker_started worker_id=%s interval=%s", worker_id, interval)
    while True:
        try:
            result = await run_once(worker_id)
            logger.info("xpert_sync_worker_tick result=%s", result)
        except Exception:
            logger.exception("xpert_sync_worker_failed")
        await asyncio.sleep(interval)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("xpert_sync_worker_stopped")
        sys.exit(0)
