from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.distributor import Distributor
from app.models.quote import Quote
from app.models.quote_item import QuoteItem


@dataclass
class QuoteCandidate:
    quote: Quote
    item: QuoteItem
    distributor_name: str
    distribution_base_name: str | None


class QuoteCandidateService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    def item_effective_valid_until(self, item: QuoteItem, quote: Quote) -> datetime:
        if item.valid_until is not None:
            return self._as_utc(item.valid_until)
        return self._as_utc(quote.valid_until)

    def was_quote_known_at(self, quote: Quote, comparison_datetime: datetime) -> bool:
        if quote.activated_at is None:
            return False
        return self._as_utc(quote.activated_at) <= self._as_utc(comparison_datetime)

    def was_quote_active_at(self, quote: Quote, comparison_datetime: datetime) -> bool:
        comp = self._as_utc(comparison_datetime)
        if not self.was_quote_known_at(quote, comp):
            return False
        if quote.cancelled_at is not None and self._as_utc(quote.cancelled_at) <= comp:
            return False
        if quote.superseded_at is not None and self._as_utc(quote.superseded_at) <= comp:
            return False
        if self._as_utc(quote.valid_until) <= comp:
            return False
        return True

    def was_item_valid_at(self, item: QuoteItem, quote: Quote, comparison_datetime: datetime) -> bool:
        return self.item_effective_valid_until(item, quote) > self._as_utc(comparison_datetime)

    async def find_candidates(
        self,
        *,
        organization_id: uuid.UUID,
        station_id: uuid.UUID,
        product_id: uuid.UUID,
        comparison_datetime: datetime,
    ) -> list[QuoteCandidate]:
        comp = self._as_utc(comparison_datetime)
        query = (
            select(Quote, QuoteItem, Distributor)
            .join(QuoteItem, QuoteItem.quote_id == Quote.id)
            .join(Distributor, Distributor.id == Quote.distributor_id)
            .where(
                Quote.organization_id == organization_id,
                Quote.station_id == station_id,
                QuoteItem.product_id == product_id,
                Quote.activated_at.isnot(None),
                Quote.activated_at <= comp,
                Quote.analytics_eligible.is_(True),
                or_(Quote.cancelled_at.is_(None), Quote.cancelled_at > comp),
                or_(Quote.superseded_at.is_(None), Quote.superseded_at > comp),
                Quote.valid_until > comp,
            )
            .order_by(Quote.activated_at.desc(), Quote.quote_number.desc(), QuoteItem.sequence)
        )
        rows = (await self.db.execute(query)).all()
        candidates: list[QuoteCandidate] = []
        for quote, item, distributor in rows:
            candidates.append(
                QuoteCandidate(
                    quote=quote,
                    item=item,
                    distributor_name=distributor.trade_name or distributor.corporate_name,
                    distribution_base_name=None,
                )
            )
        return candidates
