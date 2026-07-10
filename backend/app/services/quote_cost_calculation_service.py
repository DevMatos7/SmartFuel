from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.domain.quote_comparison.formulas import (
    compute_daily_rate,
    compute_delivered_cost_per_liter,
    compute_financial_equivalent_cost_per_liter,
    compute_freight_per_liter,
    compute_total,
)
from app.models.financial_parameter import FinancialParameter
from app.services.quote_candidate_service import QuoteCandidate
from app.services.quote_eligibility_service import QuoteEligibilityService


@dataclass
class CostBreakdown:
    raw_price_per_liter: Decimal
    discount_per_liter: Decimal
    rebate_per_liter: Decimal
    freight_per_liter: Decimal
    other_cost_per_liter: Decimal
    delivered_cost_per_liter: Decimal
    delivered_total: Decimal
    financial_days: int
    annual_effective_rate: Decimal | None
    daily_rate: Decimal | None
    financial_equivalent_cost_per_liter: Decimal | None
    financial_equivalent_total: Decimal | None
    calculation_snapshot: dict


class QuoteCostCalculationService:
    def __init__(self, eligibility_service: QuoteEligibilityService) -> None:
        self.eligibility = eligibility_service

    def calculate(
        self,
        candidate: QuoteCandidate,
        *,
        requested_volume_liters: Decimal,
        financial_parameter: FinancialParameter | None,
    ) -> CostBreakdown:
        item = candidate.item
        discount = item.discount_per_liter or Decimal("0")
        rebate = item.rebate_per_liter or Decimal("0")
        other = item.other_cost_per_liter or Decimal("0")
        freight = compute_freight_per_liter(
            freight_calculation_type=item.freight_calculation_type,
            freight_value_per_liter=item.freight_value_per_liter,
            freight_value_total=item.freight_value_total,
            requested_volume_liters=requested_volume_liters,
        )
        delivered = compute_delivered_cost_per_liter(
            quoted_price_per_liter=item.quoted_price_per_liter,
            discount_per_liter=discount,
            rebate_per_liter=rebate,
            freight_per_liter=freight,
            other_cost_per_liter=other,
        )
        delivered_total = compute_total(
            cost_per_liter=delivered,
            requested_volume_liters=requested_volume_liters,
        )

        financial_days = self.eligibility.financial_days_from_snapshot(
            item.payment_type_snapshot,
            item.payment_term_days_snapshot,
        )
        annual_rate: Decimal | None = None
        daily_rate: Decimal | None = None
        equivalent: Decimal | None = None
        equivalent_total: Decimal | None = None

        if financial_parameter is not None:
            annual_rate = financial_parameter.annual_effective_rate
            daily_rate = compute_daily_rate(
                annual_effective_rate=annual_rate,
                day_count_basis=financial_parameter.day_count_basis,
            )
            equivalent = compute_financial_equivalent_cost_per_liter(
                delivered_cost_per_liter=delivered,
                daily_rate=daily_rate,
                financial_days=financial_days,
            )
            equivalent_total = compute_total(
                cost_per_liter=equivalent,
                requested_volume_liters=requested_volume_liters,
            )

        snapshot = {
            "formulas": {
                "delivered_cost_per_liter": (
                    "quoted_price - discount - rebate + freight + other_cost"
                ),
                "financial_equivalent_cost_per_liter": (
                    "delivered_cost / (1 + daily_rate) ^ financial_days"
                ),
                "daily_rate": "(1 + annual_rate) ^ (1/day_basis) - 1",
            },
            "inputs": {
                "quoted_price_per_liter": str(item.quoted_price_per_liter),
                "discount_per_liter": str(discount),
                "rebate_per_liter": str(rebate),
                "freight_per_liter": str(freight),
                "other_cost_per_liter": str(other),
                "freight_calculation_type": item.freight_calculation_type,
                "requested_volume_liters": str(requested_volume_liters),
                "financial_days": financial_days,
                "payment_type_snapshot": item.payment_type_snapshot,
                "payment_term_days_snapshot": item.payment_term_days_snapshot,
            },
        }

        return CostBreakdown(
            raw_price_per_liter=item.quoted_price_per_liter,
            discount_per_liter=discount,
            rebate_per_liter=rebate,
            freight_per_liter=freight,
            other_cost_per_liter=other,
            delivered_cost_per_liter=delivered,
            delivered_total=delivered_total,
            financial_days=financial_days,
            annual_effective_rate=annual_rate,
            daily_rate=daily_rate,
            financial_equivalent_cost_per_liter=equivalent,
            financial_equivalent_total=equivalent_total,
            calculation_snapshot=snapshot,
        )
