import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class Quote(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "quotes"
    __table_args__ = (
        UniqueConstraint("organization_id", "quote_number", name="uq_quotes_org_number"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    station_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stations.id"), nullable=False, index=True
    )
    distributor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("distributors.id"), nullable=False, index=True
    )
    distribution_base_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("distribution_bases.id"), nullable=True
    )

    quote_number: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    quoted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    source_channel: Mapped[str] = mapped_column(String(30), nullable=False)
    entry_method: Mapped[str] = mapped_column(String(30), nullable=False, default="MANUAL")
    origin: Mapped[str] = mapped_column(String(40), nullable=False, default="MANUAL_OPERATIONAL", index=True)
    analytics_eligible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)

    seller_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    seller_contact: Mapped[str | None] = mapped_column(String(150), nullable=True)
    external_reference: Mapped[str | None] = mapped_column(String(150), nullable=True)
    source_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(String(30), nullable=False, default="DRAFT", index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    replaces_quote_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("quotes.id"), nullable=True, index=True
    )
    duplicated_from_quote_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("quotes.id"), nullable=True
    )

    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    activated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    cancellation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    superseded_by_quote_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("quotes.id"), nullable=True
    )

    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    items: Mapped[list["QuoteItem"]] = relationship(
        "QuoteItem", back_populates="quote", cascade="all, delete-orphan", order_by="QuoteItem.sequence"
    )
    evidences: Mapped[list["QuoteEvidence"]] = relationship(
        "QuoteEvidence", back_populates="quote", cascade="all, delete-orphan"
    )
