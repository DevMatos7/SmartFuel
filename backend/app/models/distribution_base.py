import uuid

from sqlalchemy import Boolean, CHAR, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class DistributionBase(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "distribution_bases"
    __table_args__ = (
        UniqueConstraint(
            "distributor_id", "state", "normalized_name",
            name="uq_distribution_bases_distributor_state_name",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    distributor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("distributors.id"), nullable=False, index=True
    )
    external_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    city: Mapped[str] = mapped_column(String(150), nullable=False)
    state: Mapped[str] = mapped_column(CHAR(2), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    distributor = relationship("Distributor", back_populates="bases")
