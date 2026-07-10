import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class QuoteItem(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "quote_items"

    quote_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("quotes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id"), nullable=False, index=True
    )
    distribution_base_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("distribution_bases.id"), nullable=True
    )

    sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    quoted_price_per_liter: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)

    payment_term_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("payment_terms.id"), nullable=False, index=True
    )
    payment_type_snapshot: Mapped[str] = mapped_column(String(30), nullable=False)
    payment_term_days_snapshot: Mapped[int] = mapped_column(Integer, nullable=False)
    payment_term_name_snapshot: Mapped[str] = mapped_column(String(120), nullable=False)

    freight_type: Mapped[str] = mapped_column(String(20), nullable=False, default="CIF")
    freight_calculation_type: Mapped[str] = mapped_column(String(20), nullable=False, default="NONE")
    freight_value_total: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    freight_value_per_liter: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)

    discount_per_liter: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False, default=0)
    rebate_per_liter: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False, default=0)
    other_cost_per_liter: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False, default=0)
    other_cost_description: Mapped[str | None] = mapped_column(Text, nullable=True)

    minimum_volume_liters: Mapped[Decimal] = mapped_column(Numeric(16, 3), nullable=False)
    available_volume_liters: Mapped[Decimal | None] = mapped_column(Numeric(16, 3), nullable=True)

    delivery_expected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    quote: Mapped["Quote"] = relationship("Quote", back_populates="items")
