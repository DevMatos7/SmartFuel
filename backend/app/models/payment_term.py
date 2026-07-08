import uuid

from sqlalchemy import Boolean, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class PaymentTerm(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "payment_terms"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "payment_type", "days", "normalized_name",
            name="uq_payment_terms_org_type_days_name",
        ),
        UniqueConstraint("organization_id", "code", name="uq_payment_terms_org_code"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(60), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(120), nullable=False)
    payment_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    days: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
