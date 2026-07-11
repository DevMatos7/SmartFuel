from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class FuelPurchaseInvoice(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "fuel_purchase_invoices"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "station_id",
            "source_invoice_id",
            name="uq_fuel_purchase_invoices_natural_key",
        ),
        # Unicidade parcial (access_key IS NOT NULL) criada na migration 0015.
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    station_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stations.id"), nullable=False, index=True
    )
    source_invoice_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    source_document_number: Mapped[str] = mapped_column(String(100), nullable=False)
    source_series: Mapped[str | None] = mapped_column(String(20), nullable=True)
    access_key: Mapped[str | None] = mapped_column(String(44), nullable=True, index=True)
    # Flag do XPERT (COMPENTRADAS.IMPORTOU_XML). Não implica arquivo no MinIO.
    xml_imported_in_erp: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    erp_supplier_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("erp_suppliers.id"), nullable=True, index=True
    )
    distributor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("distributors.id"), nullable=True, index=True
    )
    source_supplier_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    issue_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    entry_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    operation_type: Mapped[str] = mapped_column(String(40), nullable=False, default="PURCHASE")
    source_status: Mapped[str] = mapped_column(String(80), nullable=False)
    is_cancelled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    gross_amount: Mapped[Decimal] = mapped_column(Numeric(22, 4), nullable=False, default=0)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(22, 4), nullable=False, default=0)
    freight_amount: Mapped[Decimal] = mapped_column(Numeric(22, 4), nullable=False, default=0)
    insurance_amount: Mapped[Decimal] = mapped_column(Numeric(22, 4), nullable=False, default=0)
    other_expenses_amount: Mapped[Decimal] = mapped_column(Numeric(22, 4), nullable=False, default=0)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(22, 4), nullable=False, default=0)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(22, 4), nullable=False, default=0)

    payment_condition_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source_base_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    allocation_method: Mapped[str | None] = mapped_column(String(40), nullable=True)

    metric_eligibility_status: Mapped[str] = mapped_column(
        String(40), nullable=False, default="EXCLUDED", index=True
    )
    metric_exclusion_reasons: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    source_record_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    last_sync_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("erp_sync_runs.id"), nullable=True
    )


class FuelPurchaseItem(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "fuel_purchase_items"
    __table_args__ = (
        UniqueConstraint(
            "station_id",
            "source_invoice_id",
            "source_invoice_item_id",
            name="uq_fuel_purchase_items_natural_key",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    station_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stations.id"), nullable=False, index=True
    )
    purchase_invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("fuel_purchase_invoices.id"), nullable=False, index=True
    )
    source_invoice_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    source_invoice_item_id: Mapped[str] = mapped_column(String(100), nullable=False)
    source_product_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    erp_product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("erp_products.id"), nullable=True, index=True
    )
    canonical_product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id"), nullable=True, index=True
    )

    source_description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_unit: Mapped[str | None] = mapped_column(String(30), nullable=True)
    source_quantity: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    volume_liters: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)

    unit_price: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False, default=0)
    gross_item_amount: Mapped[Decimal] = mapped_column(Numeric(22, 4), nullable=False, default=0)
    gross_amount_source: Mapped[str | None] = mapped_column(String(40), nullable=True)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(22, 4), nullable=False, default=0)
    rebate_amount: Mapped[Decimal] = mapped_column(Numeric(22, 4), nullable=False, default=0)
    allocated_freight_amount: Mapped[Decimal] = mapped_column(Numeric(22, 4), nullable=False, default=0)
    allocated_insurance_amount: Mapped[Decimal] = mapped_column(Numeric(22, 4), nullable=False, default=0)
    allocated_other_expenses: Mapped[Decimal] = mapped_column(Numeric(22, 4), nullable=False, default=0)

    icms_amount: Mapped[Decimal | None] = mapped_column(Numeric(22, 4), nullable=True)
    icms_st_amount: Mapped[Decimal | None] = mapped_column(Numeric(22, 4), nullable=True)
    fcp_amount: Mapped[Decimal | None] = mapped_column(Numeric(22, 4), nullable=True)
    pis_amount: Mapped[Decimal | None] = mapped_column(Numeric(22, 4), nullable=True)
    cofins_amount: Mapped[Decimal | None] = mapped_column(Numeric(22, 4), nullable=True)

    erp_recorded_cost: Mapped[Decimal | None] = mapped_column(Numeric(22, 4), nullable=True)
    accounting_cost: Mapped[Decimal | None] = mapped_column(Numeric(22, 4), nullable=True)
    commercial_delivered_cost: Mapped[Decimal] = mapped_column(Numeric(22, 4), nullable=False, default=0)
    delivered_cost_per_liter: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)

    cfop: Mapped[str | None] = mapped_column(String(20), nullable=True)
    ncm: Mapped[str | None] = mapped_column(String(20), nullable=True)
    operation_type: Mapped[str] = mapped_column(String(40), nullable=False, default="PURCHASE")
    is_cancelled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    metric_eligibility_status: Mapped[str] = mapped_column(
        String(40), nullable=False, default="EXCLUDED", index=True
    )
    metric_exclusion_reasons: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    source_record_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_sync_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("erp_sync_runs.id"), nullable=True
    )


class NfeXmlDocument(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "nfe_xml_documents"
    __table_args__ = (
        UniqueConstraint("organization_id", "access_key", name="uq_nfe_xml_documents_access_key"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    station_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stations.id"), nullable=False, index=True
    )
    purchase_invoice_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("fuel_purchase_invoices.id"), nullable=True, index=True
    )

    access_key: Mapped[str] = mapped_column(String(44), nullable=False, index=True)
    issuer_cnpj: Mapped[str] = mapped_column(String(14), nullable=False)
    recipient_cnpj: Mapped[str] = mapped_column(String(14), nullable=False)
    document_number: Mapped[str] = mapped_column(String(100), nullable=False)
    series: Mapped[str] = mapped_column(String(20), nullable=False)
    issue_datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(22, 4), nullable=False)

    xml_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    xml_storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    xml_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)

    parse_status: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDING", index=True)
    parse_errors: Mapped[list | dict | None] = mapped_column(JSONB, nullable=True)
    reconciliation_status: Mapped[str] = mapped_column(
        String(40), nullable=False, default="PENDING", index=True
    )
    reconciliation_details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    imported_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AccountsPayableTitle(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "accounts_payable_titles"
    __table_args__ = (
        UniqueConstraint(
            "station_id",
            "source_title_id",
            name="uq_accounts_payable_titles_natural_key",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    station_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stations.id"), nullable=False, index=True
    )
    source_title_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    source_invoice_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    purchase_invoice_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("fuel_purchase_invoices.id"), nullable=True, index=True
    )
    invoice_link_status: Mapped[str] = mapped_column(
        String(40), nullable=False, default="PENDING_INVOICE_LINK", index=True
    )

    source_supplier_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    erp_supplier_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("erp_suppliers.id"), nullable=True, index=True
    )
    distributor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("distributors.id"), nullable=True, index=True
    )

    installment_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    document_number: Mapped[str | None] = mapped_column(String(100), nullable=True)

    issue_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    due_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    payment_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    original_amount: Mapped[Decimal] = mapped_column(Numeric(22, 4), nullable=False)
    paid_amount: Mapped[Decimal | None] = mapped_column(Numeric(22, 4), nullable=True)
    open_amount: Mapped[Decimal] = mapped_column(Numeric(22, 4), nullable=False)
    interest_amount: Mapped[Decimal | None] = mapped_column(Numeric(22, 4), nullable=True)
    penalty_amount: Mapped[Decimal | None] = mapped_column(Numeric(22, 4), nullable=True)
    discount_amount: Mapped[Decimal | None] = mapped_column(Numeric(22, 4), nullable=True)

    source_status: Mapped[str] = mapped_column(String(80), nullable=False)
    normalized_status: Mapped[str] = mapped_column(String(40), nullable=False, default="UNKNOWN", index=True)
    is_cancelled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    payment_method: Mapped[str | None] = mapped_column(String(80), nullable=True)

    source_record_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_sync_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("erp_sync_runs.id"), nullable=True
    )


class FuelPurchaseDailyMetric(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "fuel_purchase_daily_metrics"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "station_id",
            "business_date",
            "canonical_product_id",
            "distributor_id",
            name="uq_fuel_purchase_daily_metrics_key",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    station_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stations.id"), nullable=False, index=True
    )
    business_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    canonical_product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id"), nullable=True, index=True
    )
    distributor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("distributors.id"), nullable=True, index=True
    )

    invoice_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    item_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    purchased_volume_liters: Mapped[Decimal] = mapped_column(Numeric(22, 6), nullable=False, default=0)

    gross_purchase_amount: Mapped[Decimal] = mapped_column(Numeric(24, 4), nullable=False, default=0)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(24, 4), nullable=False, default=0)
    freight_amount: Mapped[Decimal] = mapped_column(Numeric(24, 4), nullable=False, default=0)
    other_expenses_amount: Mapped[Decimal] = mapped_column(Numeric(24, 4), nullable=False, default=0)
    commercial_delivered_cost: Mapped[Decimal] = mapped_column(Numeric(24, 4), nullable=False, default=0)
    average_delivered_cost_per_liter: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    erp_recorded_cost: Mapped[Decimal | None] = mapped_column(Numeric(24, 4), nullable=True)

    unmapped_item_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unmapped_volume_liters: Mapped[Decimal] = mapped_column(Numeric(22, 6), nullable=False, default=0)
    missing_cost_item_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    last_rebuilt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_sync_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("erp_sync_runs.id"), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
