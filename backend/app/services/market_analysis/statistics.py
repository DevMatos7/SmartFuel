"""Estatística pura (Decimal) — Pearson, Spearman, lags, repasse."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Sequence

from app.core.market_analysis_enums import QualityStatus


def _mean(values: Sequence[Decimal]) -> Decimal:
    if not values:
        raise ValueError("série vazia")
    return sum(values, Decimal(0)) / Decimal(len(values))


def _is_constant(values: Sequence[Decimal]) -> bool:
    if len(values) < 2:
        return True
    first = values[0]
    return all(v == first for v in values)


def pearson(xs: Sequence[Decimal], ys: Sequence[Decimal]) -> tuple[Decimal | None, QualityStatus, list[str]]:
    warnings: list[str] = []
    if len(xs) != len(ys):
        return None, QualityStatus.FAILED, ["pares desalinhados"]
    n = len(xs)
    if n < 2:
        return None, QualityStatus.INSUFFICIENT_SAMPLE, ["n < 2"]
    if _is_constant(xs) or _is_constant(ys):
        return None, QualityStatus.CONSTANT_SERIES, ["série constante — correlação não calculada"]
    mx, my = _mean(xs), _mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True))
    den_x = sum((x - mx) ** 2 for x in xs)
    den_y = sum((y - my) ** 2 for y in ys)
    if den_x == 0 or den_y == 0:
        return None, QualityStatus.NO_VARIATION, ["variância zero"]
    try:
        coef = num / (den_x ** Decimal("0.5") * den_y ** Decimal("0.5"))
    except (InvalidOperation, ValueError):
        return None, QualityStatus.FAILED, ["falha no cálculo de Pearson"]
    # clamp numeric noise
    if coef > 1:
        coef = Decimal(1)
    if coef < -1:
        coef = Decimal(-1)
    return coef.quantize(Decimal("0.0000000001")), QualityStatus.VALID, warnings


def _ranks(values: Sequence[Decimal]) -> list[Decimal]:
    indexed = sorted(enumerate(values), key=lambda item: item[1])
    ranks = [Decimal(0)] * len(values)
    i = 0
    while i < len(indexed):
        j = i
        while j + 1 < len(indexed) and indexed[j + 1][1] == indexed[i][1]:
            j += 1
        avg_rank = Decimal(sum(range(i + 1, j + 2))) / Decimal(j - i + 1)
        for k in range(i, j + 1):
            ranks[indexed[k][0]] = avg_rank
        i = j + 1
    return ranks


def spearman(xs: Sequence[Decimal], ys: Sequence[Decimal]) -> tuple[Decimal | None, QualityStatus, list[str]]:
    if len(xs) != len(ys):
        return None, QualityStatus.FAILED, ["pares desalinhados"]
    if len(xs) < 2:
        return None, QualityStatus.INSUFFICIENT_SAMPLE, ["n < 2"]
    if _is_constant(xs) or _is_constant(ys):
        return None, QualityStatus.CONSTANT_SERIES, ["série constante — correlação não calculada"]
    return pearson(_ranks(xs), _ranks(ys))


@dataclass
class LagResult:
    lag: int
    coefficient: Decimal | None
    sample_size: int
    quality_status: QualityStatus
    warnings: list[str]


def cross_correlation_by_lag(
    external: Sequence[Decimal],
    internal: Sequence[Decimal],
    *,
    lag_min: int,
    lag_max: int,
    method: str = "PEARSON",
) -> list[LagResult]:
    """Lag positivo: internal[t] vs external[t - lag] (índice antecede o alvo)."""
    results: list[LagResult] = []
    n = len(external)
    assert n == len(internal)
    for lag in range(lag_min, lag_max + 1):
        xs: list[Decimal] = []
        ys: list[Decimal] = []
        for t in range(n):
            src = t - lag
            if src < 0 or src >= n:
                continue
            xs.append(external[src])
            ys.append(internal[t])
        if method == "SPEARMAN":
            coef, quality, warnings = spearman(xs, ys)
        else:
            coef, quality, warnings = pearson(xs, ys)
        results.append(
            LagResult(
                lag=lag,
                coefficient=coef,
                sample_size=len(xs),
                quality_status=quality,
                warnings=warnings,
            )
        )
    return results


def select_best_lag(
    lags: Sequence[LagResult], *, minimum_sample_size: int
) -> LagResult | None:
    eligible = [
        r
        for r in lags
        if r.coefficient is not None
        and r.sample_size >= minimum_sample_size
        and r.quality_status
        in (QualityStatus.VALID, QualityStatus.VALID_WITH_WARNINGS)
    ]
    if not eligible:
        return None
    return max(eligible, key=lambda r: abs(r.coefficient or Decimal(0)))


def pass_through_ratio(
    reference_change: Decimal,
    target_change: Decimal,
    *,
    minimum_reference_change: Decimal,
) -> tuple[Decimal | None, QualityStatus]:
    if abs(reference_change) < minimum_reference_change:
        return None, QualityStatus.PASS_THROUGH_UNAVAILABLE
    return (target_change / reference_change).quantize(Decimal("0.0000000001")), QualityStatus.VALID


def pass_through_elasticity(
    reference_pct: Decimal,
    target_pct: Decimal,
    *,
    minimum_reference_change: Decimal,
) -> tuple[Decimal | None, QualityStatus]:
    if abs(reference_pct) < minimum_reference_change:
        return None, QualityStatus.PASS_THROUGH_UNAVAILABLE
    return (target_pct / reference_pct).quantize(Decimal("0.0000000001")), QualityStatus.VALID


def absolute_changes(values: Sequence[Decimal]) -> list[Decimal | None]:
    out: list[Decimal | None] = [None]
    for i in range(1, len(values)):
        out.append(values[i] - values[i - 1])
    return out


def percentage_changes(values: Sequence[Decimal]) -> list[Decimal | None]:
    out: list[Decimal | None] = [None]
    for i in range(1, len(values)):
        prev = values[i - 1]
        if prev == 0:
            out.append(None)
        else:
            out.append(((values[i] / prev) - Decimal(1)).quantize(Decimal("0.0000000001")))
    return out


def base_100(values: Sequence[Decimal]) -> list[Decimal]:
    if not values:
        return []
    base = values[0]
    if base == 0:
        return [Decimal(0) for _ in values]
    return [(v / base * Decimal(100)).quantize(Decimal("0.0000000001")) for v in values]
