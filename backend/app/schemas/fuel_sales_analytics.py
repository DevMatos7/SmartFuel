from __future__ import annotations

import uuid
from datetime import date

from pydantic import BaseModel, Field


class FuelSalesFilterParams(BaseModel):
    station_ids: list[uuid.UUID] = Field(default_factory=list)
    product_ids: list[uuid.UUID] | None = None
    date_from: date
    date_to: date
    payment_method_groups: list[str] | None = None
    include_returns: bool = True


class FuelSalesSummaryResponse(BaseModel):
    net_volume_liters: str
    net_sales_amount: str
    realized_price_per_liter: str | None = None
    cost_coverage_percent: str | None = None
    item_count: int
    total_cost_amount: str | None = None
    gross_margin_amount: str | None = None
    gross_margin_per_liter: str | None = None
    gross_margin_percent: str | None = None


class FuelSalesTrendPoint(BaseModel):
    business_date: str
    net_volume_liters: str
    net_sales_amount: str
    realized_price_per_liter: str | None = None
    gross_margin_amount: str | None = None
    gross_margin_per_liter: str | None = None


class FuelSalesByStationRow(BaseModel):
    station_id: str
    station_name: str
    net_volume_liters: str
    net_sales_amount: str
    realized_price_per_liter: str | None = None
    participation_percent: str | None = None


class FuelSalesByProductRow(BaseModel):
    product_id: str
    product_name: str
    net_volume_liters: str
    net_sales_amount: str
    realized_price_per_liter: str | None = None
    cost_coverage_percent: str | None = None
    total_cost_amount: str | None = None
    gross_margin_amount: str | None = None
    gross_margin_per_liter: str | None = None
    gross_margin_percent: str | None = None


class FuelSalesDataQualityResponse(BaseModel):
    unmapped_item_count: int
    unmapped_volume_liters: str
    missing_cost_item_count: int
    missing_cost_volume_liters: str
    quarantined_item_count: int
    pending_payment_methods: int


class FuelSalesFreshnessResponse(BaseModel):
    status: str
    security_status: str | None = None
    last_completed_run_at: str | None = None
    source_upper_bound: str | None = None


class FuelSalesUnmappedRow(BaseModel):
    erp_product_id: str
    erp_product_code: str | None = None
    erp_description: str
    item_count: int
    volume_liters: str
    net_amount: str


class FuelSalesMissingCostRow(BaseModel):
    product_id: str | None = None
    product_name: str
    item_count: int
    volume_liters: str
    net_amount: str


class FuelSalesQuarantinedRow(BaseModel):
    reason: str
    item_count: int


class FuelSalesPriceVarianceRow(BaseModel):
    product_id: str
    product_name: str
    payment_method_group: str | None = None
    net_volume_liters: str
    realized_price_per_liter: str | None = None
    registered_price_per_liter: str | None = None
    variance_per_liter: str | None = None
    variance_percent: str | None = None


class FuelSalesRetailPriceRow(BaseModel):
    station_id: str
    station_name: str
    product_id: str | None = None
    product_name: str
    payment_method_group: str | None = None
    payment_method_name: str | None = None
    price_per_liter: str
    observed_at: str


class ReconcileMappingsRequest(BaseModel):
    erp_product_id: uuid.UUID | None = None
    station_ids: list[uuid.UUID] = Field(default_factory=list)


class ReconcileMappingsResponse(BaseModel):
    runs: list[dict]
