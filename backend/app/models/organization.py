from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.core.database import Base


class Organization(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(150), nullable=False)
    corporate_name: Mapped[str] = mapped_column(String(200), nullable=False)
    cnpj: Mapped[str] = mapped_column(String(14), unique=True, nullable=False)
    timezone: Mapped[str] = mapped_column(String(80), nullable=False, default="America/Cuiaba")
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    stations = relationship("Station", back_populates="organization")
    users = relationship("User", back_populates="organization")
