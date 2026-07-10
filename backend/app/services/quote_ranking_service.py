from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.core.quote_comparison_enums import EligibilityStatus, RankingMode, RankingScope
from app.domain.quote_comparison.ranking import RankableOffer, sort_offers


@dataclass
class ProcessedOffer:
    quote_id: uuid.UUID
    quote_item_id: uuid.UUID
    distributor_id: uuid.UUID
    eligibility_status: str
    raw_price_per_liter: Decimal
    delivered_cost_per_liter: Decimal
    financial_equivalent_cost_per_liter: Decimal | None
    ranking_cost_per_liter: Decimal | None
    rank_position: int | None = None
    is_best_for_distributor: bool = False
    is_best_overall: bool = False
    difference_per_liter: Decimal | None = None
    difference_total: Decimal | None = None
    distributor_name: str = ""
    delivery_expected_at: datetime | None = None
    effective_valid_until: datetime | None = None
    activated_at: datetime | None = None


class QuoteRankingService:
    @staticmethod
    def ranking_cost(
        *,
        ranking_mode: str,
        raw_price: Decimal,
        delivered_cost: Decimal,
        financial_equivalent: Decimal | None,
    ) -> Decimal | None:
        if ranking_mode == RankingMode.RAW:
            return raw_price
        if ranking_mode == RankingMode.DELIVERED:
            return delivered_cost
        if ranking_mode == RankingMode.FINANCIAL_EQUIVALENT:
            return financial_equivalent
        return delivered_cost

    def apply_ranking(
        self,
        offers: list[ProcessedOffer],
        *,
        ranking_mode: str,
        ranking_scope: str,
        requested_volume_liters: Decimal,
    ) -> list[ProcessedOffer]:
        rankable_statuses = {EligibilityStatus.ELIGIBLE, EligibilityStatus.ELIGIBLE_WITH_WARNINGS}
        eligible = [o for o in offers if o.eligibility_status in rankable_statuses and o.ranking_cost_per_liter is not None]

        for offer in eligible:
            if offer.ranking_cost_per_liter is None:
                offer.ranking_cost_per_liter = self.ranking_cost(
                    ranking_mode=ranking_mode,
                    raw_price=offer.raw_price_per_liter,
                    delivered_cost=offer.delivered_cost_per_liter,
                    financial_equivalent=offer.financial_equivalent_cost_per_liter,
                )

        rankable = [
            RankableOffer(
                item_id=offer.quote_item_id,
                distributor_id=offer.distributor_id,
                distributor_name=offer.distributor_name,
                ranking_cost=offer.ranking_cost_per_liter,
                financial_equivalent_cost=offer.financial_equivalent_cost_per_liter,
                delivered_cost=offer.delivered_cost_per_liter,
                raw_price=offer.raw_price_per_liter,
                delivery_expected_at=offer.delivery_expected_at,
                effective_valid_until=offer.effective_valid_until or datetime.max.replace(tzinfo=datetime.now().astimezone().tzinfo),
                activated_at=offer.activated_at,
                eligibility_status=offer.eligibility_status,
            )
            for offer in eligible
        ]

        best_by_distributor: dict[uuid.UUID, ProcessedOffer] = {}
        for offer in eligible:
            current = best_by_distributor.get(offer.distributor_id)
            if current is None:
                best_by_distributor[offer.distributor_id] = offer
                continue
            current_rankable = next(r for r in rankable if r.item_id == current.quote_item_id)
            offer_rankable = next(r for r in rankable if r.item_id == offer.quote_item_id)
            if sort_offers([offer_rankable, current_rankable])[0].item_id == offer.quote_item_id:
                best_by_distributor[offer.distributor_id] = offer

        for dist_id, best in best_by_distributor.items():
            best.is_best_for_distributor = True

        if ranking_scope == RankingScope.BEST_PER_DISTRIBUTOR:
            ranking_pool = list(best_by_distributor.values())
            pool_rankable = [
                next(r for r in rankable if r.item_id == offer.quote_item_id) for offer in ranking_pool
            ]
        else:
            ranking_pool = eligible
            pool_rankable = rankable

        ordered = sort_offers(pool_rankable)
        ordered_ids = [r.item_id for r in ordered]
        best_cost = ordered[0].ranking_cost if ordered else None

        position = 1
        for item_id in ordered_ids:
            offer = next(o for o in ranking_pool if o.quote_item_id == item_id)
            offer.rank_position = position
            if position == 1:
                offer.is_best_overall = True
            if best_cost is not None and offer.ranking_cost_per_liter is not None:
                diff = offer.ranking_cost_per_liter - best_cost
                offer.difference_per_liter = diff
                offer.difference_total = diff * requested_volume_liters
            position += 1

        ineligible = [o for o in offers if o.eligibility_status not in rankable_statuses]
        non_ranked_eligible = [o for o in eligible if o.rank_position is None]
        return sorted(
            [o for o in offers if o.rank_position is not None]
            + non_ranked_eligible
            + ineligible,
            key=lambda o: (o.rank_position is None, o.rank_position or 999999, o.distributor_name.lower(), str(o.quote_item_id)),
        )
