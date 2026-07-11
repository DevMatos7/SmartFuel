"""Schemas Sprint 10 — market analysis."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class MarketParametersResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    minimum_sample_size: int
    maximum_missing_percentage: str
    maximum_carry_forward_age: int
    minimum_lag: int
    maximum_lag: int
    lag_unit: str
    minimum_reference_change: str
    default_frequency: str
    default_transformation: str
    valid_from: datetime
    valid_until: datetime | None
    active: bool


class MarketParametersUpsert(BaseModel):
    minimum_sample_size: int | None = None
    maximum_missing_percentage: str | None = None
    maximum_carry_forward_age: int | None = None
    minimum_lag: int | None = None
    maximum_lag: int | None = None
    lag_unit: str | None = None
    minimum_reference_change: str | None = None
    default_frequency: str | None = None
    default_transformation: str | None = None


class SyntheticPoint(BaseModel):
    observation_datetime: datetime
    available_at: datetime
    value: str


class MarketRunCreate(BaseModel):
    analysis_type: str = "FULL"
    external_series_id: uuid.UUID | None = None
    internal_series_type: str
    station_id: uuid.UUID | None = None
    canonical_product_id: uuid.UUID | None = None
    distributor_id: uuid.UUID | None = None
    period_start: datetime
    period_end: datetime
    frequency: str | None = None
    transformation: str | None = None
    alignment_policy: str | None = None
    lag_min: int | None = None
    lag_max: int | None = None
    synthetic_external: list[SyntheticPoint] | None = None
    synthetic_internal: list[SyntheticPoint] | None = None


class MarketRunReprocess(BaseModel):
    reason: str = Field(min_length=3)


class MarketRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    analysis_type: str
    status: str
    external_series_id: uuid.UUID | None
    external_series_code: str | None
    internal_series_type: str
    station_id: uuid.UUID | None
    canonical_product_id: uuid.UUID | None
    distributor_id: uuid.UUID | None
    period_start: datetime
    period_end: datetime
    frequency: str
    transformation: str
    alignment_policy: str
    lag_min: int
    lag_max: int
    selected_lag: int | None
    sample_size: int
    aligned_pair_count: int
    warning_count: int
    snapshot_hash: str | None
    interpretive_disclaimer: str
    trigger_type: str
    reprocess_of_run_id: uuid.UUID | None
    started_at: datetime
    finished_at: datetime | None
    output_snapshot: dict[str, Any] | None = None
    input_snapshot: dict[str, Any] | None = None


def params_to_response(p) -> MarketParametersResponse:
    return MarketParametersResponse(
        id=p.id,
        organization_id=p.organization_id,
        minimum_sample_size=p.minimum_sample_size,
        maximum_missing_percentage=str(p.maximum_missing_percentage),
        maximum_carry_forward_age=p.maximum_carry_forward_age,
        minimum_lag=p.minimum_lag,
        maximum_lag=p.maximum_lag,
        lag_unit=p.lag_unit,
        minimum_reference_change=str(p.minimum_reference_change),
        default_frequency=p.default_frequency,
        default_transformation=p.default_transformation,
        valid_from=p.valid_from,
        valid_until=p.valid_until,
        active=p.active,
    )
