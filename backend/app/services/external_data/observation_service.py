"""Hash canônico e aplicação versionada de observações."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.external_data_enums import (
    ObservationApplyResult,
    ObservationRevisionStatus,
    QualityIssueCode,
    QualitySeverity,
)
from app.models.external_data import ExternalObservation, ExternalQualityIssue, ExternalSeries
from app.services.external_data.units import UnitConversionError, convert_value


def observation_hash(
    *,
    series_code: str,
    observation_datetime: datetime,
    reference_period_start: datetime | None,
    reference_period_end: datetime | None,
    source_value: Decimal,
    canonical_value: Decimal,
    source_unit: str,
    canonical_unit: str,
    currency: str | None,
    external_identifier: str | None,
    extra: dict[str, Any] | None = None,
) -> str:
    payload = {
        "series_code": series_code,
        "observation_datetime": observation_datetime.astimezone(UTC).isoformat(),
        "reference_period_start": (
            reference_period_start.astimezone(UTC).isoformat() if reference_period_start else None
        ),
        "reference_period_end": (
            reference_period_end.astimezone(UTC).isoformat() if reference_period_end else None
        ),
        "source_value": str(source_value),
        "canonical_value": str(canonical_value),
        "source_unit": source_unit,
        "canonical_unit": canonical_unit,
        "currency": currency,
        "external_identifier": external_identifier,
        "extra": extra or {},
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass
class ObservationCandidate:
    observation_datetime: datetime
    source_value: Decimal
    source_unit: str
    currency: str | None = None
    published_at: datetime | None = None
    available_at: datetime | None = None
    reference_period_start: datetime | None = None
    reference_period_end: datetime | None = None
    external_identifier: str | None = None
    raw_payload: dict[str, Any] | None = None


@dataclass
class ApplyOutcome:
    result: ObservationApplyResult
    observation: ExternalObservation | None = None
    previous: ExternalObservation | None = None


class ExternalObservationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def apply_candidate(
        self,
        *,
        series: ExternalSeries,
        candidate: ObservationCandidate,
        ingestion_run_id: uuid.UUID | None,
        fetched_at: datetime | None = None,
    ) -> ApplyOutcome:
        fetched = fetched_at or datetime.now(UTC)
        try:
            canonical = convert_value(
                candidate.source_value,
                source_unit=candidate.source_unit,
                canonical_unit=series.canonical_unit,
                conversion_policy=series.conversion_policy,
            )
        except UnitConversionError:
            await self._issue(
                source_id=series.source_id,
                series_id=series.id,
                organization_id=series.organization_id,
                ingestion_run_id=ingestion_run_id,
                code=QualityIssueCode.INVALID_UNIT,
                severity=QualitySeverity.ERROR,
                details={
                    "source_unit": candidate.source_unit,
                    "canonical_unit": series.canonical_unit,
                },
            )
            return ApplyOutcome(result=ObservationApplyResult.REJECTED)

        digest = observation_hash(
            series_code=series.code,
            observation_datetime=candidate.observation_datetime,
            reference_period_start=candidate.reference_period_start,
            reference_period_end=candidate.reference_period_end,
            source_value=candidate.source_value,
            canonical_value=canonical,
            source_unit=candidate.source_unit,
            canonical_unit=series.canonical_unit,
            currency=candidate.currency or series.currency,
            external_identifier=candidate.external_identifier,
        )

        current = (
            await self.db.execute(
                select(ExternalObservation).where(
                    ExternalObservation.series_id == series.id,
                    ExternalObservation.observation_datetime == candidate.observation_datetime,
                    ExternalObservation.revision_status == ObservationRevisionStatus.CURRENT.value,
                )
            )
        ).scalar_one_or_none()

        if current is not None and current.source_record_hash == digest:
            return ApplyOutcome(result=ObservationApplyResult.SKIPPED_UNCHANGED, observation=current)

        if current is not None:
            current.revision_status = ObservationRevisionStatus.SUPERSEDED.value
            await self._issue(
                source_id=series.source_id,
                series_id=series.id,
                organization_id=series.organization_id,
                ingestion_run_id=ingestion_run_id,
                observation_id=current.id,
                code=QualityIssueCode.REVISION_DETECTED,
                severity=QualitySeverity.INFO,
                details={
                    "previous_value": str(current.canonical_value),
                    "new_value": str(canonical),
                    "previous_revision": current.revision_number,
                },
            )
            obs = ExternalObservation(
                series_id=series.id,
                organization_id=series.organization_id,
                observation_datetime=candidate.observation_datetime,
                reference_period_start=candidate.reference_period_start,
                reference_period_end=candidate.reference_period_end,
                source_value=candidate.source_value,
                canonical_value=canonical,
                source_unit=candidate.source_unit,
                canonical_unit=series.canonical_unit,
                currency=candidate.currency or series.currency,
                published_at=candidate.published_at,
                available_at=candidate.available_at,
                fetched_at=fetched,
                revision_number=current.revision_number + 1,
                revision_status=ObservationRevisionStatus.CURRENT.value,
                external_identifier=candidate.external_identifier,
                source_record_hash=digest,
                raw_payload=candidate.raw_payload,
                ingestion_run_id=ingestion_run_id,
                created_at=fetched,
            )
            self.db.add(obs)
            await self.db.flush()
            await self._maybe_outlier(series, obs, previous=current, ingestion_run_id=ingestion_run_id)
            return ApplyOutcome(
                result=ObservationApplyResult.NEW_REVISION,
                observation=obs,
                previous=current,
            )

        obs = ExternalObservation(
            series_id=series.id,
            organization_id=series.organization_id,
            observation_datetime=candidate.observation_datetime,
            reference_period_start=candidate.reference_period_start,
            reference_period_end=candidate.reference_period_end,
            source_value=candidate.source_value,
            canonical_value=canonical,
            source_unit=candidate.source_unit,
            canonical_unit=series.canonical_unit,
            currency=candidate.currency or series.currency,
            published_at=candidate.published_at,
            available_at=candidate.available_at,
            fetched_at=fetched,
            revision_number=1,
            revision_status=ObservationRevisionStatus.CURRENT.value,
            external_identifier=candidate.external_identifier,
            source_record_hash=digest,
            raw_payload=candidate.raw_payload,
            ingestion_run_id=ingestion_run_id,
            created_at=fetched,
        )
        self.db.add(obs)
        await self.db.flush()
        return ApplyOutcome(result=ObservationApplyResult.INSERTED, observation=obs)

    async def _maybe_outlier(
        self,
        series: ExternalSeries,
        obs: ExternalObservation,
        *,
        previous: ExternalObservation,
        ingestion_run_id: uuid.UUID | None,
    ) -> None:
        threshold = series.outlier_pct_threshold
        if threshold is None or previous.canonical_value == 0:
            return
        change = abs((obs.canonical_value - previous.canonical_value) / previous.canonical_value) * Decimal(
            "100"
        )
        if change > threshold:
            await self._issue(
                source_id=series.source_id,
                series_id=series.id,
                organization_id=series.organization_id,
                ingestion_run_id=ingestion_run_id,
                observation_id=obs.id,
                code=QualityIssueCode.VALUE_OUTLIER,
                severity=QualitySeverity.WARNING,
                details={
                    "change_pct": str(change),
                    "threshold_pct": str(threshold),
                    "previous": str(previous.canonical_value),
                    "current": str(obs.canonical_value),
                    "note": "Valor preservado; não excluído automaticamente",
                },
            )

    async def _issue(
        self,
        *,
        source_id: uuid.UUID,
        series_id: uuid.UUID | None,
        organization_id: uuid.UUID | None,
        ingestion_run_id: uuid.UUID | None,
        code: QualityIssueCode,
        severity: QualitySeverity,
        details: dict[str, Any],
        observation_id: uuid.UUID | None = None,
    ) -> None:
        self.db.add(
            ExternalQualityIssue(
                source_id=source_id,
                series_id=series_id,
                observation_id=observation_id,
                ingestion_run_id=ingestion_run_id,
                organization_id=organization_id,
                issue_code=code.value,
                severity=severity.value,
                details=details,
                resolution_status="OPEN",
                created_at=datetime.now(UTC),
            )
        )
