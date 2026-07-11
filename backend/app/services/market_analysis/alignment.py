"""Alinhamento temporal sem hindsight e transformações."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.core.market_analysis_enums import AlignmentPolicy, MarketTransformation
from app.services.market_analysis.statistics import absolute_changes, base_100, percentage_changes


@dataclass
class SeriesPoint:
    observation_datetime: datetime
    available_at: datetime
    value: Decimal
    observation_id: str | None = None
    entity_type: str | None = None
    entity_id: str | None = None


@dataclass
class AlignedPair:
    period_datetime: datetime
    external_value: Decimal
    internal_value: Decimal
    external_observation_id: str | None
    internal_entity_type: str | None
    internal_entity_id: str | None
    lag_applied: int
    carry_forward: bool
    carry_forward_age: int | None
    included: bool
    exclusion_reason: str | None
    external_change: Decimal | None = None
    internal_change: Decimal | None = None
    external_transformed: Decimal | None = None
    internal_transformed: Decimal | None = None


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def align_series(
    *,
    external: list[SeriesPoint],
    internal: list[SeriesPoint],
    event_datetimes: list[datetime] | None = None,
    alignment_policy: AlignmentPolicy = AlignmentPolicy.EXACT_DATE,
    maximum_carry_forward_age: int = 7,
    lag: int = 0,
) -> list[AlignedPair]:
    """Alinha pares respeitando available_at <= event_datetime (no-hindsight).

    Para lag > 0, o valor externo usado é o da data (event - lag dias),
    ainda exigindo available_at <= event_datetime.
    """
    ext_by_day: dict[datetime, SeriesPoint] = {}
    for p in external:
        day = _as_utc(p.observation_datetime).replace(hour=0, minute=0, second=0, microsecond=0)
        # última observação do dia
        prev = ext_by_day.get(day)
        if prev is None or _as_utc(p.available_at) >= _as_utc(prev.available_at):
            ext_by_day[day] = p

    int_by_day: dict[datetime, SeriesPoint] = {}
    for p in internal:
        day = _as_utc(p.observation_datetime).replace(hour=0, minute=0, second=0, microsecond=0)
        prev = int_by_day.get(day)
        if prev is None or _as_utc(p.available_at) >= _as_utc(prev.available_at):
            int_by_day[day] = p

    if event_datetimes is None:
        event_datetimes = sorted(int_by_day.keys())

    pairs: list[AlignedPair] = []
    for event_dt in event_datetimes:
        event_day = _as_utc(event_dt).replace(hour=0, minute=0, second=0, microsecond=0)
        internal_pt = int_by_day.get(event_day)
        if internal_pt is None:
            continue

        ref_day = event_day - timedelta(days=lag)
        external_pt = ext_by_day.get(ref_day)
        carry = False
        carry_age: int | None = None

        if external_pt is None and alignment_policy == AlignmentPolicy.CARRY_FORWARD_EXTERNAL:
            # último valor externo conhecido por data econômica (<= ref_day);
            # available_at é validado depois (no-hindsight)
            candidates = [p for d, p in ext_by_day.items() if d <= ref_day]
            if candidates:
                external_pt = max(candidates, key=lambda p: _as_utc(p.observation_datetime))
                carry = True
                carry_age = (
                    ref_day
                    - _as_utc(external_pt.observation_datetime).replace(
                        hour=0, minute=0, second=0, microsecond=0
                    )
                ).days
                if carry_age > maximum_carry_forward_age:
                    pairs.append(
                        AlignedPair(
                            period_datetime=event_day,
                            external_value=external_pt.value,
                            internal_value=internal_pt.value,
                            external_observation_id=external_pt.observation_id,
                            internal_entity_type=internal_pt.entity_type,
                            internal_entity_id=internal_pt.entity_id,
                            lag_applied=lag,
                            carry_forward=True,
                            carry_forward_age=carry_age,
                            included=False,
                            exclusion_reason="CARRY_FORWARD_EXPIRED",
                        )
                    )
                    continue

        if external_pt is None:
            continue

        # no-hindsight: comparar com o momento do evento interno (available_at)
        decision_t = _as_utc(internal_pt.available_at)
        if _as_utc(external_pt.available_at) > decision_t:
            pairs.append(
                AlignedPair(
                    period_datetime=event_day,
                    external_value=external_pt.value,
                    internal_value=internal_pt.value,
                    external_observation_id=external_pt.observation_id,
                    internal_entity_type=internal_pt.entity_type,
                    internal_entity_id=internal_pt.entity_id,
                    lag_applied=lag,
                    carry_forward=carry,
                    carry_forward_age=carry_age,
                    included=False,
                    exclusion_reason="HINDSIGHT_BLOCKED_AVAILABLE_AT",
                )
            )
            continue

        pairs.append(
            AlignedPair(
                period_datetime=event_day,
                external_value=external_pt.value,
                internal_value=internal_pt.value,
                external_observation_id=external_pt.observation_id,
                internal_entity_type=internal_pt.entity_type,
                internal_entity_id=internal_pt.entity_id,
                lag_applied=lag,
                carry_forward=carry,
                carry_forward_age=carry_age,
                included=True,
                exclusion_reason=None,
            )
        )

    # mudanças absolutas entre pares incluídos em ordem
    included = [p for p in pairs if p.included]
    if included:
        ext_vals = [p.external_value for p in included]
        int_vals = [p.internal_value for p in included]
        ext_ch = absolute_changes(ext_vals)
        int_ch = absolute_changes(int_vals)
        for i, p in enumerate(included):
            p.external_change = ext_ch[i]
            p.internal_change = int_ch[i]

    return pairs


def apply_transformation(
    pairs: list[AlignedPair],
    transformation: MarketTransformation,
) -> list[AlignedPair]:
    included = [p for p in pairs if p.included]
    if not included:
        return pairs
    ext = [p.external_value for p in included]
    inn = [p.internal_value for p in included]

    if transformation == MarketTransformation.LEVEL:
        for p in included:
            p.external_transformed = p.external_value
            p.internal_transformed = p.internal_value
    elif transformation == MarketTransformation.ABSOLUTE_CHANGE:
        e_ch = absolute_changes(ext)
        i_ch = absolute_changes(inn)
        for i, p in enumerate(included):
            if e_ch[i] is None or i_ch[i] is None:
                p.included = False
                p.exclusion_reason = "MISSING_CHANGE"
            else:
                p.external_transformed = e_ch[i]
                p.internal_transformed = i_ch[i]
    elif transformation == MarketTransformation.PERCENTAGE_CHANGE:
        e_ch = percentage_changes(ext)
        i_ch = percentage_changes(inn)
        for i, p in enumerate(included):
            if e_ch[i] is None or i_ch[i] is None:
                p.included = False
                p.exclusion_reason = "MISSING_PCT_CHANGE"
            else:
                p.external_transformed = e_ch[i]
                p.internal_transformed = i_ch[i]
    elif transformation == MarketTransformation.BASE_100:
        e100 = base_100(ext)
        i100 = base_100(inn)
        for i, p in enumerate(included):
            p.external_transformed = e100[i]
            p.internal_transformed = i100[i]
            if i == 0:
                # base 100 no primeiro ponto — correlação em nível ainda possível,
                # mas documentamos risco de espúria via warning no serviço
                pass
    return pairs
