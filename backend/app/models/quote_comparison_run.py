import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import UUIDPrimaryKeyMixin


class QuoteComparisonRun(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "quote_comparison_runs"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True
    )
    station_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stations.id"), nullable=False, index=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id"), nullable=False, index=True
    )

    requested_volume_liters: Mapped[Decimal] = mapped_column(Numeric(16, 3), nullable=False)
    comparison_datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    required_delivery_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    ranking_mode: Mapped[str] = mapped_column(String(40), nullable=False)
    ranking_scope: Mapped[str] = mapped_column(String(40), nullable=False)

    financial_parameter_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("financial_parameters.id"), nullable=True
    )
    methodology_version: Mapped[str] = mapped_column(String(50), nullable=False)

    status: Mapped[str] = mapped_column(String(30), nullable=False, default="PROCESSING", index=True)
    reprocessed_from_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("quote_comparison_runs.id"), nullable=True
    )

    eligible_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    warning_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ineligible_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    distributor_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    best_cost_per_liter: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    highest_cost_per_liter: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    average_cost_per_liter: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    spread_absolute: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    spread_percent: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)

    input_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    summary_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    calculation_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    processing_duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    results: Mapped[list["QuoteComparisonResult"]] = relationship(
        "QuoteComparisonResult", back_populates="run", cascade="all, delete-orphan"
    )


class QuoteComparisonResult(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "quote_comparison_results"

    comparison_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("quote_comparison_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )

    quote_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("quotes.id"), nullable=False)
    quote_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("quote_items.id"), nullable=False, index=True
    )
    distributor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("distributors.id"), nullable=False, index=True
    )
    distribution_base_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("distribution_bases.id"), nullable=True
    )
    payment_term_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("payment_terms.id"), nullable=True
    )

    eligibility_status: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    eligibility_reasons: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    raw_price_per_liter: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    discount_per_liter: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    rebate_per_liter: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    freight_per_liter: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    other_cost_per_liter: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)

    delivered_cost_per_liter: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    delivered_total: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)

    financial_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    annual_effective_rate: Mapped[Decimal | None] = mapped_column(Numeric(12, 8), nullable=True)
    daily_rate: Mapped[Decimal | None] = mapped_column(Numeric(18, 12), nullable=True)

    financial_equivalent_cost_per_liter: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    financial_equivalent_total: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)

    ranking_cost_per_liter: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    rank_position: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    is_best_for_distributor: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_best_overall: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    difference_per_liter: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    difference_total: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)

    effective_valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    delivery_expected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    input_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    calculation_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    run: Mapped["QuoteComparisonRun"] = relationship("QuoteComparisonRun", back_populates="results")
