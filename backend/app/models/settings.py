from sqlalchemy import Boolean, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IntPk, TimestampMixin


class StoreSettings(Base, TimestampMixin):
    """Singleton (id always 1) holding store-wide configuration."""

    __tablename__ = "store_settings"

    id: Mapped[IntPk]

    store_name: Mapped[str] = mapped_column(String(120), default="My Telegram Shop")
    store_description: Mapped[str | None] = mapped_column(Text)
    welcome_message: Mapped[str | None] = mapped_column(Text)
    currency_code: Mapped[str] = mapped_column(String(8), default="USD")
    currency_symbol: Mapped[str] = mapped_column(String(8), default="$")

    # Contact
    contact_phone: Mapped[str | None] = mapped_column(String(32))
    contact_email: Mapped[str | None] = mapped_column(String(120))
    store_address: Mapped[str | None] = mapped_column(Text)

    # Delivery
    delivery_fee: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    free_delivery_threshold: Mapped[float | None] = mapped_column(Numeric(12, 2))

    # Payment toggles
    bank_qr_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    cod_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    online_payments_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true"
    )

    # Alerts
    low_stock_threshold: Mapped[int] = mapped_column(Integer, default=5, server_default="5")

    # Bank details for QR payments
    bank_name: Mapped[str | None] = mapped_column(String(120))
    bank_account_name: Mapped[str | None] = mapped_column(String(120))
    bank_account_number: Mapped[str | None] = mapped_column(String(64))
    bank_qr_image: Mapped[str | None] = mapped_column(String(512))
    payment_instructions: Mapped[str | None] = mapped_column(Text)

    def to_dict(self) -> dict:
        return {
            "store_name": self.store_name,
            "store_description": self.store_description,
            "welcome_message": self.welcome_message,
            "currency_code": self.currency_code,
            "currency_symbol": self.currency_symbol,
            "contact_phone": self.contact_phone,
            "contact_email": self.contact_email,
            "store_address": self.store_address,
            "delivery_fee": float(self.delivery_fee or 0),
            "free_delivery_threshold": (
                float(self.free_delivery_threshold) if self.free_delivery_threshold is not None else None
            ),
            "bank_qr_enabled": self.bank_qr_enabled,
            "cod_enabled": self.cod_enabled,
            "online_payments_enabled": self.online_payments_enabled,
            "low_stock_threshold": self.low_stock_threshold,
            "bank_name": self.bank_name,
            "bank_account_name": self.bank_account_name,
            "bank_account_number": self.bank_account_number,
            "bank_qr_image": self.bank_qr_image,
            "payment_instructions": self.payment_instructions,
        }
