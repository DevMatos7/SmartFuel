"""Models Sprint 10 — correlação, defasagem e repasse."""

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


class MarketAnalysisParameter(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "market_analysis_parameters"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "valid_from",
            name="uq_market_analysis_parameters_org_valid_from",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    minimum_sample_size: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    maximum_missing_percentage: Mapped[Decimal] = mapped_column(
        Numeric(8, 4), nullable=False, default=Decimal("30.0000")
    )
    maximum_carry_forward_age: Mapped[int] = mapped_column(Integer, nullable=False, default=7)
    minimum_lag: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    maximum_lag: Mapped[int] = mapped_column(Integer, nullable=False, default=14)
    lag_unit: Mapped[str] = mapped_column(String(20), nullable=False, default="DAYS")
    minimum_reference_change: Mapped[Decimal] = mapped_column(
        Numeric(20, 10), nullable=False, default=Decimal("0.0001000000")
    )
    default_frequency: Mapped[str] = mapped_column(String(20), nullable=False, default="DAILY")
    default_transformation: Mapped[str] = mapped_column(
        String(40), nullable=False, default="PERCENTAGE_CHANGE"
    )
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )


class MarketAnalysisRun(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "market_analysis_runs"

    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    analysis_type: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, index=True)

    external_series_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("external_series.id"), nullable=True, index=True
    )
    external_series_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    internal_series_type: Mapped[str] = mapped_column(String(80), nullable=False)

    station_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stations.id"), nullable=True, index=True
    )
    canonical_product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id"), nullable=True, index=True
    )
    distributor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("distributors.id"), nullable=True, index=True
    )

    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    frequency: Mapped[str] = mapped_column(String(20), nullable=False)
    transformation: Mapped[str] = mapped_column(String(40), nullable=False)
    alignment_policy: Mapped[str] = mapped_column(String(60), nullable=False)

    lag_min: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    lag_max: Mapped[int] = mapped_column(Integer, nullable=False, default=14)
    selected_lag: Mapped[int | None] = mapped_column(Integer, nullable=True)

    input_snapshot: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    output_snapshot: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    snapshot_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    sample_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    aligned_pair_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    warning_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    interpretive_disclaimer: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default=(
            "Resultados exploratórios de associação observada. "
            "Correlação e defasagem não constituem prova de causalidade."
        ),
    )

    trigger_type: Mapped[str] = mapped_column(String(30), nullable=False, default="MANUAL")
    requested_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    reprocess_of_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("market_analysis_runs.id"), nullable=True
    )
    reprocess_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class MarketAnalysisResult(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "market_analysis_results"

    analysis_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("market_analysis_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    metric_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    coefficient: Mapped[Decimal | None] = mapped_column(Numeric(20, 10), nullable=True)
    p_value: Mapped[Decimal | None] = mapped_column(Numeric(20, 10), nullable=True)
    lag_value: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sample_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    coverage_percentage: Mapped[Decimal | None] = mapped_column(Numeric(12, 8), nullable=True)
    pass_through_ratio: Mapped[Decimal | None] = mapped_column(Numeric(20, 10), nullable=True)
    pass_through_elasticity: Mapped[Decimal | None] = mapped_column(Numeric(20, 10), nullable=True)
    quality_status: Mapped[str] = mapped_column(String(40), nullable=False)
    warnings: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class MarketAlignedObservation(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "market_aligned_observations"

    analysis_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("market_analysis_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    period_datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    external_observation_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    external_value: Mapped[Decimal] = mapped_column(Numeric(28, 10), nullable=False)
    external_change: Mapped[Decimal | None] = mapped_column(Numeric(28, 10), nullable=True)
    internal_entity_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    internal_entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    internal_value: Mapped[Decimal] = mapped_column(Numeric(28, 10), nullable=False)
    internal_change: Mapped[Decimal | None] = mapped_column(Numeric(28, 10), nullable=True)
    lag_applied: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    carry_forward: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    carry_forward_age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    included: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    exclusion_reason: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class MarketPassThroughEvent(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "market_pass_through_events"

    analysis_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("market_analysis_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    event_direction: Mapped[str] = mapped_column(String(20), nullable=False)
    reference_event_datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    target_event_datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    lag_value: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reference_change: Mapped[Decimal] = mapped_column(Numeric(28, 10), nullable=False)
    target_change: Mapped[Decimal] = mapped_column(Numeric(28, 10), nullable=False)
    pass_through_ratio: Mapped[Decimal | None] = mapped_column(Numeric(20, 10), nullable=True)
    pass_through_elasticity: Mapped[Decimal | None] = mapped_column(Numeric(20, 10), nullable=True)
    quality_status: Mapped[str] = mapped_column(String(40), nullable=False)
    details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class InternalMarketSeriesPoint(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "internal_market_series_points"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "series_type",
            "observation_datetime",
            "station_id",
            "canonical_product_id",
            "distributor_id",
            name="uq_internal_market_series_point_natural",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    series_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    station_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stations.id"), nullable=True, index=True
    )
    canonical_product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id"), nullable=True, index=True
    )
    distributor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("distributors.id"), nullable=True, index=True
    )
    observation_datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    value: Mapped[Decimal] = mapped_column(Numeric(28, 10), nullable=False)
    unit: Mapped[str] = mapped_column(String(40), nullable=False)
    volume_weight: Mapped[Decimal | None] = mapped_column(Numeric(22, 6), nullable=True)
    source_entity_type: Mapped[str] = mapped_column(String(80), nullable=False)
    source_entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    source_record_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
