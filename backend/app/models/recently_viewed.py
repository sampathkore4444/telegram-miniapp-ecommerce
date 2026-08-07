from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IntPk, TgId


class RecentlyViewed(Base):
    """One row per (user, product); viewed_at bumped on each view."""

    __tablename__ = "recently_viewed"
    __table_args__ = (
        UniqueConstraint("user_id", "product_id", name="uq_recently_viewed_user_product"),
    )

    id: Mapped[IntPk]
    store_id: Mapped[int] = mapped_column(
        ForeignKey("stores.id", ondelete="RESTRICT"), index=True
    )
    user_id: Mapped[TgId] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    viewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    user: Mapped["User"] = relationship(back_populates="recently_viewed")
    product: Mapped["Product"] = relationship(back_populates="recently_viewed")
