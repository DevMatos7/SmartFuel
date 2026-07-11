"""Normalização de status e aging de contas a pagar."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.core.fuel_purchases_enums import AccountsPayableNormalizedStatus, AgingBucket


def normalize_title_status(
    *,
    source_status: str | None,
    open_amount: Decimal | None,
    paid_amount: Decimal | None,
    original_amount: Decimal | None,
    due_date: date | None,
    business_today: date,
    is_cancelled: bool = False,
) -> AccountsPayableNormalizedStatus:
    if is_cancelled:
        return AccountsPayableNormalizedStatus.CANCELLED

    raw = (source_status or "").strip().upper()
    if "RENEG" in raw:
        return AccountsPayableNormalizedStatus.RENEGOTIATED
    if "CANCEL" in raw:
        return AccountsPayableNormalizedStatus.CANCELLED

    # Não inventar zero quando campos ausentes.
    if open_amount is None:
        return AccountsPayableNormalizedStatus.UNKNOWN

    if open_amount <= 0:
        return AccountsPayableNormalizedStatus.PAID

    if (
        paid_amount is not None
        and original_amount is not None
        and paid_amount > 0
        and paid_amount < original_amount
        and open_amount > 0
    ):
        status = AccountsPayableNormalizedStatus.PARTIALLY_PAID
    else:
        status = AccountsPayableNormalizedStatus.OPEN

    if due_date is not None and due_date < business_today and open_amount > 0:
        return AccountsPayableNormalizedStatus.OVERDUE

    return status


def aging_bucket(*, due_date: date, business_today: date, open_amount: Decimal) -> AgingBucket | None:
    if open_amount is None or open_amount <= 0:
        return None
    delta = (due_date - business_today).days
    if delta < 0:
        return AgingBucket.OVERDUE
    if delta <= 7:
        return AgingBucket.D0_7
    if delta <= 15:
        return AgingBucket.D8_15
    if delta <= 30:
        return AgingBucket.D16_30
    if delta <= 60:
        return AgingBucket.D31_60
    return AgingBucket.OVER_60


def weighted_term_days(
    *,
    amounts: list[Decimal],
    days: list[int],
) -> Decimal | None:
    if not amounts or len(amounts) != len(days):
        return None
    total = sum(amounts, Decimal("0"))
    if total <= 0:
        return None
    weighted = sum((a * Decimal(d) for a, d in zip(amounts, days, strict=True)), Decimal("0"))
    return (weighted / total).quantize(Decimal("0.01"))
