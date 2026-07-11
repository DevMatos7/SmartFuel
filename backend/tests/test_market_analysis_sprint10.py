"""Testes sintéticos Sprint 10 — estatística, lag, no-hindsight."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from app.core.market_analysis_enums import (
    AlignmentPolicy,
    MarketAnalysisStatus,
    MarketTransformation,
    QualityStatus,
)
from app.services.market_analysis.alignment import SeriesPoint, align_series, apply_transformation
from app.services.market_analysis.statistics import (
    pass_through_ratio,
    pearson,
    select_best_lag,
    spearman,
)
from app.services.market_analysis_service import MarketAnalysisService
from app.services.audit_service import AuditContext


def test_pearson_perfect_positive():
    xs = [Decimal(i) for i in range(1, 11)]
    ys = [Decimal(i) * 2 for i in range(1, 11)]
    coef, quality, _ = pearson(xs, ys)
    assert quality == QualityStatus.VALID
    assert coef is not None
    assert abs(coef - Decimal(1)) < Decimal("0.0001")


def test_pearson_negative():
    xs = [Decimal(i) for i in range(1, 11)]
    ys = [Decimal(-i) for i in range(1, 11)]
    coef, quality, _ = pearson(xs, ys)
    assert quality == QualityStatus.VALID
    assert coef is not None
    assert coef < Decimal("-0.99")


def test_constant_series_rejected():
    xs = [Decimal(5)] * 10
    ys = [Decimal(i) for i in range(10)]
    coef, quality, _ = pearson(xs, ys)
    assert coef is None
    assert quality == QualityStatus.CONSTANT_SERIES


def test_spearman_monotonic():
    xs = [Decimal(1), Decimal(2), Decimal(3), Decimal(4), Decimal(5)]
    ys = [Decimal(10), Decimal(100), Decimal(1000), Decimal(10000), Decimal(100000)]
    coef, quality, _ = spearman(xs, ys)
    assert quality == QualityStatus.VALID
    assert coef == Decimal(1)


def test_pass_through_small_denominator_blocked():
    ratio, status = pass_through_ratio(
        Decimal("0.00001"),
        Decimal("0.5"),
        minimum_reference_change=Decimal("0.0001"),
    )
    assert ratio is None
    assert status == QualityStatus.PASS_THROUGH_UNAVAILABLE


def test_hindsight_blocked_by_available_at():
    base = datetime(2026, 1, 10, 12, 0, tzinfo=UTC)
    external = [
        SeriesPoint(
            observation_datetime=base,
            available_at=base + timedelta(days=2),  # publicado depois
            value=Decimal("100"),
        )
    ]
    internal = [
        SeriesPoint(
            observation_datetime=base + timedelta(days=1),
            available_at=base + timedelta(days=1),
            value=Decimal("50"),
        )
    ]
    pairs = align_series(
        external=external,
        internal=internal,
        event_datetimes=[base + timedelta(days=1)],
        alignment_policy=AlignmentPolicy.CARRY_FORWARD_EXTERNAL,
        maximum_carry_forward_age=10,
        lag=0,
    )
    assert pairs
    assert pairs[0].included is False
    assert pairs[0].exclusion_reason == "HINDSIGHT_BLOCKED_AVAILABLE_AT"


def test_alignment_allows_when_available_before_event():
    base = datetime(2026, 1, 10, 12, 0, tzinfo=UTC)
    external = [
        SeriesPoint(
            observation_datetime=base,
            available_at=base,
            value=Decimal("100"),
        )
    ]
    internal = [
        SeriesPoint(
            observation_datetime=base,
            available_at=base,
            value=Decimal("50"),
        )
    ]
    pairs = align_series(external=external, internal=internal, lag=0)
    assert len(pairs) == 1
    assert pairs[0].included is True


@pytest.mark.asyncio
async def test_synthetic_run_finds_lag(db_session):
    org_id = uuid4()
    user_id = uuid4()
    service = MarketAnalysisService(db_session)
    start = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    external = []
    internal = []
    for i in range(40):
        day = start + timedelta(days=i)
        external.append(
            {
                "observation_datetime": day.isoformat(),
                "available_at": day.isoformat(),
                "value": str(Decimal(100) + Decimal(i) * Decimal("0.5")),
            }
        )
        src = max(0, i - 3)
        internal.append(
            {
                "observation_datetime": day.isoformat(),
                "available_at": day.isoformat(),
                "value": str(Decimal(50) + Decimal(src) * Decimal("0.5")),
            }
        )

    audit = AuditContext(
        organization_id=org_id,
        user_id=user_id,
        ip_address="127.0.0.1",
        request_id=str(uuid4()),
    )
    # ensure params exist with low sample min
    params = await service.get_or_create_parameters(org_id, user_id)
    params.minimum_sample_size = 10
    params.maximum_lag = 7
    await db_session.flush()

    run = await service.run_analysis(
        organization_id=org_id,
        user_id=None,
        data={
            "analysis_type": "FULL",
            "internal_series_type": "SYNTHETIC_INTERNAL",
            "period_start": start.isoformat(),
            "period_end": (start + timedelta(days=39)).isoformat(),
            "frequency": "DAILY",
            "transformation": MarketTransformation.ABSOLUTE_CHANGE.value,
            "alignment_policy": AlignmentPolicy.EXACT_DATE.value,
            "lag_min": 0,
            "lag_max": 7,
            "synthetic_external": external,
            "synthetic_internal": internal,
        },
        audit_ctx=None,
        trigger_type="SYNTHETIC",
    )
    assert run.status in (
        MarketAnalysisStatus.COMPLETED.value,
        MarketAnalysisStatus.INSUFFICIENT_SAMPLE.value,
    )
    assert run.snapshot_hash
    assert run.interpretive_disclaimer
    assert "causalidade" in run.interpretive_disclaimer.lower() or "associação" in run.interpretive_disclaimer.lower()
    # lag conhecido ~3
    if run.selected_lag is not None:
        assert run.selected_lag in (2, 3, 4)

    # reprocess creates new run — sem FK de usuário em teste unitário
    run2 = await service.run_analysis(
        organization_id=org_id,
        user_id=None,
        data={
            "analysis_type": "FULL",
            "internal_series_type": "SYNTHETIC_INTERNAL",
            "period_start": start.isoformat(),
            "period_end": (start + timedelta(days=39)).isoformat(),
            "frequency": "DAILY",
            "transformation": MarketTransformation.ABSOLUTE_CHANGE.value,
            "alignment_policy": AlignmentPolicy.EXACT_DATE.value,
            "lag_min": 0,
            "lag_max": 7,
            "synthetic_external": external,
            "synthetic_internal": internal,
        },
        audit_ctx=None,
        trigger_type="REPROCESS",
        reprocess_of_run_id=run.id,
        reprocess_reason="teste imutabilidade",
    )
    assert run2.id != run.id
    assert run2.reprocess_of_run_id == run.id
    original = await service.get_run(run.id, org_id)
    assert original.snapshot_hash == run.snapshot_hash


def test_select_best_lag_respects_sample():
    from app.services.market_analysis.statistics import LagResult

    lags = [
        LagResult(0, Decimal("0.9"), 5, QualityStatus.VALID, []),
        LagResult(3, Decimal("0.8"), 20, QualityStatus.VALID, []),
    ]
    best = select_best_lag(lags, minimum_sample_size=10)
    assert best is not None
    assert best.lag == 3
