"""Schemas — Sprint 8 purchase benchmarks."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class BenchmarkRunCreate(BaseModel):
    purchase_invoice_id: UUID
    comparison_mode: str | None = None


class BenchmarkReprocessRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=2000)


class BenchmarkReferenceOverrideRequest(BaseModel):
    reference_datetime: datetime
    reason: str = Field(min_length=3, max_length=2000)


class BenchmarkDistributorOverrideRequest(BaseModel):
    distributor_id: UUID
    reason: str = Field(min_length=3, max_length=2000)


class BenchmarkParametersUpsert(BaseModel):
    absolute_tolerance_per_liter: str = "0.005"
    percentage_tolerance: str = "0.001"
    allow_low_confidence_reference: bool = True
    default_comparison_mode: str = "DELIVERED_COST"


class BenchmarkRunListItem(BaseModel):
    id: UUID
    purchase_invoice_id: UUID
    station_id: UUID
    status: str
    comparison_mode: str
    reference_datetime: datetime | None = None
    reference_source: str
    reference_confidence: str
    item_count: int
    benchmarked_item_count: int
    opportunity_amount: str | None = None
    cost_variance_amount: str | None = None
    created_at: datetime
    finished_at: datetime | None = None
    snapshot_hash: str | None = None


class BenchmarkRunListResponse(BaseModel):
    items: list[BenchmarkRunListItem]
    total: int
    page: int
    page_size: int


class BenchmarkItemResponse(BaseModel):
    id: UUID
    group_key: str
    canonical_product_id: UUID | None = None
    actual_distributor_id: UUID | None = None
    volume_liters: str
    actual_delivered_cost: str
    actual_delivered_cost_per_liter: str | None = None
    benchmark_status: str
    decision_result: str
    best_quote_id: UUID | None = None
    best_distributor_id: UUID | None = None
    benchmark_cost_per_liter: str | None = None
    cost_variance_per_liter: str | None = None
    cost_variance_amount: str | None = None
    opportunity_amount: str | None = None
    actual_advantage_amount: str | None = None
    actual_distributor_rank: int | None = None
    candidate_count: int
    eligible_candidate_count: int
    exclusion_reasons: list | None = None
    warnings: list | None = None


class BenchmarkCandidateResponse(BaseModel):
    id: UUID
    quote_id: UUID
    quote_item_id: UUID
    distributor_id: UUID
    eligibility_status: str
    ranking_position: int | None = None
    is_best: bool
    delivered_cost_per_liter: str | None = None
    financial_equivalent_per_liter: str | None = None
    blocking_reasons: list | dict | None = None


class BenchmarkRunDetailResponse(BaseModel):
    id: UUID
    purchase_invoice_id: UUID
    station_id: UUID
    status: str
    comparison_mode: str
    reference_datetime: datetime | None = None
    reference_source: str
    reference_confidence: str
    trigger_type: str
    reprocess_of_run_id: UUID | None = None
    reprocess_reason: str | None = None
    item_count: int
    benchmarked_item_count: int
    warning_count: int
    error_count: int
    actual_total_cost: str
    benchmark_total_cost: str | None = None
    cost_variance_amount: str | None = None
    opportunity_amount: str | None = None
    actual_advantage_amount: str | None = None
    snapshot_hash: str | None = None
    input_snapshot: dict | None = None
    output_snapshot: dict | None = None
    started_at: datetime
    finished_at: datetime | None = None
    created_at: datetime
    items: list[BenchmarkItemResponse] = []


class BenchmarkSummaryResponse(BaseModel):
    purchase_group_count: int
    benchmarked_group_count: int
    purchased_volume_liters: str
    benchmarked_volume_liters: str
    coverage_volume_ratio: str | None = None
    actual_total_cost: str
    benchmark_total_cost: str | None = None
    cost_variance_amount: str | None = None
    opportunity_amount: str | None = None
    best_or_tied_count: int


class BenchmarkCoverageResponse(BaseModel):
    total_groups: int
    total_volume_liters: str
    total_value: str
    by_status: dict


class BenchmarkDataQualityResponse(BaseModel):
    unmapped_product_count: int
    unmapped_supplier_warning_count: int
    missing_cost_count: int
    missing_volume_count: int
    reference_unavailable_count: int
    no_quotes_count: int
    no_eligible_count: int
    not_comparable_count: int
    low_confidence_count: int


class BenchmarkOpportunityRow(BaseModel):
    benchmark_item_id: UUID
    purchase_invoice_id: UUID
    station_id: UUID
    canonical_product_id: UUID | None = None
    volume_liters: str
    opportunity_amount: str | None = None
    cost_variance_per_liter: str | None = None
    decision_result: str


class BenchmarkParametersResponse(BaseModel):
    id: UUID
    absolute_tolerance_per_liter: str
    percentage_tolerance: str
    allow_low_confidence_reference: bool
    default_comparison_mode: str
    valid_from: datetime
    valid_until: datetime | None = None
    active: bool
