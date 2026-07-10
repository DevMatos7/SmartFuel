from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from app.core.quote_enums import FreightCalculationType
from app.domain.quote_comparison.constants import (
    LITER_PERSIST_SCALE,
    RATE_PERSIST_SCALE,
    TOTAL_PERSIST_SCALE,
)


def quantize_decimal(value: Decimal, scale: Decimal) -> Decimal:
    return value.quantize(scale, rounding=ROUND_HALF_UP)


def _q(value: Decimal, scale: Decimal) -> Decimal:
    return quantize_decimal(value, scale)


def compute_daily_rate(*, annual_effective_rate: Decimal, day_count_basis: int) -> Decimal:
    if annual_effective_rate <= 0:
        return Decimal("0")
    one = Decimal("1")
    basis = Decimal(str(day_count_basis))
    rate = (one + annual_effective_rate) ** (one / basis) - one
    return _q(rate, RATE_PERSIST_SCALE)


def compute_freight_per_liter(
    *,
    freight_calculation_type: str,
    freight_value_per_liter: Decimal | None,
    freight_value_total: Decimal | None,
    requested_volume_liters: Decimal,
) -> Decimal:
    if freight_calculation_type == FreightCalculationType.PER_LITER:
        return freight_value_per_liter or Decimal("0")
    if freight_calculation_type == FreightCalculationType.TOTAL:
        if not freight_value_total or requested_volume_liters <= 0:
            return Decimal("0")
        return _q(freight_value_total / requested_volume_liters, LITER_PERSIST_SCALE)
    return Decimal("0")


def compute_delivered_cost_per_liter(
    *,
    quoted_price_per_liter: Decimal,
    discount_per_liter: Decimal,
    rebate_per_liter: Decimal,
    freight_per_liter: Decimal,
    other_cost_per_liter: Decimal,
) -> Decimal:
    value = (
        quoted_price_per_liter
        - discount_per_liter
        - rebate_per_liter
        + freight_per_liter
        + other_cost_per_liter
    )
    return _q(value, LITER_PERSIST_SCALE)


def compute_financial_equivalent_cost_per_liter(
    *,
    delivered_cost_per_liter: Decimal,
    daily_rate: Decimal,
    financial_days: int,
) -> Decimal:
    if financial_days <= 0 or daily_rate <= 0:
        return delivered_cost_per_liter
    divisor = (Decimal("1") + daily_rate) ** financial_days
    return _q(delivered_cost_per_liter / divisor, LITER_PERSIST_SCALE)


def compute_total(*, cost_per_liter: Decimal, requested_volume_liters: Decimal) -> Decimal:
    return _q(cost_per_liter * requested_volume_liters, TOTAL_PERSIST_SCALE)
