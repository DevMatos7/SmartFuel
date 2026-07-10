import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class Distributor(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "distributors"
    __table_args__ = (
        UniqueConstraint("organization_id", "cnpj", name="uq_distributors_org_cnpj"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    internal_code: Mapped[str] = mapped_column(String(60), nullable=False)
    corporate_name: Mapped[str] = mapped_column(String(200), nullable=False)
    trade_name: Mapped[str] = mapped_column(String(200), nullable=False)
    cnpj: Mapped[str | None] = mapped_column(String(14), nullable=True)
    normalized_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    registration_status: Mapped[str] = mapped_column(String(30), nullable=False, default="INCOMPLETE")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    bases = relationship("DistributionBase", back_populates="distributor")


class ErpSupplier(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "erp_suppliers"
    __table_args__ = (UniqueConstraint("station_id", "erp_entity_id", name="uq_erp_suppliers_station_entity"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    station_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stations.id"), nullable=False, index=True
    )
    erp_entity_id: Mapped[str] = mapped_column(String(100), nullable=False)
    erp_entity_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    erp_name: Mapped[str] = mapped_column(String(255), nullable=False)
    erp_cnpj: Mapped[str | None] = mapped_column(String(14), nullable=True)
    distributor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("distributors.id"), nullable=True, index=True
    )
    mapping_status: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDING", index=True)
    mapping_source: Mapped[str | None] = mapped_column(String(30), nullable=True)
    ignore_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    mapped_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    mapped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    source_system: Mapped[str | None] = mapped_column(String(50), nullable=True)
    source_record_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_active: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    last_sync_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("erp_sync_runs.id"), nullable=True
    )
