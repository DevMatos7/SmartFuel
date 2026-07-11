"""Freshness de séries externas."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.external_data_enums import ExternalSeriesFrequency, FreshnessStatus, ObservationRevisionStatus
from app.models.external_data import ExternalObservation, ExternalSeries


@dataclass
class FreshnessResult:
    series_id: str
    series_code: str
    status: FreshnessStatus
    last_observation_datetime: datetime | None
    last_published_at: datetime | None
    last_fetched_at: datetime | None
    expected_by: datetime | None
    grace_minutes: int
    frequency: str


class ExternalFreshnessService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def _expected_interval(self, frequency: str) -> timedelta | None:
        return {
            ExternalSeriesFrequency.INTRADAY.value: timedelta(hours=6),
            ExternalSeriesFrequency.DAILY.value: timedelta(days=1),
            ExternalSeriesFrequency.WEEKLY.value: timedelta(days=7),
            ExternalSeriesFrequency.MONTHLY.value: timedelta(days=31),
            ExternalSeriesFrequency.IRREGULAR.value: None,
        }.get(frequency)

    async def evaluate_series(self, series: ExternalSeries, *, now: datetime | None = None) -> FreshnessResult:
        now = now or datetime.now(UTC)
        last = (
            await self.db.execute(
                select(ExternalObservation)
                .where(
                    ExternalObservation.series_id == series.id,
                    ExternalObservation.revision_status == ObservationRevisionStatus.CURRENT.value,
                )
                .order_by(ExternalObservation.observation_datetime.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

        grace = timedelta(minutes=series.freshness_grace_minutes or 0)
        interval = self._expected_interval(series.frequency)

        if last is None:
            return FreshnessResult(
                series_id=str(series.id),
                series_code=series.code,
                status=FreshnessStatus.UNKNOWN,
                last_observation_datetime=None,
                last_published_at=None,
                last_fetched_at=None,
                expected_by=None,
                grace_minutes=series.freshness_grace_minutes,
                frequency=series.frequency,
            )

        if interval is None:
            status = FreshnessStatus.FRESH
            expected_by = None
        else:
            expected_by = last.observation_datetime + interval + grace
            due_soon_at = last.observation_datetime + interval
            if now <= due_soon_at:
                status = FreshnessStatus.FRESH
            elif now <= expected_by:
                status = FreshnessStatus.DUE_SOON
            else:
                status = FreshnessStatus.STALE

        return FreshnessResult(
            series_id=str(series.id),
            series_code=series.code,
            status=status,
            last_observation_datetime=last.observation_datetime,
            last_published_at=last.published_at,
            last_fetched_at=last.fetched_at,
            expected_by=expected_by,
            grace_minutes=series.freshness_grace_minutes,
            frequency=series.frequency,
        )
