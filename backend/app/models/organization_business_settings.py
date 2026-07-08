import uuid
from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class OrganizationBusinessSettings(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "organization_business_settings"
    __table_args__ = (UniqueConstraint("organization_id", name="uq_org_business_settings_org"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True
    )
    default_supplier_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    default_minimum_volume_liters: Mapped[Decimal] = mapped_column(
        Numeric(16, 3), nullable=False, default=Decimal("5000.000")
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
