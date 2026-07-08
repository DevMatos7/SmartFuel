import uuid

from sqlalchemy import Boolean, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class Product(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "products"
    __table_args__ = (UniqueConstraint("organization_id", "code", name="uq_products_org_code"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(60), nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    fuel_family: Mapped[str] = mapped_column(String(40), nullable=False)
    commercial_variant: Mapped[str] = mapped_column(String(40), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False, default="LITER")
    regulatory_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    purchasable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sellable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    code_locked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
