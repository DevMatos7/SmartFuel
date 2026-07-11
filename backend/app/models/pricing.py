"""Models Sprint 11 — formação de preço, margem, aprovação e evidências."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
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


class PricingPolicy(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "pricing_policies"

    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    station_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stations.id"), nullable=True, index=True
    )
    canonical_product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id"), nullable=True, index=True
    )
    price_type: Mapped[str] = mapped_column(String(40), nullable=False, default="POSTED_PRICE")
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="ACTIVE")

    cost_basis_type: Mapped[str] = mapped_column(String(60), nullable=False)
    weighted_cost_window_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    minimum_purchase_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    minimum_purchase_volume: Mapped[Decimal | None] = mapped_column(Numeric(22, 6), nullable=True)

    minimum_margin_per_liter: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    minimum_margin_percentage: Mapped[Decimal | None] = mapped_column(Numeric(12, 8), nullable=True)
    minimum_markup_percentage: Mapped[Decimal | None] = mapped_column(Numeric(12, 8), nullable=True)

    target_margin_per_liter: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    target_margin_percentage: Mapped[Decimal | None] = mapped_column(Numeric(12, 8), nullable=True)
    target_markup_percentage: Mapped[Decimal | None] = mapped_column(Numeric(12, 8), nullable=True)

    maximum_increase_per_liter: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    maximum_decrease_per_liter: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    maximum_increase_percentage: Mapped[Decimal | None] = mapped_column(Numeric(12, 8), nullable=True)
    maximum_decrease_percentage: Mapped[Decimal | None] = mapped_column(Numeric(12, 8), nullable=True)
    minimum_change_per_liter: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)

    rounding_policy: Mapped[str] = mapped_column(String(40), nullable=False, default="NEAREST_CENT")
    rounding_increment: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)

    default_scenario: Mapped[str] = mapped_column(String(40), nullable=False, default="BALANCED")
    allow_low_confidence_cost: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    require_market_signal: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    require_evidence_on_approve: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    allow_self_approval: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    required_approvals: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    implementation_tolerance_per_liter: Mapped[Decimal] = mapped_column(
        Numeric(20, 8), nullable=False, default=Decimal("0.01000000")
    )

    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )


class PricingRecommendationRun(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "pricing_recommendation_runs"

    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    trigger_type: Mapped[str] = mapped_column(String(30), nullable=False, default="MANUAL")
    reference_datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    station_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stations.id"), nullable=True, index=True
    )
    canonical_product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id"), nullable=True, index=True
    )
    price_type: Mapped[str] = mapped_column(String(40), nullable=False, default="POSTED_PRICE")
    requested_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    reprocess_of_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pricing_recommendation_runs.id"), nullable=True
    )
    reprocess_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    item_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    recommendation_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    warning_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    input_snapshot: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    output_snapshot: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    snapshot_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    interpretive_disclaimer: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default=(
            "Margem bruta comercial estimada. Não é lucro líquido. "
            "Recomendação não altera preço no ERP/XPERT."
        ),
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PricingRecommendationItem(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "pricing_recommendation_items"

    recommendation_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pricing_recommendation_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    station_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stations.id"), nullable=False, index=True
    )
    canonical_product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id"), nullable=False, index=True
    )
    price_type: Mapped[str] = mapped_column(String(40), nullable=False)
    reference_datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    current_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    current_price_source: Mapped[str | None] = mapped_column(String(60), nullable=True)
    current_price_datetime: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    cost_basis_type: Mapped[str] = mapped_column(String(60), nullable=False)
    cost_per_liter: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    cost_datetime: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cost_confidence: Mapped[str] = mapped_column(String(20), nullable=False)

    current_margin_per_liter: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    current_margin_percentage: Mapped[Decimal | None] = mapped_column(Numeric(12, 8), nullable=True)
    current_markup_percentage: Mapped[Decimal | None] = mapped_column(Numeric(12, 8), nullable=True)

    commercial_floor_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    target_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)

    raw_recommended_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    recommended_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    recommended_change_per_liter: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    recommended_change_percentage: Mapped[Decimal | None] = mapped_column(Numeric(12, 8), nullable=True)

    recommendation_status: Mapped[str] = mapped_column(String(40), nullable=False)
    quality_status: Mapped[str] = mapped_column(String(40), nullable=False)
    guardrail_applied: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    rounding_policy: Mapped[str | None] = mapped_column(String(40), nullable=True)

    reasons: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    warnings: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    input_snapshot: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    result_snapshot: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PricingRecommendationScenario(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "pricing_recommendation_scenarios"

    recommendation_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pricing_recommendation_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scenario_type: Mapped[str] = mapped_column(String(40), nullable=False)
    cost_per_liter: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    margin_per_liter: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    margin_percentage: Mapped[Decimal | None] = mapped_column(Numeric(12, 8), nullable=True)
    markup_percentage: Mapped[Decimal | None] = mapped_column(Numeric(12, 8), nullable=True)
    calculated_price: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    rounded_price: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PricingDecision(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "pricing_decisions"

    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    recommendation_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pricing_recommendation_items.id"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    selected_scenario: Mapped[str | None] = mapped_column(String(40), nullable=True)
    recommended_price: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    approved_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    decision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PricingDecisionApproval(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "pricing_decision_approvals"

    pricing_decision_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pricing_decisions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    approval_level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDING")
    decision: Mapped[str | None] = mapped_column(String(30), nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    assigned_role: Mapped[str | None] = mapped_column(String(40), nullable=True)
    assigned_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    decided_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PricingDecisionEvidence(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "pricing_decision_evidence"

    pricing_decision_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pricing_decisions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    evidence_type: Mapped[str] = mapped_column(String(60), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    storage_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    structured_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PricingImplementationCheck(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "pricing_implementation_checks"

    pricing_decision_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pricing_decisions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    check_type: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    approved_price: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    implemented_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    implementation_variance: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    price_snapshot_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    implemented_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    evidence_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    checked_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
