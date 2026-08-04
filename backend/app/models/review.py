from sqlalchemy import Boolean, ForeignKey, Integer, JSON, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IntPk, TimestampMixin


class ProductReview(Base, TimestampMixin):
    __tablename__ = "product_reviews"
    __table_args__ = (
        UniqueConstraint("user_id", "product_id", name="uq_review_user_product"),
    )

    id: Mapped[IntPk]
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    rating: Mapped[int] = mapped_column(Integer)
    comment: Mapped[str | None] = mapped_column(Text)
    images: Mapped[list[str]] = mapped_column(JSON, default=list)
    is_approved: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    user: Mapped["User"] = relationship(back_populates="reviews", lazy="joined")
    product: Mapped["Product"] = relationship(back_populates="reviews")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "product_id": self.product_id,
            "rating": self.rating,
            "comment": self.comment,
            "images": self.images or [],
            "is_approved": self.is_approved,
            "user_id": self.user_id,
            "user_name": self.user.display_name if self.user else "Anonymous",
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
