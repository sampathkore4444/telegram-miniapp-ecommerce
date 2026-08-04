import datetime as dt
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Enum, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IntPk, TimestampMixin
from app.models.enums import DiscountType


class DiscountCode(Base, TimestampMixin):
    __tablename__ = "discount_codes"

    id: Mapped[IntPk]
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    discount_type: Mapped[DiscountType] = mapped_column(
        Enum(DiscountType, native_enum=False, length=8),
        default=DiscountType.PERCENT,
        server_default=DiscountType.PERCENT.value,
    )
    value: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    min_subtotal: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0"), server_default="0"
    )
    max_uses: Mapped[int | None] = mapped_column(Integer)
    used_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    per_user_limit: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    active_from: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    active_until: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "code": self.code,
            "discount_type": self.discount_type.value,
            "value": float(self.value),
            "min_subtotal": float(self.min_subtotal),
            "max_uses": self.max_uses,
            "used_count": self.used_count,
            "per_user_limit": self.per_user_limit,
            "active_from": self.active_from.isoformat() if self.active_from else None,
            "active_until": self.active_until.isoformat() if self.active_until else None,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
