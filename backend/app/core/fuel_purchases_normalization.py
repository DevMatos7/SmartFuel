from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from app.core.fuel_purchases_enums import (
    AllocationMethod,
    GrossAmountSource,
    PurchaseCostConcept,
)
from app.integrations.xpert.canonical_hash import canonical_record_hash

FUEL_PURCHASE_NORMALIZATION_VERSION = "FUEL_PURCHASE_V1"
FUEL_PURCHASE_HASH_SCHEMA_VERSION = 1

_QTY = Decimal("0.000001")
_MONEY = Decimal("0.0001")
_COST_L = Decimal("0.00000001")
_ZERO = Decimal("0")


def _d(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def money(value: Decimal | None) -> Decimal | None:
    if value is None:
        return None
    return value.quantize(_MONEY, rounding=ROUND_HALF_UP)


def quantity(value: Decimal | None) -> Decimal | None:
    if value is None:
        return None
    return value.quantize(_QTY, rounding=ROUND_HALF_UP)


def cost_per_liter(value: Decimal | None) -> Decimal | None:
    if value is None:
        return None
    return value.quantize(_COST_L, rounding=ROUND_HALF_UP)


def resolve_gross_item_amount(
    *,
    source_item_total: Decimal | None,
    source_quantity: Decimal | None,
    source_unit_price: Decimal | None,
) -> tuple[Decimal | None, GrossAmountSource | None]:
    if source_item_total is not None:
        return money(source_item_total), GrossAmountSource.SOURCE_ITEM_TOTAL
    if source_quantity is not None and source_unit_price is not None:
        return money(source_quantity * source_unit_price), GrossAmountSource.QUANTITY_TIMES_UNIT_PRICE
    return None, None


def commercial_delivered_cost(
    *,
    gross_item_amount: Decimal,
    discount_amount: Decimal = _ZERO,
    rebate_amount: Decimal = _ZERO,
    allocated_freight: Decimal = _ZERO,
    allocated_insurance: Decimal = _ZERO,
    allocated_other_expenses: Decimal = _ZERO,
) -> Decimal:
    total = (
        gross_item_amount
        - (discount_amount or _ZERO)
        - (rebate_amount or _ZERO)
        + (allocated_freight or _ZERO)
        + (allocated_insurance or _ZERO)
        + (allocated_other_expenses or _ZERO)
    )
    return money(total) or _ZERO


def delivered_cost_per_liter(
    *,
    commercial_cost: Decimal,
    volume_liters: Decimal | None,
) -> Decimal | None:
    if volume_liters is None or volume_liters <= 0:
        return None
    return cost_per_liter(commercial_cost / volume_liters)


def allocate_header_amounts(
    *,
    item_gross_amounts: list[Decimal],
    header_freight: Decimal = _ZERO,
    header_insurance: Decimal = _ZERO,
    header_other: Decimal = _ZERO,
) -> tuple[list[dict[str, Decimal]], AllocationMethod]:
    """Rateia valores do cabeçalho proporcionalmente ao bruto; resíduo no último item."""
    n = len(item_gross_amounts)
    if n == 0:
        return [], AllocationMethod.NONE

    freight = money(header_freight) or _ZERO
    insurance = money(header_insurance) or _ZERO
    other = money(header_other) or _ZERO
    if freight == 0 and insurance == 0 and other == 0:
        return (
            [{"freight": _ZERO, "insurance": _ZERO, "other": _ZERO} for _ in range(n)],
            AllocationMethod.NONE,
        )

    total_gross = sum(item_gross_amounts, _ZERO)
    if total_gross <= 0:
        # Sem base: zera e registra método NONE (não inventa rateio).
        return (
            [{"freight": _ZERO, "insurance": _ZERO, "other": _ZERO} for _ in range(n)],
            AllocationMethod.NONE,
        )

    allocated: list[dict[str, Decimal]] = []
    sum_f = sum_i = sum_o = _ZERO
    for idx, gross in enumerate(item_gross_amounts):
        if idx == n - 1:
            allocated.append(
                {
                    "freight": money(freight - sum_f) or _ZERO,
                    "insurance": money(insurance - sum_i) or _ZERO,
                    "other": money(other - sum_o) or _ZERO,
                }
            )
        else:
            ratio = gross / total_gross
            f = money(freight * ratio) or _ZERO
            i = money(insurance * ratio) or _ZERO
            o = money(other * ratio) or _ZERO
            sum_f += f
            sum_i += i
            sum_o += o
            allocated.append({"freight": f, "insurance": i, "other": o})

    return allocated, AllocationMethod.PROPORTIONAL_GROSS_AMOUNT


def purchase_record_hash(payload: dict[str, Any]) -> str:
    material = {
        "normalization_version": FUEL_PURCHASE_NORMALIZATION_VERSION,
        "hash_schema_version": FUEL_PURCHASE_HASH_SCHEMA_VERSION,
        **payload,
    }
    return canonical_record_hash(material)


def cost_concepts_snapshot(
    *,
    erp_recorded_cost: Decimal | None,
    commercial_cost: Decimal,
    accounting_cost: Decimal | None = None,
) -> dict[str, Any]:
    return {
        PurchaseCostConcept.ERP_RECORDED_COST.value: (
            str(money(erp_recorded_cost)) if erp_recorded_cost is not None else None
        ),
        PurchaseCostConcept.COMMERCIAL_DELIVERED_COST.value: str(money(commercial_cost) or _ZERO),
        PurchaseCostConcept.ACCOUNTING_COST.value: (
            str(money(accounting_cost)) if accounting_cost is not None else None
        ),
    }


def to_decimal(value: Any) -> Decimal | None:
    return _d(value)
