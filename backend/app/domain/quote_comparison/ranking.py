from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any


@dataclass
class RankableOffer:
    item_id: uuid.UUID
    distributor_id: uuid.UUID
    distributor_name: str
    ranking_cost: Decimal | None
    financial_equivalent_cost: Decimal | None
    delivered_cost: Decimal
    raw_price: Decimal
    delivery_expected_at: datetime | None
    effective_valid_until: datetime
    activated_at: datetime | None
    eligibility_status: str


def tie_break_key(offer: RankableOffer) -> tuple[Any, ...]:
  delivery_sort = offer.delivery_expected_at or datetime.max.replace(tzinfo=offer.effective_valid_until.tzinfo)
  return (
      offer.ranking_cost if offer.ranking_cost is not None else Decimal("999999"),
      offer.financial_equivalent_cost if offer.financial_equivalent_cost is not None else Decimal("999999"),
      offer.delivered_cost,
      offer.raw_price,
      delivery_sort,
      -offer.effective_valid_until.timestamp(),
      -(offer.activated_at.timestamp() if offer.activated_at else 0),
      offer.distributor_name.lower(),
      str(offer.item_id),
  )


def sort_offers(offers: list[RankableOffer]) -> list[RankableOffer]:
    return sorted(offers, key=tie_break_key)
