from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class QuoteItemBase(BaseModel):
    product_id: uuid.UUID
    distribution_base_id: uuid.UUID | None = None
    sequence: int | None = None
    quoted_price_per_liter: str
    payment_term_id: uuid.UUID
    freight_type: str = "CIF"
    freight_calculation_type: str = "NONE"
    freight_value_total: str | None = None
    freight_value_per_liter: str | None = None
    discount_per_liter: str = "0.0000"
    rebate_per_liter: str = "0.0000"
    other_cost_per_liter: str = "0.0000"
    other_cost_description: str | None = None
    minimum_volume_liters: str
    available_volume_liters: str | None = None
    delivery_expected_at: datetime | None = None
    valid_until: datetime | None = None
    notes: str | None = None


class QuoteItemCreate(QuoteItemBase):
    expected_version: int


class QuoteItemUpdate(BaseModel):
    expected_version: int
    product_id: uuid.UUID | None = None
    distribution_base_id: uuid.UUID | None = None
    sequence: int | None = None
    quoted_price_per_liter: str | None = None
    payment_term_id: uuid.UUID | None = None
    freight_type: str | None = None
    freight_calculation_type: str | None = None
    freight_value_total: str | None = None
    freight_value_per_liter: str | None = None
    discount_per_liter: str | None = None
    rebate_per_liter: str | None = None
    other_cost_per_liter: str | None = None
    other_cost_description: str | None = None
    minimum_volume_liters: str | None = None
    available_volume_liters: str | None = None
    delivery_expected_at: datetime | None = None
    valid_until: datetime | None = None
    notes: str | None = None


class QuoteItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_id: uuid.UUID
    distribution_base_id: uuid.UUID | None
    sequence: int
    quoted_price_per_liter: str
    payment_term_id: uuid.UUID
    payment_type_snapshot: str
    payment_term_days_snapshot: int
    payment_term_name_snapshot: str
    freight_type: str
    freight_calculation_type: str
    freight_value_total: str | None
    freight_value_per_liter: str | None
    discount_per_liter: str
    rebate_per_liter: str
    other_cost_per_liter: str
    other_cost_description: str | None
    minimum_volume_liters: str
    available_volume_liters: str | None
    delivery_expected_at: datetime | None
    valid_until: datetime | None
    notes: str | None
    item_effective_status: str | None = None
    effective_valid_until: datetime | None = None

    @field_validator(
        "quoted_price_per_liter",
        "freight_value_total",
        "freight_value_per_liter",
        "discount_per_liter",
        "rebate_per_liter",
        "other_cost_per_liter",
        "minimum_volume_liters",
        "available_volume_liters",
        mode="before",
    )
    @classmethod
    def _decimal_to_str(cls, value: object) -> str | None:
        if value is None:
            return None
        if isinstance(value, Decimal):
            return str(value)
        return str(value)


class QuoteEvidenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    category: str
    original_file_name: str
    content_type: str
    file_extension: str
    size_bytes: int
    sha256: str
    is_supplemental: bool
    active: bool
    uploaded_by: uuid.UUID
    uploaded_at: datetime


class QuoteCreate(BaseModel):
    station_id: uuid.UUID
    distributor_id: uuid.UUID
    distribution_base_id: uuid.UUID | None = None
    quoted_at: datetime
    valid_until: datetime
    source_channel: str
    entry_method: str = "MANUAL"
    origin: str = "MANUAL_OPERATIONAL"
    analytics_eligible: bool = True
    seller_name: str | None = None
    seller_contact: str | None = None
    external_reference: str | None = None
    source_description: str | None = None
    notes: str | None = None


class QuoteUpdate(BaseModel):
    expected_version: int
    station_id: uuid.UUID | None = None
    distributor_id: uuid.UUID | None = None
    distribution_base_id: uuid.UUID | None = None
    quoted_at: datetime | None = None
    valid_until: datetime | None = None
    source_channel: str | None = None
    entry_method: str | None = None
    origin: str | None = None
    analytics_eligible: bool | None = None
    seller_name: str | None = None
    seller_contact: str | None = None
    external_reference: str | None = None
    source_description: str | None = None
    notes: str | None = None


class QuoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    station_id: uuid.UUID
    distributor_id: uuid.UUID
    distribution_base_id: uuid.UUID | None
    quote_number: int
    quoted_at: datetime
    valid_until: datetime
    source_channel: str
    entry_method: str
    origin: str
    analytics_eligible: bool
    seller_name: str | None
    seller_contact: str | None
    external_reference: str | None
    source_description: str | None
    notes: str | None
    status: str
    effective_status: str
    version: int
    replaces_quote_id: uuid.UUID | None
    duplicated_from_quote_id: uuid.UUID | None
    activated_at: datetime | None
    activated_by: uuid.UUID | None
    cancelled_at: datetime | None
    cancelled_by: uuid.UUID | None
    cancellation_reason: str | None
    superseded_at: datetime | None
    superseded_by_quote_id: uuid.UUID | None
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime
    items: list[QuoteItemResponse] = Field(default_factory=list)
    evidences: list[QuoteEvidenceResponse] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class QuoteListItem(BaseModel):
    id: uuid.UUID
    quote_number: int
    station_id: uuid.UUID
    distributor_id: uuid.UUID
    quoted_at: datetime
    valid_until: datetime
    source_channel: str
    status: str
    effective_status: str
    version: int
    item_count: int


class QuoteListResponse(BaseModel):
    items: list[QuoteListItem]
    total: int
    page: int
    page_size: int
    summary: dict[str, int]


class VersionedAction(BaseModel):
    expected_version: int


class CancelQuoteRequest(VersionedAction):
    reason: str


class ReviseQuoteRequest(BaseModel):
    reason: str


class DuplicateQuoteRequest(BaseModel):
    target_station_id: uuid.UUID
    quoted_at: datetime
    valid_until: datetime
    copy_evidences: bool = False
    notes: str | None = None


class DeactivateEvidenceRequest(BaseModel):
    reason: str


class QuoteHistoryEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    action: str
    version: int
    reason: str | None
    changed_fields: dict | None
    metadata: dict | None = Field(default=None, validation_alias="metadata_")
    user_id: uuid.UUID | None
    request_id: uuid.UUID | None
    created_at: datetime
    quote_item_id: uuid.UUID | None
    quote_evidence_id: uuid.UUID | None


class QuoteHistoryListResponse(BaseModel):
    items: list[QuoteHistoryEntry]
    total: int
    page: int
    page_size: int


class ItemPrefillResponse(BaseModel):
    minimum_volume_liters: str
    distribution_base_id: str | None
    supplier_allowed: bool
    rule_source: str
    alert_supplier_not_allowed: bool


class ExpirationRunResponse(BaseModel):
    expired_count: int
    skipped: bool = False
    reason: str | None = None
