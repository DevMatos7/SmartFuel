from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.logging import get_logger
from app.core.quote_enums import QuoteChangeAction, QuoteStatus
from app.models.quote import Quote
from app.services.audit_service import AuditContext, AuditService
from app.services.quote_history_service import QuoteHistoryService
from app.services.quote_service import QuoteService

logger = get_logger(__name__)

QUOTE_EXPIRATION_ADVISORY_LOCK_KEY = 738_291_047


class QuoteExpirationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.history = QuoteHistoryService(db)
        self.audit = AuditService(db)
        self.quote_service = QuoteService(db)

    async def _try_acquire_lock(self) -> bool:
        result = await self.db.execute(
            text("SELECT pg_try_advisory_lock(:key)"),
            {"key": QUOTE_EXPIRATION_ADVISORY_LOCK_KEY},
        )
        return bool(result.scalar())

    async def _release_lock(self) -> None:
        await self.db.execute(
            text("SELECT pg_advisory_unlock(:key)"),
            {"key": QUOTE_EXPIRATION_ADVISORY_LOCK_KEY},
        )

    async def run(
        self,
        *,
        organization_id: uuid.UUID | None = None,
        origin: str = "SYSTEM",
    ) -> dict[str, int | bool | str]:
        if not await self._try_acquire_lock():
            logger.info("quote_expiration_skipped reason=lock_not_acquired origin=%s", origin)
            return {
                "expired_count": 0,
                "skipped": True,
                "reason": "lock_not_acquired",
            }

        try:
            now = datetime.now(UTC)
            query = (
                select(Quote)
                .options(selectinload(Quote.items))
                .where(Quote.status == QuoteStatus.ACTIVE)
                .limit(settings.quote_expiration_batch_size)
            )
            if organization_id:
                query = query.where(Quote.organization_id == organization_id)

            result = await self.db.execute(query)
            expired_count = 0
            for quote in result.scalars().all():
                effective = self.quote_service.compute_effective_status(quote, now=now)
                if effective != QuoteStatus.EXPIRED:
                    continue
                quote.status = QuoteStatus.EXPIRED
                quote.version += 1
                await self.history.record(
                    quote_id=quote.id,
                    action=QuoteChangeAction.EXPIRED,
                    version=quote.version,
                    user_id=None,
                    metadata={"expired_at": now.isoformat(), "origin": origin},
                )
                await self.audit.log(
                    ctx=AuditContext(
                        organization_id=quote.organization_id,
                        user_id=None,
                        request_id=None,
                        ip_address=None,
                    ),
                    entity_type="quote",
                    entity_id=quote.id,
                    action="expire",
                    after_data={"status": QuoteStatus.EXPIRED, "origin": origin},
                )
                expired_count += 1

            logger.info(
                "quote_expiration_completed origin=%s expired_count=%s",
                origin,
                expired_count,
            )
            return {"expired_count": expired_count, "skipped": False}
        finally:
            await self._release_lock()
