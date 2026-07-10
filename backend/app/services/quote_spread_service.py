from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.core.quote_comparison_enums import EligibilityStatus
from app.domain.quote_comparison.constants import LITER_PERSIST_SCALE
from app.domain.quote_comparison.formulas import quantize_decimal
from app.services.quote_ranking_service import ProcessedOffer


@dataclass
class SpreadSummary:
    eligible_count: int
    warning_count: int
    ineligible_count: int
    distributor_count: int
    best_cost_per_liter: Decimal | None
    highest_cost_per_liter: Decimal | None
    average_cost_per_liter: Decimal | None
    spread_absolute: Decimal | None
    spread_percent: Decimal | None


class QuoteSpreadService:
    def compute(self, offers: list[ProcessedOffer]) -> SpreadSummary:
        rankable_statuses = {EligibilityStatus.ELIGIBLE, EligibilityStatus.ELIGIBLE_WITH_WARNINGS}
        ranked_eligible = [
            o
            for o in offers
            if o.eligibility_status in rankable_statuses
            and o.rank_position is not None
            and o.ranking_cost_per_liter is not None
        ]
        eligible_count = sum(1 for o in offers if o.eligibility_status == EligibilityStatus.ELIGIBLE)
        warning_count = sum(
            1 for o in offers if o.eligibility_status == EligibilityStatus.ELIGIBLE_WITH_WARNINGS
        )
        ineligible_count = sum(1 for o in offers if o.eligibility_status == EligibilityStatus.INELIGIBLE)
        distributor_ids = {o.distributor_id for o in ranked_eligible}

        if not ranked_eligible:
            return SpreadSummary(
                eligible_count=eligible_count,
                warning_count=warning_count,
                ineligible_count=ineligible_count,
                distributor_count=0,
                best_cost_per_liter=None,
                highest_cost_per_liter=None,
                average_cost_per_liter=None,
                spread_absolute=None,
                spread_percent=None,
            )

        costs = [o.ranking_cost_per_liter for o in ranked_eligible if o.ranking_cost_per_liter is not None]
        best = min(costs)
        highest = max(costs)
        average = quantize_decimal(sum(costs) / Decimal(len(costs)), LITER_PERSIST_SCALE)
        spread_abs: Decimal | None = None
        spread_pct: Decimal | None = None
        if len(costs) >= 2:
            spread_abs = quantize_decimal(highest - best, LITER_PERSIST_SCALE)
            spread_pct = quantize_decimal((spread_abs / best) * Decimal("100"), LITER_PERSIST_SCALE)

        return SpreadSummary(
            eligible_count=eligible_count,
            warning_count=warning_count,
            ineligible_count=ineligible_count,
            distributor_count=len(distributor_ids),
            best_cost_per_liter=best,
            highest_cost_per_liter=highest,
            average_cost_per_liter=average,
            spread_absolute=spread_abs,
            spread_percent=spread_pct,
        )
