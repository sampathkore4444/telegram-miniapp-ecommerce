from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Integer, JSON, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IntPk


class ProductVariant(Base):
    __tablename__ = "product_variants"

    id: Mapped[IntPk]
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(160))
    options: Mapped[dict] = mapped_column(JSON, default=dict)
    price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    compare_at_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    sku: Mapped[str | None] = mapped_column(String(64))
    stock: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    product: Mapped["Product"] = relationship(back_populates="variants")

    @property
    def in_stock(self) -> bool:
        return self.stock > 0

    def to_public_dict(self) -> dict:
        return {
            "id": self.id,
            "product_id": self.product_id,
            "name": self.name,
            "options": self.options or {},
            "price": float(self.price) if self.price is not None else None,
            "compare_at_price": (
                float(self.compare_at_price) if self.compare_at_price is not None else None
            ),
            "sku": self.sku,
            "stock": self.stock,
            "is_active": self.is_active,
            "in_stock": self.in_stock,
        }
