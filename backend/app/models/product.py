import datetime as dt

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, JSON, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IntPk, TimestampMixin
from app.models.enums import CatalogStatus


class Product(Base, TimestampMixin):
    __tablename__ = "products"

    id: Mapped[IntPk]
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), index=True
    )
    name: Mapped[str] = mapped_column(String(160), index=True)
    slug: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    price: Mapped[float] = mapped_column(Numeric(12, 2))
    compare_at_price: Mapped[float | None] = mapped_column(Numeric(12, 2))
    sku: Mapped[str | None] = mapped_column(String(64))
    stock: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    images: Mapped[list[str]] = mapped_column(JSON, default=list)
    status: Mapped[CatalogStatus] = mapped_column(
        Enum(CatalogStatus, native_enum=False, length=16),
        default=CatalogStatus.ACTIVE,
        server_default=CatalogStatus.ACTIVE.value,
        index=True,
    )
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    sold_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    published_at: Mapped[dt.datetime | None] = mapped_column(default=None)
    # Quantity-discount tiers: [{"min_quantity": 3, "price": 90.0}, ...]
    price_tiers: Mapped[list[dict]] = mapped_column(JSON, default=list)

    category: Mapped["Category | None"] = relationship(back_populates="products", lazy="joined")
    reviews: Mapped[list["ProductReview"]] = relationship(back_populates="product")
    variants: Mapped[list["ProductVariant"]] = relationship(
        back_populates="product", cascade="all, delete-orphan", lazy="selectin"
    )

    @property
    def in_stock(self) -> bool:
        return self.stock > 0

    @property
    def active_variants(self) -> list["ProductVariant"]:
        return [v for v in self.variants if v.is_active]

    def _tiers(self) -> list[dict]:
        tiers = sorted((self.price_tiers or []), key=lambda t: int(t.get("min_quantity", 0)))
        return [{"min_quantity": int(t["min_quantity"]), "price": float(t["price"])} for t in tiers]

    def to_public_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "description": self.description,
            "price": float(self.price),
            "compare_at_price": (
                float(self.compare_at_price) if self.compare_at_price is not None else None
            ),
            "sku": self.sku,
            "stock": self.stock,
            "images": self.images or [],
            "is_featured": self.is_featured,
            "sold_count": self.sold_count,
            "category_id": self.category_id,
            "category": self.category.name if self.category else None,
            "in_stock": self.in_stock,
            "price_tiers": self._tiers(),
            "variants": [v.to_public_dict() for v in self.active_variants],
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
