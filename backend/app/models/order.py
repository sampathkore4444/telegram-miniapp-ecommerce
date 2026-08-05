import uuid
from decimal import Decimal

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IntPk, TimestampMixin, TgId
from app.models.enums import OrderStatus, PaymentMethod, PaymentStatus


def gen_order_number() -> str:
    return "ORD-" + uuid.uuid4().hex[:8].upper()


class Order(Base, TimestampMixin):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_number: Mapped[str] = mapped_column(String(20), unique=True, index=True, default=gen_order_number)
    user_id: Mapped[TgId] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    coupon_id: Mapped[int | None] = mapped_column(
        ForeignKey("discount_codes.id", ondelete="SET NULL")
    )
    coupon_code: Mapped[str | None] = mapped_column(String(32))

    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, native_enum=False, length=32),
        default=OrderStatus.PENDING,
        server_default=OrderStatus.PENDING.value,
        index=True,
    )

    # Money
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    delivery_fee: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    discount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))

    # Payment
    payment_method: Mapped[PaymentMethod] = mapped_column(
        Enum(PaymentMethod, native_enum=False, length=16), index=True
    )
    payment_status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, native_enum=False, length=16),
        default=PaymentStatus.UNPAID,
        server_default=PaymentStatus.UNPAID.value,
        index=True,
    )
    receipt_image: Mapped[str | None] = mapped_column(String(512))
    transaction_ref: Mapped[str | None] = mapped_column(String(128))
    paid_at: Mapped[object | None] = mapped_column(DateTime(timezone=True))

    # Delivery
    recipient_name: Mapped[str] = mapped_column(String(120))
    recipient_phone: Mapped[str] = mapped_column(String(32))
    delivery_address: Mapped[str] = mapped_column(Text)
    delivery_note: Mapped[str | None] = mapped_column(Text)

    cancel_reason: Mapped[str | None] = mapped_column(Text)
    admin_note: Mapped[str | None] = mapped_column(Text)

    # Tracking / courier
    tracking_number: Mapped[str | None] = mapped_column(String(128))
    tracking_carrier: Mapped[str | None] = mapped_column(String(64))

    # Refunds
    refund_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    refund_reason: Mapped[str | None] = mapped_column(Text)
    refunded_at: Mapped[object | None] = mapped_column(DateTime(timezone=True))

    user: Mapped["User"] = relationship(back_populates="orders")
    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan", lazy="selectin"
    )
    status_logs: Mapped[list["OrderStatusLog"]] = relationship(
        back_populates="order", cascade="all, delete-orphan", lazy="selectin"
    )
    payment_transactions: Mapped[list["PaymentTransaction"]] = relationship(
        back_populates="order", cascade="all, delete-orphan", lazy="selectin"
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[IntPk]
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id", ondelete="SET NULL"))
    variant_id: Mapped[int | None] = mapped_column(
        ForeignKey("product_variants.id", ondelete="SET NULL")
    )
    product_name: Mapped[str] = mapped_column(String(160))
    variant_name: Mapped[str | None] = mapped_column(String(160))
    image_url: Mapped[str | None] = mapped_column(String(512))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    quantity: Mapped[int] = mapped_column(Integer)
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2))

    order: Mapped[Order] = relationship(back_populates="items")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "product_id": self.product_id,
            "variant_id": self.variant_id,
            "product_name": self.product_name,
            "variant_name": self.variant_name,
            "image_url": self.image_url,
            "unit_price": float(self.unit_price),
            "quantity": self.quantity,
            "total": float(self.total),
        }


class OrderStatusLog(Base):
    __tablename__ = "order_status_logs"

    id: Mapped[IntPk]
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    from_status: Mapped[str | None] = mapped_column(String(32))
    to_status: Mapped[str] = mapped_column(String(32))
    note: Mapped[str | None] = mapped_column(Text)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())

    order: Mapped[Order] = relationship(back_populates="status_logs")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "from_status": self.from_status,
            "to_status": self.to_status,
            "note": self.note,
            "actor_id": self.actor_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
