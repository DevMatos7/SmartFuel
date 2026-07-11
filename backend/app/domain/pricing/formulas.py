"""Fórmulas comerciais de formação de preço (Decimal only).

Margem bruta comercial estimada — não é lucro líquido.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal
from typing import Any

from app.core.pricing_enums import (
    RecommendationReason,
    RecommendationStatus,
    RoundingPolicy,
)

_ZERO = Decimal("0")
_ONE = Decimal("1")
_CENT = Decimal("0.01")
_NINETYNINE = Decimal("0.99")


def _d(value: Decimal | float | int | str | None) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def gross_margin_per_liter(
    sale_price_per_liter: Decimal | None,
    comparable_cost_per_liter: Decimal | None,
) -> Decimal | None:
    if sale_price_per_liter is None or comparable_cost_per_liter is None:
        return None
    return sale_price_per_liter - comparable_cost_per_liter


def gross_margin_percentage(
    sale_price_per_liter: Decimal | None,
    comparable_cost_per_liter: Decimal | None,
) -> Decimal | None:
    if sale_price_per_liter is None or comparable_cost_per_liter is None:
        return None
    if sale_price_per_liter <= _ZERO:
        return None
    margin = sale_price_per_liter - comparable_cost_per_liter
    return margin / sale_price_per_liter


def markup_percentage(
    sale_price_per_liter: Decimal | None,
    comparable_cost_per_liter: Decimal | None,
) -> Decimal | None:
    if sale_price_per_liter is None or comparable_cost_per_liter is None:
        return None
    if comparable_cost_per_liter <= _ZERO:
        return None
    margin = sale_price_per_liter - comparable_cost_per_liter
    return margin / comparable_cost_per_liter


def floor_by_margin_per_liter(
    cost_per_liter: Decimal, minimum_margin_per_liter: Decimal
) -> Decimal:
    return cost_per_liter + minimum_margin_per_liter


def floor_by_margin_percentage(
    cost_per_liter: Decimal, minimum_margin_percentage: Decimal
) -> Decimal | None:
    if minimum_margin_percentage >= _ONE:
        return None
    denominator = _ONE - minimum_margin_percentage
    if denominator <= _ZERO:
        return None
    return cost_per_liter / denominator


def floor_by_markup(cost_per_liter: Decimal, minimum_markup_percentage: Decimal) -> Decimal:
    return cost_per_liter * (_ONE + minimum_markup_percentage)


def commercial_floor_price(
    cost_per_liter: Decimal,
    *,
    minimum_margin_per_liter: Decimal | None = None,
    minimum_margin_percentage: Decimal | None = None,
    minimum_markup_percentage: Decimal | None = None,
) -> Decimal | None:
    candidates: list[Decimal] = []
    if minimum_margin_per_liter is not None:
        candidates.append(floor_by_margin_per_liter(cost_per_liter, minimum_margin_per_liter))
    if minimum_margin_percentage is not None:
        by_pct = floor_by_margin_percentage(cost_per_liter, minimum_margin_percentage)
        if by_pct is not None:
            candidates.append(by_pct)
    if minimum_markup_percentage is not None:
        candidates.append(floor_by_markup(cost_per_liter, minimum_markup_percentage))
    if not candidates:
        return None
    return max(candidates)


def target_price(
    cost_per_liter: Decimal,
    *,
    target_margin_per_liter: Decimal | None = None,
    target_margin_percentage: Decimal | None = None,
    target_markup_percentage: Decimal | None = None,
    floor: Decimal | None = None,
) -> Decimal | None:
    raw = commercial_floor_price(
        cost_per_liter,
        minimum_margin_per_liter=target_margin_per_liter,
        minimum_margin_percentage=target_margin_percentage,
        minimum_markup_percentage=target_markup_percentage,
    )
    if raw is None:
        return floor
    if floor is not None and raw < floor:
        return floor
    return raw


def apply_rounding(
    price: Decimal,
    policy: str,
    *,
    increment: Decimal | None = None,
    floor: Decimal | None = None,
) -> tuple[Decimal, Decimal]:
    """Retorna (price_before_rounding, price_after_rounding). Nunca abaixo do piso."""
    before = price
    after = price
    if policy == RoundingPolicy.NONE:
        after = price
    elif policy == RoundingPolicy.NEAREST_CENT:
        after = price.quantize(_CENT, rounding=ROUND_HALF_UP)
    elif policy == RoundingPolicy.END_WITH_9:
        cents = (price / _CENT).to_integral_value(rounding=ROUND_HALF_UP)
        rem = int(cents % 10)
        if rem == 9:
            target_cents = cents
        else:
            target_cents = cents + (9 - rem)
        after = Decimal(target_cents) * _CENT
    elif policy == RoundingPolicy.END_WITH_99:
        whole = price.to_integral_value(rounding=ROUND_HALF_UP)
        candidate_high = whole + _NINETYNINE
        candidate_low = whole - _ONE + _NINETYNINE
        if candidate_low > _ZERO and abs(price - candidate_low) <= abs(candidate_high - price):
            after = candidate_low
        else:
            after = candidate_high
    elif policy == RoundingPolicy.CUSTOM_INCREMENT:
        inc = increment or _CENT
        if inc <= _ZERO:
            after = price
        else:
            units = (price / inc).to_integral_value(rounding=ROUND_HALF_UP)
            after = units * inc
    else:
        after = price.quantize(_CENT, rounding=ROUND_HALF_UP)

    if floor is not None and after < floor:
        # bump up to satisfy floor under same policy
        if policy == RoundingPolicy.NEAREST_CENT:
            after = floor.quantize(_CENT, rounding=ROUND_CEILING)
        elif policy == RoundingPolicy.CUSTOM_INCREMENT and increment and increment > _ZERO:
            units = (floor / increment).to_integral_value(rounding=ROUND_CEILING)
            after = units * increment
        else:
            after = floor if after < floor else after
            if after < floor:
                after = floor
    return before, after


@dataclass
class GuardrailResult:
    raw_recommended_price: Decimal
    guarded_recommended_price: Decimal
    guardrail_applied: bool
    guardrail_reason: str | None
    status_hint: RecommendationStatus | None = None
    reasons: list[str] | None = None


def apply_guardrails(
    current_price: Decimal,
    recommended_price: Decimal,
    *,
    maximum_increase_per_liter: Decimal | None = None,
    maximum_decrease_per_liter: Decimal | None = None,
    maximum_increase_percentage: Decimal | None = None,
    maximum_decrease_percentage: Decimal | None = None,
    minimum_change_per_liter: Decimal | None = None,
) -> GuardrailResult:
    raw = recommended_price
    guarded = recommended_price
    applied = False
    reason: str | None = None
    reasons: list[str] = []
    status_hint: RecommendationStatus | None = None

    delta = recommended_price - current_price
    abs_delta = abs(delta)

    if minimum_change_per_liter is not None and abs_delta < minimum_change_per_liter:
        return GuardrailResult(
            raw_recommended_price=raw,
            guarded_recommended_price=current_price,
            guardrail_applied=True,
            guardrail_reason="CHANGE_BELOW_MINIMUM",
            status_hint=RecommendationStatus.HOLD,
            reasons=[RecommendationReason.CHANGE_BELOW_MINIMUM],
        )

    max_up = maximum_increase_per_liter
    if maximum_increase_percentage is not None and current_price > _ZERO:
        pct_cap = current_price * maximum_increase_percentage
        max_up = pct_cap if max_up is None else min(max_up, pct_cap)

    max_down = maximum_decrease_per_liter
    if maximum_decrease_percentage is not None and current_price > _ZERO:
        pct_cap = current_price * maximum_decrease_percentage
        max_down = pct_cap if max_down is None else min(max_down, pct_cap)

    if delta > _ZERO and max_up is not None and delta > max_up:
        guarded = current_price + max_up
        applied = True
        reason = "CHANGE_EXCEEDS_GUARDRAIL"
        reasons.append(RecommendationReason.CHANGE_EXCEEDS_GUARDRAIL)
        status_hint = RecommendationStatus.REVIEW_REQUIRED
    elif delta < _ZERO and max_down is not None and abs_delta > max_down:
        guarded = current_price - max_down
        applied = True
        reason = "CHANGE_EXCEEDS_GUARDRAIL"
        reasons.append(RecommendationReason.CHANGE_EXCEEDS_GUARDRAIL)
        status_hint = RecommendationStatus.REVIEW_REQUIRED

    return GuardrailResult(
        raw_recommended_price=raw,
        guarded_recommended_price=guarded,
        guardrail_applied=applied,
        guardrail_reason=reason,
        status_hint=status_hint,
        reasons=reasons or None,
    )


def classify_recommendation(
    current_price: Decimal | None,
    recommended_price: Decimal | None,
    *,
    floor: Decimal | None = None,
    target: Decimal | None = None,
    extra_reasons: list[str] | None = None,
    force_status: RecommendationStatus | None = None,
) -> tuple[RecommendationStatus, list[str]]:
    reasons: list[str] = list(extra_reasons or [])
    if force_status == RecommendationStatus.NO_RECOMMENDATION:
        return RecommendationStatus.NO_RECOMMENDATION, reasons
    if current_price is None or recommended_price is None:
        if RecommendationReason.MISSING_COST not in reasons and RecommendationReason.MISSING_CURRENT_PRICE not in reasons:
            reasons.append(RecommendationReason.MISSING_CURRENT_PRICE)
        return RecommendationStatus.NO_RECOMMENDATION, reasons

    if floor is not None and current_price < floor:
        reasons.append(RecommendationReason.BELOW_COMMERCIAL_FLOOR)
    if target is not None and current_price < target:
        reasons.append(RecommendationReason.BELOW_TARGET_MARGIN)
    if target is not None and current_price > target:
        reasons.append(RecommendationReason.ABOVE_TARGET_MARGIN)
    if target is not None and abs(current_price - target) < Decimal("0.005") and RecommendationReason.AT_TARGET not in reasons:
        reasons.append(RecommendationReason.AT_TARGET)

    if force_status is not None:
        return force_status, reasons

    delta = recommended_price - current_price
    if abs(delta) < Decimal("0.005"):
        return RecommendationStatus.HOLD, reasons
    if delta > _ZERO:
        return RecommendationStatus.INCREASE, reasons
    return RecommendationStatus.DECREASE, reasons


def build_scenario_price(
    cost_per_liter: Decimal,
    *,
    floor: Decimal | None,
    target: Decimal | None,
    scenario_type: str,
    conservative_cost: Decimal | None = None,
) -> Decimal:
    from app.core.pricing_enums import PricingScenarioType

    if scenario_type == PricingScenarioType.CONSERVATIVE:
        base_cost = conservative_cost if conservative_cost is not None else cost_per_liter
        # alvo superior: se houver target, usa max(target, floor) com custo conservador recalculado
        t = target_price(
            base_cost,
            target_margin_per_liter=(target - base_cost) if target and base_cost else None,
        )
        # Prefer explicit target inflated by 5% when target exists
        if target is not None:
            inflated = target * Decimal("1.05")
            price = inflated
        elif floor is not None:
            price = floor * Decimal("1.05")
        else:
            price = base_cost * Decimal("1.20")
        if floor is not None:
            price = max(price, floor)
        return price

    if scenario_type == PricingScenarioType.COMPETITIVE:
        if floor is not None:
            return floor
        return cost_per_liter * Decimal("1.05")

    # BALANCED
    if target is not None:
        return max(target, floor) if floor is not None else target
    if floor is not None:
        return floor
    return cost_per_liter * Decimal("1.12")


def estimated_margin_impact(
    price_change_per_liter: Decimal | None,
    reference_daily_volume: Decimal | None,
    *,
    month_days: int = 30,
) -> dict[str, Any] | None:
    if price_change_per_liter is None or reference_daily_volume is None:
        return None
    if reference_daily_volume <= _ZERO:
        return None
    daily = price_change_per_liter * reference_daily_volume
    return {
        "estimated_daily_margin_impact": str(daily),
        "estimated_monthly_margin_impact": str(daily * Decimal(month_days)),
        "reference_daily_volume": str(reference_daily_volume),
        "is_estimate": True,
        "disclaimer": "Estimativa baseada em volume de referência. Não é resultado contábil.",
    }
