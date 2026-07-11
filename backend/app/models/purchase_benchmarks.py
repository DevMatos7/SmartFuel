"""Models — Sprint 8 purchase × quote benchmarks."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
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


class PurchaseQuoteBenchmarkRun(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "purchase_quote_benchmark_runs"

    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    purchase_invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("fuel_purchase_invoices.id"), nullable=False, index=True
    )
    station_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stations.id"), nullable=False, index=True
    )

    status: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    comparison_mode: Mapped[str] = mapped_column(String(40), nullable=False)

    reference_datetime: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reference_source: Mapped[str] = mapped_column(String(40), nullable=False, default="UNKNOWN")
    reference_confidence: Mapped[str] = mapped_column(String(20), nullable=False, default="UNAVAILABLE")

    trigger_type: Mapped[str] = mapped_column(String(30), nullable=False, default="MANUAL")
    requested_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    reprocess_of_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("purchase_quote_benchmark_runs.id"), nullable=True
    )
    reprocess_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    input_snapshot: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    output_snapshot: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    snapshot_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    item_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    benchmarked_item_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    warning_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    actual_total_cost: Mapped[Decimal] = mapped_column(Numeric(24, 4), nullable=False, default=0)
    benchmark_total_cost: Mapped[Decimal | None] = mapped_column(Numeric(24, 4), nullable=True)
    cost_variance_amount: Mapped[Decimal | None] = mapped_column(Numeric(24, 4), nullable=True)
    opportunity_amount: Mapped[Decimal | None] = mapped_column(Numeric(24, 4), nullable=True)
    actual_advantage_amount: Mapped[Decimal | None] = mapped_column(Numeric(24, 4), nullable=True)

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PurchaseQuoteBenchmarkItem(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "purchase_quote_benchmark_items"

    benchmark_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("purchase_quote_benchmark_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    station_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stations.id"), nullable=False, index=True
    )
    purchase_invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("fuel_purchase_invoices.id"), nullable=False, index=True
    )

    group_key: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    canonical_product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id"), nullable=True, index=True
    )
    actual_distributor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("distributors.id"), nullable=True, index=True
    )

    volume_liters: Mapped[Decimal] = mapped_column(Numeric(22, 6), nullable=False, default=0)
    actual_delivered_cost: Mapped[Decimal] = mapped_column(Numeric(24, 4), nullable=False, default=0)
    actual_delivered_cost_per_liter: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    actual_financial_equivalent_cost: Mapped[Decimal | None] = mapped_column(Numeric(24, 4), nullable=True)
    actual_financial_equivalent_per_liter: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)

    benchmark_status: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    decision_result: Mapped[str] = mapped_column(String(40), nullable=False, index=True)

    best_quote_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    best_quote_item_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    best_distributor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("distributors.id"), nullable=True
    )

    benchmark_cost_per_liter: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    benchmark_total_cost: Mapped[Decimal | None] = mapped_column(Numeric(24, 4), nullable=True)
    cost_variance_per_liter: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    cost_variance_amount: Mapped[Decimal | None] = mapped_column(Numeric(24, 4), nullable=True)
    opportunity_amount: Mapped[Decimal | None] = mapped_column(Numeric(24, 4), nullable=True)
    actual_advantage_amount: Mapped[Decimal | None] = mapped_column(Numeric(24, 4), nullable=True)

    actual_distributor_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    candidate_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    eligible_candidate_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    exclusion_reasons: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    warnings: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    input_snapshot: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    result_snapshot: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    snapshot_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PurchaseQuoteBenchmarkCandidate(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "purchase_quote_benchmark_candidates"

    benchmark_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_quote_benchmark_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    quote_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    quote_item_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    distributor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)

    eligibility_status: Mapped[str] = mapped_column(String(40), nullable=False)
    blocking_reasons: Mapped[list | dict | None] = mapped_column(JSONB, nullable=True)
    warnings: Mapped[list | dict | None] = mapped_column(JSONB, nullable=True)

    raw_price_per_liter: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    delivered_cost_per_liter: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    financial_equivalent_per_liter: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)

    ranking_position: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_best: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    candidate_snapshot: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PurchaseBenchmarkOverride(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "purchase_benchmark_overrides"

    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    purchase_invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("fuel_purchase_invoices.id"), nullable=False, index=True
    )
    override_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    previous_value: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    new_value: Mapped[dict] = mapped_column(JSONB, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    deactivated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PurchaseBenchmarkParameter(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "purchase_benchmark_parameters"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "valid_from",
            name="uq_purchase_benchmark_parameters_org_valid_from",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    absolute_tolerance_per_liter: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False, default=0)
    percentage_tolerance: Mapped[Decimal] = mapped_column(Numeric(12, 8), nullable=False, default=0)
    allow_low_confidence_reference: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    default_comparison_mode: Mapped[str] = mapped_column(String(40), nullable=False, default="DELIVERED_COST")
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
