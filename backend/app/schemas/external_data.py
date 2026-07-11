"""Schemas Sprint 9 — índices externos."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ExternalSourceCreate(BaseModel):
    code: str
    name: str
    source_type: str
    base_url: str | None = None
    secret_ref: str | None = None
    requires_credentials: bool = False
    contract_validated: bool = False
    authorized_mechanism: str | None = None
    terms_review_status: str = "PENDING"
    metadata: dict[str, Any] | None = None


class ExternalSourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID | None
    code: str
    name: str
    source_type: str
    status: str
    connector_status: str
    base_url: str | None
    secret_ref: str | None
    requires_credentials: bool
    supports_scheduling: bool
    scheduler_enabled: bool
    terms_review_status: str
    capabilities: dict[str, Any] | None
    last_success_at: datetime | None
    last_failure_at: datetime | None
    last_test_result: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime


class ExternalSeriesCreate(BaseModel):
    source_id: uuid.UUID
    code: str
    name: str
    description: str | None = None
    frequency: str
    source_unit: str
    canonical_unit: str
    currency: str | None = None
    timezone: str = "America/Sao_Paulo"
    calendar_type: str = "BUSINESS_DAYS"
    freshness_grace_minutes: int = 1440
    expected_publish_time: str | None = None
    conversion_policy: dict[str, Any] | None = None
    outlier_pct_threshold: str | None = "15"
    active: bool = True
    metadata: dict[str, Any] | None = None


class ExternalSeriesResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID | None
    source_id: uuid.UUID
    code: str
    name: str
    description: str | None
    frequency: str
    source_unit: str
    canonical_unit: str
    currency: str | None
    timezone: str
    calendar_type: str
    freshness_grace_minutes: int
    active: bool
    created_at: datetime
    updated_at: datetime


class ManualObservationCreate(BaseModel):
    observation_datetime: datetime
    value: str
    source_unit: str | None = None
    currency: str | None = None
    published_at: datetime | None = None
    available_at: datetime | None = None
    reference_period_start: datetime | None = None
    reference_period_end: datetime | None = None
    external_identifier: str | None = None


class ObservationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    series_id: uuid.UUID
    observation_datetime: datetime
    reference_period_start: datetime | None
    reference_period_end: datetime | None
    source_value: str
    canonical_value: str
    source_unit: str
    canonical_unit: str
    currency: str | None
    published_at: datetime | None
    available_at: datetime | None
    fetched_at: datetime
    revision_number: int
    revision_status: str
    source_record_hash: str
    created_at: datetime


class ImportConfirmRequest(BaseModel):
    import_file_id: uuid.UUID


class ImportColumnMapping(BaseModel):
    date_column: str = "date"
    value_column: str = "value"
    date_format: str | None = None
    timezone: str = "America/Sao_Paulo"
    unit: str | None = None
    currency: str | None = None


class SchedulerToggleRequest(BaseModel):
    enabled: bool = False


class RunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_id: uuid.UUID
    series_id: uuid.UUID | None
    trigger_type: str
    status: str
    records_read: int
    records_inserted: int
    records_revised: int
    records_unchanged: int
    records_rejected: int
    started_at: datetime
    finished_at: datetime | None


class QualityIssueResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_id: uuid.UUID
    series_id: uuid.UUID | None
    observation_id: uuid.UUID | None
    issue_code: str
    severity: str
    details: dict[str, Any]
    resolution_status: str
    created_at: datetime


def observation_to_response(obs) -> ObservationResponse:
    return ObservationResponse(
        id=obs.id,
        series_id=obs.series_id,
        observation_datetime=obs.observation_datetime,
        reference_period_start=obs.reference_period_start,
        reference_period_end=obs.reference_period_end,
        source_value=str(obs.source_value),
        canonical_value=str(obs.canonical_value),
        source_unit=obs.source_unit,
        canonical_unit=obs.canonical_unit,
        currency=obs.currency,
        published_at=obs.published_at,
        available_at=obs.available_at,
        fetched_at=obs.fetched_at,
        revision_number=obs.revision_number,
        revision_status=obs.revision_status,
        source_record_hash=obs.source_record_hash,
        created_at=obs.created_at,
    )
