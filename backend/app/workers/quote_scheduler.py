"""Scheduler periódico de expiração de cotações (Sprint 3.1)."""

from __future__ import annotations

import asyncio
import sys

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.logging import configure_logging, get_logger
from app.services.quote_expiration_service import QuoteExpirationService

logger = get_logger(__name__)


async def run_once() -> None:
    async with AsyncSessionLocal() as session:
        service = QuoteExpirationService(session)
        result = await service.run(origin="SCHEDULER")
        await session.commit()
        logger.info("quote_scheduler_run result=%s", result)


async def main() -> None:
    configure_logging()
    interval_seconds = max(60, settings.quote_expiration_interval_minutes * 60)
    logger.info(
        "quote_scheduler_started interval_minutes=%s",
        settings.quote_expiration_interval_minutes,
    )
    while True:
        try:
            await run_once()
        except Exception:
            logger.exception("quote_scheduler_run_failed")
        await asyncio.sleep(interval_seconds)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("quote_scheduler_stopped")
        sys.exit(0)
