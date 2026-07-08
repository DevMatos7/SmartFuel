import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class ErpProduct(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "erp_products"
    __table_args__ = (UniqueConstraint("station_id", "erp_product_id", name="uq_erp_products_station_erp_id"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    station_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stations.id"), nullable=False, index=True
    )
    erp_product_id: Mapped[str] = mapped_column(String(100), nullable=False)
    erp_product_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    erp_description: Mapped[str] = mapped_column(String(255), nullable=False)
    erp_unit: Mapped[str | None] = mapped_column(String(30), nullable=True)
    erp_group_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    erp_group_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    erp_subgroup_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    erp_subgroup_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    canonical_product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id"), nullable=True, index=True
    )
    mapping_status: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDING", index=True)
    mapping_source: Mapped[str] = mapped_column(String(30), nullable=False, default="MANUAL")
    ignore_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    mapped_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    mapped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    history = relationship("ProductMappingHistory", back_populates="erp_product")


class ProductMappingHistory(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "product_mapping_history"

    erp_product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("erp_products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    previous_product_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=True)
    new_product_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=True)
    previous_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    new_status: Mapped[str] = mapped_column(String(30), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    changed_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    erp_product = relationship("ErpProduct", back_populates="history")
