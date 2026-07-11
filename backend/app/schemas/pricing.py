"""Schemas Sprint 11 — formação de preço."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PricingPolicyCreate(BaseModel):
    name: str
    station_id: uuid.UUID | None = None
    canonical_product_id: uuid.UUID | None = None
    price_type: str = "POSTED_PRICE"
    cost_basis_type: str = "LAST_CONFIRMED_PURCHASE"
    weighted_cost_window_days: int | None = None
    minimum_purchase_count: int | None = None
    minimum_purchase_volume: Decimal | None = None
    minimum_margin_per_liter: Decimal | None = None
    minimum_margin_percentage: Decimal | None = None
    minimum_markup_percentage: Decimal | None = None
    target_margin_per_liter: Decimal | None = None
    target_margin_percentage: Decimal | None = None
    target_markup_percentage: Decimal | None = None
    maximum_increase_per_liter: Decimal | None = None
    maximum_decrease_per_liter: Decimal | None = None
    maximum_increase_percentage: Decimal | None = None
    maximum_decrease_percentage: Decimal | None = None
    minimum_change_per_liter: Decimal | None = None
    rounding_policy: str = "NEAREST_CENT"
    rounding_increment: Decimal | None = None
    default_scenario: str = "BALANCED"
    allow_low_confidence_cost: bool = False
    require_market_signal: bool = False
    require_evidence_on_approve: bool = False
    allow_self_approval: bool = False
    required_approvals: int = 1
    implementation_tolerance_per_liter: Decimal = Decimal("0.01")
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    active: bool = True


class PricingPolicyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    station_id: uuid.UUID | None
    canonical_product_id: uuid.UUID | None
    price_type: str
    name: str
    status: str
    cost_basis_type: str
    minimum_margin_per_liter: Decimal | None
    target_margin_per_liter: Decimal | None
    rounding_policy: str
    default_scenario: str
    required_approvals: int
    allow_self_approval: bool
    valid_from: datetime
    valid_until: datetime | None
    active: bool


class PricingRunCreate(BaseModel):
    station_id: uuid.UUID | None = None
    canonical_product_id: uuid.UUID | None = None
    price_type: str = "POSTED_PRICE"
    reference_datetime: datetime | None = None
    trigger_type: str = "MANUAL"
    items: list[dict[str, Any]] | None = None
    synthetic_cost: dict[str, Any] | None = None
    synthetic_price: dict[str, Any] | None = None
    synthetic_policy: dict[str, Any] | None = None
    market_signal: dict[str, Any] | None = None
    reference_daily_volume: Decimal | None = None
    allow_non_posted: bool = False


class PricingRunReprocess(BaseModel):
    reason: str = Field(min_length=3)


class PricingRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    status: str
    trigger_type: str
    reference_datetime: datetime
    station_id: uuid.UUID | None
    canonical_product_id: uuid.UUID | None
    price_type: str
    item_count: int
    recommendation_count: int
    warning_count: int
    error_count: int
    snapshot_hash: str | None
    interpretive_disclaimer: str
    started_at: datetime
    finished_at: datetime | None
    reprocess_of_run_id: uuid.UUID | None = None


class PricingItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    recommendation_run_id: uuid.UUID
    station_id: uuid.UUID
    canonical_product_id: uuid.UUID
    price_type: str
    current_price: Decimal | None
    current_price_source: str | None
    cost_basis_type: str
    cost_per_liter: Decimal | None
    cost_confidence: str
    current_margin_per_liter: Decimal | None
    current_margin_percentage: Decimal | None
    current_markup_percentage: Decimal | None
    commercial_floor_price: Decimal | None
    target_price: Decimal | None
    raw_recommended_price: Decimal | None
    recommended_price: Decimal | None
    recommended_change_per_liter: Decimal | None
    recommendation_status: str
    quality_status: str
    guardrail_applied: bool
    reasons: list | None
    warnings: list | None
    snapshot_hash: str
    result_snapshot: dict | None = None


class DecisionCreate(BaseModel):
    selected_scenario: str | None = None
    decision_reason: str | None = None
    required_approvals: int = 1
    expires_at: datetime | None = None


class DecisionAction(BaseModel):
    comment: str | None = None
    approved_price: Decimal | None = None
    allow_self_approval: bool = False


class DecisionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    recommendation_item_id: uuid.UUID
    status: str
    selected_scenario: str | None
    recommended_price: Decimal
    approved_price: Decimal | None
    decision_reason: str | None
    created_by: uuid.UUID | None
    created_at: datetime
    approved_at: datetime | None
    rejected_at: datetime | None


class EvidenceCreate(BaseModel):
    evidence_type: str = "NOTE"
    description: str | None = None
    storage_key: str | None = None
    sha256: str | None = None
    content_type: str | None = None
    size_bytes: int | None = None
    original_filename: str | None = None
    structured_payload: dict[str, Any] | None = None


class ImplementationConfirm(BaseModel):
    implemented_price: Decimal
    implemented_at: datetime | None = None
    note: str | None = None
    tolerance: Decimal | None = None


class ErpPriceCheck(BaseModel):
    implemented_price: Decimal | None = None
    price_snapshot_id: uuid.UUID | None = None
    tolerance: Decimal | None = None
    stale: bool = False


class SyntheticHomologationRequest(BaseModel):
    station_id: uuid.UUID
    canonical_product_id: uuid.UUID
