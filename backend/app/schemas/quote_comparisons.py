from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ComparisonScenarioInput(BaseModel):
    station_id: uuid.UUID
    product_id: uuid.UUID
    requested_volume_liters: Decimal = Field(..., gt=0)
    comparison_datetime: datetime
    required_delivery_at: datetime | None = None
    ranking_mode: str = "FINANCIAL_EQUIVALENT"
    ranking_scope: str = "BEST_PER_DISTRIBUTOR"


class ReprocessComparisonRequest(BaseModel):
    comparison_datetime: datetime | None = None
    required_delivery_at: datetime | None = None
    requested_volume_liters: Decimal | None = Field(default=None, gt=0)
    ranking_mode: str | None = None
    ranking_scope: str | None = None


class EligibilityReasonResponse(BaseModel):
    code: str
    severity: str
    message: str
    metadata: dict = Field(default_factory=dict)


class ComparisonCostsResponse(BaseModel):
    raw_price_per_liter: Decimal
    discount_per_liter: Decimal
    rebate_per_liter: Decimal
    freight_per_liter: Decimal
    other_cost_per_liter: Decimal
    delivered_cost_per_liter: Decimal
    delivered_total: Decimal
    financial_days: int | None = None
    annual_effective_rate: Decimal | None = None
    daily_rate: Decimal | None = None
    financial_equivalent_cost_per_liter: Decimal | None = None
    financial_equivalent_total: Decimal | None = None


class DistributorBrief(BaseModel):
    id: uuid.UUID
    name: str


class ComparisonResultResponse(BaseModel):
    quote_id: uuid.UUID
    quote_item_id: uuid.UUID
    quote_number: int | None = None
    distributor: DistributorBrief
    eligibility_status: str
    eligibility_reasons: list[EligibilityReasonResponse]
    costs: ComparisonCostsResponse
    rank_position: int | None = None
    difference_per_liter: Decimal | None = None
    difference_total: Decimal | None = None
    is_best_for_distributor: bool = False
    is_best_overall: bool = False
    payment_term_name: str | None = None
    delivery_expected_at: datetime | None = None
    effective_valid_until: datetime | None = None
    calculation_snapshot: dict = Field(default_factory=dict)


class ComparisonSummaryResponse(BaseModel):
    eligible_count: int
    warning_count: int
    ineligible_count: int
    distributor_count: int
    best_cost_per_liter: Decimal | None = None
    highest_cost_per_liter: Decimal | None = None
    average_cost_per_liter: Decimal | None = None
    spread_absolute: Decimal | None = None
    spread_percent: Decimal | None = None


class ComparisonScenarioResponse(BaseModel):
    station_id: uuid.UUID
    product_id: uuid.UUID
    requested_volume_liters: Decimal
    comparison_datetime: datetime
    required_delivery_at: datetime | None
    ranking_mode: str
    ranking_scope: str


class ComparisonRunResponse(BaseModel):
    id: uuid.UUID
    status: str
    methodology_version: str
    scenario: ComparisonScenarioResponse
    summary: ComparisonSummaryResponse
    results: list[ComparisonResultResponse] = Field(default_factory=list)
    calculation_hash: str | None = None
    processing_duration_ms: int | None = None
    reprocessed_from_run_id: uuid.UUID | None = None
    input_snapshot: dict = Field(default_factory=dict)
    created_at: datetime
    created_by: uuid.UUID


class ComparisonRunListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    station_id: uuid.UUID
    product_id: uuid.UUID
    requested_volume_liters: Decimal
    comparison_datetime: datetime
    ranking_mode: str
    ranking_scope: str
    best_cost_per_liter: Decimal | None
    eligible_count: int
    distributor_count: int
    created_at: datetime
    created_by: uuid.UUID


class ComparisonRunListResponse(BaseModel):
    items: list[ComparisonRunListItem]
    total: int
    page: int
    page_size: int
