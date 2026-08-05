from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IntPk, TimestampMixin


class PaymentTransaction(Base, TimestampMixin):
    """One online-payment attempt for an order through a gateway."""

    __tablename__ = "payment_transactions"

    id: Mapped[IntPk]
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), index=True
    )
    gateway: Mapped[str] = mapped_column(String(32), default="sandbox")
    provider_ref: Mapped[str] = mapped_column(String(128), index=True)
    status: Mapped[str] = mapped_column(
        String(16), default="pending", index=True
    )  # pending / succeeded / failed
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    currency: Mapped[str] = mapped_column(String(8), default="USD")
    message: Mapped[str | None] = mapped_column(Text)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    order: Mapped["Order"] = relationship(back_populates="payment_transactions")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "order_id": self.order_id,
            "gateway": self.gateway,
            "provider_ref": self.provider_ref,
            "status": self.status,
            "amount": float(self.amount),
            "currency": self.currency,
            "message": self.message,
            "paid_at": self.paid_at.isoformat() if self.paid_at else None,
        }
