import uuid

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.core.database import Base


class Station(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "stations"
    __table_args__ = (
        UniqueConstraint("organization_id", "erp_branch_id", name="uq_stations_org_erp_branch"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True
    )
    station_type: Mapped[str] = mapped_column(String(20), nullable=False)
    erp_branch_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    corporate_name: Mapped[str] = mapped_column(String(200), nullable=False)
    trade_name: Mapped[str] = mapped_column(String(200), nullable=False)
    cnpj: Mapped[str] = mapped_column(String(14), unique=True, nullable=False)
    anp_code: Mapped[str | None] = mapped_column(String(30), unique=True, nullable=True)
    brand_type: Mapped[str] = mapped_column(String(20), nullable=False)
    brand_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    timezone: Mapped[str] = mapped_column(String(80), nullable=False, default="America/Cuiaba")
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    organization = relationship("Organization", back_populates="stations")
    user_links = relationship("UserStation", back_populates="station")
