from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class ErpPaymentMethod(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "erp_payment_methods"
    __table_args__ = (
        UniqueConstraint("station_id", "source_payment_method_id", name="uq_erp_payment_methods_station_source"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    station_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stations.id"), nullable=True, index=True
    )
    source_payment_method_id: Mapped[str] = mapped_column(String(100), nullable=False)
    source_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source_name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_group: Mapped[str] = mapped_column(String(40), nullable=False, default="UNMAPPED", index=True)
    mapping_status: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDING", index=True)
    source_active: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    source_record_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_sync_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("erp_sync_runs.id"), nullable=True
    )


class FuelSalesFact(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "fuel_sales_facts"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "station_id",
            "source_sale_id",
            "source_sale_item_id",
            name="uq_fuel_sales_facts_natural_key",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    station_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stations.id"), nullable=False, index=True
    )
    source_sale_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    source_sale_item_id: Mapped[str] = mapped_column(String(100), nullable=False)
    source_document_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sold_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    business_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    erp_product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("erp_products.id"), nullable=False, index=True
    )
    canonical_product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id"), nullable=True, index=True
    )
    erp_payment_method_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("erp_payment_methods.id"), nullable=True, index=True
    )
    payment_method_group: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    operation_type: Mapped[str] = mapped_column(String(30), nullable=False, default="SALE")
    is_cancelled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    source_unit: Mapped[str | None] = mapped_column(String(30), nullable=True)
    quantity_source: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    volume_liters: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    gross_amount: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False, default=0)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False, default=0)
    surcharge_amount: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False, default=0)
    net_amount: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False, default=0)
    cost_per_liter: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    total_cost_amount: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    cost_source: Mapped[str | None] = mapped_column(String(40), nullable=True)
    margin_status: Mapped[str] = mapped_column(String(30), nullable=False, default="UNAVAILABLE")
    realized_price_per_liter: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    gross_margin_amount: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    gross_margin_per_liter: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    gross_margin_percent: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    metric_eligibility_status: Mapped[str] = mapped_column(String(40), nullable=False, default="EXCLUDED", index=True)
    metric_exclusion_reasons: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    source_record_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    last_sync_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("erp_sync_runs.id"), nullable=True
    )


class FuelRetailPriceSnapshot(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "fuel_retail_price_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "station_id",
            "erp_product_id",
            "erp_payment_method_id",
            "effective_from",
            name="uq_fuel_retail_price_snapshots_key",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    station_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stations.id"), nullable=False, index=True
    )
    erp_product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("erp_products.id"), nullable=False, index=True
    )
    canonical_product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id"), nullable=True, index=True
    )
    erp_payment_method_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("erp_payment_methods.id"), nullable=False, index=True
    )
    payment_method_group: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    price_per_liter: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    history_source: Mapped[str] = mapped_column(String(40), nullable=False, default="OBSERVED_BY_SYNC")
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    effective_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    source_record_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_sync_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("erp_sync_runs.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class FuelSalesDailyMetric(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "fuel_sales_daily_metrics"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "station_id",
            "business_date",
            "canonical_product_id",
            "payment_method_group",
            name="uq_fuel_sales_daily_metrics_key",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    station_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stations.id"), nullable=False, index=True
    )
    business_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    canonical_product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id"), nullable=False, index=True
    )
    payment_method_group: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    sales_item_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    net_volume_liters: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False, default=0)
    gross_sales_amount: Mapped[Decimal] = mapped_column(Numeric(22, 4), nullable=False, default=0)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(22, 4), nullable=False, default=0)
    net_sales_amount: Mapped[Decimal] = mapped_column(Numeric(22, 4), nullable=False, default=0)
    total_cost_amount: Mapped[Decimal | None] = mapped_column(Numeric(22, 4), nullable=True)
    cost_available_volume_liters: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False, default=0)
    realized_price_per_liter: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    gross_margin_amount: Mapped[Decimal | None] = mapped_column(Numeric(22, 4), nullable=True)
    gross_margin_per_liter: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    gross_margin_percent: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    negative_margin_item_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unmapped_item_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unmapped_volume_liters: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False, default=0)
    last_rebuilt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_sync_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("erp_sync_runs.id"), nullable=True
    )


class SalesMappingReconciliationRun(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "sales_mapping_reconciliation_runs"

    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="QUEUED", index=True)
    erp_product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("erp_products.id"), nullable=True, index=True
    )
    affected_facts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    affected_dates: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    requested_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
