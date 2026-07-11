"""Testes Sprint 9 — unidades, revisões, freshness, adapters."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from app.core.external_data_enums import (
    ExternalSeriesFrequency,
    ExternalSourceStatus,
    FreshnessStatus,
    ObservationApplyResult,
)
from app.models.external_data import ExternalDataSource, ExternalSeries
from app.services.external_data.adapters import (
    ApiExternalSourceAdapter,
    AuthorizedWebSourceAdapter,
    get_adapter,
)
from app.services.external_data.freshness_service import ExternalFreshnessService
from app.services.external_data.observation_service import (
    ExternalObservationService,
    ObservationCandidate,
)
from app.services.external_data.units import UnitConversionError, convert_value, parse_decimal


def test_parse_decimal_comma_and_dot():
    assert parse_decimal("1.234,56") == Decimal("1234.56")
    assert parse_decimal("1,234.56") == Decimal("1234.56")
    assert parse_decimal("78,45") == Decimal("78.45")
    assert parse_decimal("") is None
    assert parse_decimal(None) is None


def test_convert_m3_to_liter_explicit():
    assert convert_value(
        Decimal("3500"),
        source_unit="BRL_PER_CUBIC_METER",
        canonical_unit="BRL_PER_LITER",
    ) == Decimal("3.5000000000")


def test_currency_conversion_forbidden():
    with pytest.raises(UnitConversionError):
        convert_value(
            Decimal("5"),
            source_unit="USD_PER_BARREL",
            canonical_unit="BRL_PER_LITER",
            conversion_policy={"forbid_auto_currency": True},
        )


def test_api_adapter_misconfigured_without_contract():
    adapter = ApiExternalSourceAdapter({"base_url": "https://example.com", "secret_ref": "FOO"})
    assert adapter.connector_status() == ExternalSourceStatus.MISCONFIGURED.value
    assert any("contrato" in e.lower() for e in adapter.validate_config())


def test_csonline_adapter_always_misconfigured():
    adapter = AuthorizedWebSourceAdapter({})
    assert adapter.connector_status() == ExternalSourceStatus.MISCONFIGURED.value
    assert get_adapter("AUTHORIZED_WEB").capabilities().supports_scheduling is False


@pytest.mark.asyncio
async def test_observation_insert_and_idempotent_and_revision(db_session):
    org_id = uuid4()
    source = ExternalDataSource(
        organization_id=org_id,
        code="MANUAL_TEST",
        name="Manual",
        source_type="MANUAL",
        status="READY_FOR_MANUAL",
        connector_status="READY_FOR_MANUAL",
        requires_credentials=False,
        supports_scheduling=False,
        scheduler_enabled=False,
        terms_review_status="PENDING",
    )
    db_session.add(source)
    await db_session.flush()
    series = ExternalSeries(
        organization_id=org_id,
        source_id=source.id,
        code="BRENT_CRUDE_OIL",
        name="Brent",
        frequency=ExternalSeriesFrequency.DAILY.value,
        source_unit="USD_PER_BARREL",
        canonical_unit="USD_PER_BARREL",
        currency="USD",
        timezone="UTC",
        calendar_type="BUSINESS_DAYS",
        freshness_grace_minutes=1440,
        conversion_policy={"forbid_auto_currency": True},
        outlier_pct_threshold=Decimal("15"),
        active=True,
    )
    db_session.add(series)
    await db_session.flush()

    svc = ExternalObservationService(db_session)
    obs_dt = datetime(2026, 7, 1, 12, 0, tzinfo=UTC)
    cand = ObservationCandidate(
        observation_datetime=obs_dt,
        source_value=Decimal("78.50"),
        source_unit="USD_PER_BARREL",
        currency="USD",
        published_at=obs_dt,
    )
    r1 = await svc.apply_candidate(series=series, candidate=cand, ingestion_run_id=None)
    assert r1.result == ObservationApplyResult.INSERTED

    r2 = await svc.apply_candidate(series=series, candidate=cand, ingestion_run_id=None)
    assert r2.result == ObservationApplyResult.SKIPPED_UNCHANGED

    cand2 = ObservationCandidate(
        observation_datetime=obs_dt,
        source_value=Decimal("79.10"),
        source_unit="USD_PER_BARREL",
        currency="USD",
        published_at=obs_dt,
    )
    r3 = await svc.apply_candidate(series=series, candidate=cand2, ingestion_run_id=None)
    assert r3.result == ObservationApplyResult.NEW_REVISION
    assert r3.observation is not None
    assert r3.observation.revision_number == 2
    assert r3.previous is not None
    assert r3.previous.revision_status == "SUPERSEDED"


@pytest.mark.asyncio
async def test_freshness_weekly_not_stale_after_one_day(db_session):
    org_id = uuid4()
    source = ExternalDataSource(
        organization_id=org_id,
        code="CEPEA_SRC",
        name="CEPEA",
        source_type="MANUAL",
        status="READY_FOR_MANUAL",
        connector_status="READY_FOR_MANUAL",
        requires_credentials=False,
        supports_scheduling=False,
        scheduler_enabled=False,
        terms_review_status="PENDING",
    )
    db_session.add(source)
    await db_session.flush()
    series = ExternalSeries(
        organization_id=org_id,
        source_id=source.id,
        code="CEPEA_ETHANOL_MT",
        name="CEPEA",
        frequency=ExternalSeriesFrequency.WEEKLY.value,
        source_unit="BRL_PER_LITER",
        canonical_unit="BRL_PER_LITER",
        currency="BRL",
        timezone="America/Sao_Paulo",
        calendar_type="SOURCE_SPECIFIC",
        freshness_grace_minutes=10080,
        active=True,
    )
    db_session.add(series)
    await db_session.flush()

    obs_svc = ExternalObservationService(db_session)
    obs_dt = datetime.now(UTC) - timedelta(days=2)
    await obs_svc.apply_candidate(
        series=series,
        candidate=ObservationCandidate(
            observation_datetime=obs_dt,
            source_value=Decimal("2.85"),
            source_unit="BRL_PER_LITER",
            reference_period_start=obs_dt - timedelta(days=6),
            reference_period_end=obs_dt,
            published_at=obs_dt,
        ),
        ingestion_run_id=None,
    )
    await db_session.flush()

    fresh = await ExternalFreshnessService(db_session).evaluate_series(series)
    assert fresh.status in (FreshnessStatus.FRESH, FreshnessStatus.DUE_SOON)
    assert fresh.status != FreshnessStatus.STALE
