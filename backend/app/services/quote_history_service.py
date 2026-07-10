from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.quote_enums import QuoteChangeAction
from app.models.quote_change_history import QuoteChangeHistory


class QuoteHistoryService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def record(
        self,
        *,
        quote_id: uuid.UUID,
        action: QuoteChangeAction | str,
        version: int,
        user_id: uuid.UUID | None = None,
        reason: str | None = None,
        quote_item_id: uuid.UUID | None = None,
        quote_evidence_id: uuid.UUID | None = None,
        changed_fields: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        request_id: uuid.UUID | None = None,
    ) -> QuoteChangeHistory:
        entry = QuoteChangeHistory(
            quote_id=quote_id,
            quote_item_id=quote_item_id,
            quote_evidence_id=quote_evidence_id,
            action=str(action),
            version=version,
            reason=reason,
            changed_fields=changed_fields,
            metadata_=metadata,
            user_id=user_id,
            request_id=request_id,
            created_at=datetime.now(UTC),
        )
        self.db.add(entry)
        await self.db.flush()
        return entry

    async def list_history(
        self,
        *,
        quote_id: uuid.UUID,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[QuoteChangeHistory], int]:
        query = select(QuoteChangeHistory).where(QuoteChangeHistory.quote_id == quote_id)
        count_q = select(func.count()).select_from(query.subquery())
        total = int((await self.db.execute(count_q)).scalar_one())
        query = (
            query.order_by(QuoteChangeHistory.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all()), total
