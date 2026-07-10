"""Cálculos financeiros de vendas de combustível — Sprint 6."""

from __future__ import annotations

from decimal import Decimal

from app.core.fuel_sales_enums import CostSource, MarginStatus


def compute_net_amount(
    *,
    source_net: Decimal | None,
    gross: Decimal | None,
    discount: Decimal | None,
    surcharge: Decimal | None,
) -> tuple[Decimal | None, str]:
    if source_net is not None:
        return source_net, "SOURCE_NET"
    if gross is None:
        return None, "MISSING"
    disc = discount or Decimal("0")
    sur = surcharge or Decimal("0")
    return gross - disc + sur, "DERIVED"


def compute_realized_price_per_liter(net_amount: Decimal | None, volume_liters: Decimal | None) -> Decimal | None:
    if net_amount is None or volume_liters is None or volume_liters <= 0:
        return None
    return net_amount / volume_liters


def compute_total_cost(
    *,
    source_total_cost: Decimal | None,
    cost_per_liter: Decimal | None,
    volume_liters: Decimal | None,
) -> tuple[Decimal | None, str | None, bool]:
    mismatch = False
    if source_total_cost is not None and cost_per_liter is not None and volume_liters is not None and volume_liters > 0:
        derived = cost_per_liter * volume_liters
        tolerance = max(Decimal("0.01"), abs(source_total_cost) * Decimal("0.001"))
        if abs(source_total_cost - derived) > tolerance:
            mismatch = True
    if source_total_cost is not None:
        return source_total_cost, CostSource.ERP_RECORDED_COST, mismatch
    if cost_per_liter is not None and volume_liters is not None and volume_liters > 0:
        return cost_per_liter * volume_liters, CostSource.ERP_RECORDED_COST, mismatch
    return None, None, mismatch


def compute_margin(
    *,
    net_amount: Decimal | None,
    total_cost: Decimal | None,
    volume_liters: Decimal | None,
) -> dict[str, Decimal | str | None]:
    if net_amount is None:
        return {
            "margin_status": MarginStatus.UNAVAILABLE,
            "gross_margin_amount": None,
            "gross_margin_per_liter": None,
            "gross_margin_percent": None,
        }
    if total_cost is None:
        return {
            "margin_status": MarginStatus.UNAVAILABLE,
            "gross_margin_amount": None,
            "gross_margin_per_liter": None,
            "gross_margin_percent": None,
        }
    margin = net_amount - total_cost
    per_liter = margin / volume_liters if volume_liters and volume_liters > 0 else None
    percent = (margin / net_amount * Decimal("100")) if net_amount != 0 else None
    return {
        "margin_status": MarginStatus.AVAILABLE,
        "gross_margin_amount": margin,
        "gross_margin_per_liter": per_liter,
        "gross_margin_percent": percent,
    }
