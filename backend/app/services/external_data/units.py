"""Unidades e conversões explícitas para séries externas."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.core.external_data_enums import ExternalUnit

# Conversões permitidas: (from_unit, to_unit) -> fator multiplicativo
EXPLICIT_CONVERSIONS: dict[tuple[str, str], Decimal] = {
    (ExternalUnit.BRL_PER_CUBIC_METER.value, ExternalUnit.BRL_PER_LITER.value): Decimal("0.001"),
    (ExternalUnit.BRL_PER_LITER.value, ExternalUnit.BRL_PER_CUBIC_METER.value): Decimal("1000"),
}


class UnitConversionError(ValueError):
    pass


def convert_value(
    value: Decimal,
    *,
    source_unit: str,
    canonical_unit: str,
    conversion_policy: dict[str, Any] | None = None,
) -> Decimal:
    if source_unit == canonical_unit:
        return value

    policy = conversion_policy or {}
    if policy.get("forbid_auto_currency") and (
        ("USD" in source_unit and "BRL" in canonical_unit)
        or ("BRL" in source_unit and "USD" in canonical_unit)
    ):
        raise UnitConversionError("Conversão de moeda automática é proibida")

    key = (source_unit, canonical_unit)
    if key in EXPLICIT_CONVERSIONS:
        return (value * EXPLICIT_CONVERSIONS[key]).quantize(Decimal("0.0000000001"))

    factor = policy.get("factor")
    if (
        policy.get("from_unit") == source_unit
        and policy.get("to_unit") == canonical_unit
        and factor is not None
    ):
        return (value * Decimal(str(factor))).quantize(Decimal("0.0000000001"))

    raise UnitConversionError(
        f"Conversão não configurada: {source_unit} → {canonical_unit}"
    )


def parse_decimal(raw: str | Decimal | int | float | None) -> Decimal | None:
    if raw is None:
        return None
    if isinstance(raw, Decimal):
        return raw
    if isinstance(raw, (int, float)):
        return Decimal(str(raw))
    text = str(raw).strip()
    if not text:
        return None
    # decimal BR: 1.234,56 → 1234.56 ; US: 1,234.56 → 1234.56
    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        text = text.replace(",", ".")
    return Decimal(text)
