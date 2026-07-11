from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


def _dec_str(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return format(value, "f")


class FuelPurchasesSummaryResponse(BaseModel):
    purchased_volume_liters: str
    gross_purchase_amount: str
    commercial_delivered_cost: str
    average_delivered_cost_per_liter: str | None = None
    total_freight_amount: str
    total_discount_amount: str
    invoice_count: int
    weighted_term_days: str | None = None
    open_payable_amount: str | None = None
    erp_recorded_cost: str | None = None


class FuelPurchasesTrendPoint(BaseModel):
    business_date: date
    purchased_volume_liters: str
    gross_purchase_amount: str
    commercial_delivered_cost: str
    average_delivered_cost_per_liter: str | None = None
    freight_amount: str


class FuelPurchasesByProductRow(BaseModel):
    product_id: UUID | None = None
    product_name: str
    purchased_volume_liters: str
    gross_purchase_amount: str
    commercial_delivered_cost: str
    average_delivered_cost_per_liter: str | None = None


class FuelPurchasesByStationRow(BaseModel):
    station_id: UUID
    station_name: str
    purchased_volume_liters: str
    gross_purchase_amount: str
    commercial_delivered_cost: str
    invoice_count: int


class FuelPurchasesByDistributorRow(BaseModel):
    distributor_id: UUID | None = None
    distributor_name: str
    purchased_volume_liters: str
    gross_purchase_amount: str
    commercial_delivered_cost: str
    average_delivered_cost_per_liter: str | None = None
    invoice_count: int


class FuelPurchasesCostsResponse(BaseModel):
    purchased_volume_liters: str
    gross_purchase_amount: str
    discount_amount: str
    freight_amount: str
    insurance_amount: str
    other_expenses_amount: str
    commercial_delivered_cost: str
    erp_recorded_cost: str | None = None
    average_delivered_cost_per_liter: str | None = None
    invoice_count: int
    item_count: int


class FuelPurchasesDataQualityResponse(BaseModel):
    unmapped_item_count: int
    unmapped_volume_liters: str
    unmapped_supplier_count: int
    missing_cost_item_count: int
    missing_xml_count: int
    xml_mismatch_count: int
    invalid_access_key_count: int
    quarantined_item_count: int


class FuelPurchasesFreshnessResponse(BaseModel):
    status: str
    security_status: str | None = None
    last_completed_run_at: datetime | None = None


class FuelPurchaseInvoiceListRow(BaseModel):
    id: UUID
    station_id: UUID
    station_name: str
    source_document_number: str
    source_series: str | None = None
    access_key: str | None = None
    entry_date: date
    issue_date: date
    distributor_name: str | None = None
    purchased_volume_liters: str
    total_amount: str
    delivered_cost_per_liter: str | None = None
    has_xml: bool  # arquivo disponível em nfe_xml_documents / MinIO
    xml_imported_in_erp: bool = False  # flag COMPENTRADAS.IMPORTOU_XML
    xml_reconciliation_status: str | None = None
    metric_eligibility_status: str
    is_cancelled: bool


class FuelPurchaseInvoiceDetail(BaseModel):
    id: UUID
    station_id: UUID
    station_name: str
    source_invoice_id: str
    source_document_number: str
    source_series: str | None = None
    access_key: str | None = None
    xml_imported_in_erp: bool = False
    has_xml_file: bool = False
    distributor_id: UUID | None = None
    distributor_name: str | None = None
    source_supplier_id: str
    issue_date: date
    entry_date: date
    operation_type: str
    source_status: str
    is_cancelled: bool
    gross_amount: str
    discount_amount: str
    freight_amount: str
    insurance_amount: str
    other_expenses_amount: str
    tax_amount: str
    total_amount: str
    purchased_volume_liters: str
    commercial_delivered_cost: str
    average_delivered_cost_per_liter: str | None = None
    allocation_method: str | None = None
    metric_eligibility_status: str
    metric_exclusion_reasons: list[str] | None = None
    payment_condition_id: str | None = None


class FuelPurchaseInvoiceItemRow(BaseModel):
    id: UUID
    source_description: str | None = None
    product_name: str | None = None
    source_product_id: str
    volume_liters: str | None = None
    source_quantity: str
    source_unit: str | None = None
    unit_price: str
    gross_item_amount: str
    discount_amount: str
    allocated_freight_amount: str
    allocated_insurance_amount: str
    allocated_other_expenses: str
    commercial_delivered_cost: str
    delivered_cost_per_liter: str | None = None
    erp_recorded_cost: str | None = None
    accounting_cost: str | None = None
    icms_amount: str | None = None
    icms_st_amount: str | None = None
    fcp_amount: str | None = None
    pis_amount: str | None = None
    cofins_amount: str | None = None
    cfop: str | None = None
    ncm: str | None = None
    metric_eligibility_status: str
    metric_exclusion_reasons: list[str] | None = None


class FuelPurchaseInvoiceXmlInfo(BaseModel):
    id: UUID | None = None
    access_key: str | None = None
    parse_status: str | None = None
    reconciliation_status: str | None = None
    reconciliation_details: dict[str, Any] | None = None
    xml_size_bytes: int | None = None
    imported_at: datetime | None = None


class FuelPurchaseInvoiceTitleRow(BaseModel):
    id: UUID
    installment_number: int | None = None
    document_number: str | None = None
    due_date: date
    payment_date: date | None = None
    original_amount: str
    paid_amount: str | None = None
    open_amount: str
    normalized_status: str
    source_status: str


class PaginatedInvoices(BaseModel):
    items: list[FuelPurchaseInvoiceListRow]
    total: int
    page: int
    page_size: int


class AccountsPayableSummaryResponse(BaseModel):
    open_amount: str
    overdue_amount: str
    due_in_7_days_amount: str
    due_in_30_days_amount: str
    weighted_term_days: str | None = None
    partially_paid_count: int
    open_title_count: int


class AccountsPayableAgingBucket(BaseModel):
    bucket: str
    title_count: int
    open_amount: str


class AccountsPayableTitleListRow(BaseModel):
    id: UUID
    station_id: UUID
    station_name: str
    distributor_name: str | None = None
    document_number: str | None = None
    installment_number: int | None = None
    due_date: date
    payment_date: date | None = None
    original_amount: str
    paid_amount: str | None = None
    open_amount: str
    normalized_status: str
    purchase_invoice_id: UUID | None = None


class PaginatedTitles(BaseModel):
    items: list[AccountsPayableTitleListRow]
    total: int
    page: int
    page_size: int


class AccountsPayableBySupplierRow(BaseModel):
    supplier_id: str
    supplier_name: str
    open_amount: str
    title_count: int


class DueCalendarDay(BaseModel):
    due_date: date
    open_amount: str
    title_count: int


class NfeDocumentRow(BaseModel):
    id: UUID
    station_id: UUID
    station_name: str
    access_key: str
    document_number: str
    series: str
    issuer_cnpj: str
    issue_datetime: datetime
    total_amount: str
    parse_status: str
    reconciliation_status: str
    purchase_invoice_id: UUID | None = None
    xml_size_bytes: int


class NfeDocumentDetail(NfeDocumentRow):
    recipient_cnpj: str
    parse_errors: Any = None
    reconciliation_details: dict[str, Any] | None = None
    imported_at: datetime


class PaginatedNfeDocuments(BaseModel):
    items: list[NfeDocumentRow]
    total: int
    page: int
    page_size: int


class NfeImportResponse(BaseModel):
    id: UUID
    access_key: str
    parse_status: str
    reconciliation_status: str


class NfeReconcileResponse(BaseModel):
    id: UUID
    reconciliation_status: str
    reconciliation_details: dict[str, Any] | None = None
