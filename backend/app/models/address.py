from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IntPk, TimestampMixin, TgId


class UserAddress(Base, TimestampMixin):
    """A saved delivery address owned by a buyer."""

    __tablename__ = "user_addresses"

    id: Mapped[IntPk]
    user_id: Mapped[TgId] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    label: Mapped[str | None] = mapped_column(String(40))
    recipient_name: Mapped[str] = mapped_column(String(120))
    recipient_phone: Mapped[str] = mapped_column(String(32))
    address: Mapped[str] = mapped_column(Text)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    user: Mapped["User"] = relationship(back_populates="addresses")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "label": self.label,
            "recipient_name": self.recipient_name,
            "recipient_phone": self.recipient_phone,
            "address": self.address,
            "is_default": self.is_default,
        }
