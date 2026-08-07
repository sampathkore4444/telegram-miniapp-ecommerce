from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IntPk, TimestampMixin


class Store(Base, TimestampMixin):
    """A merchant-owned store. The merchant (owner User) may own several on Pro."""

    __tablename__ = "stores"

    id: Mapped[IntPk]
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    name: Mapped[str] = mapped_column(String(120))
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    owner: Mapped["User"] = relationship(foreign_keys=[owner_id], lazy="joined")
    settings: Mapped["StoreSettings | None"] = relationship(
        back_populates="store", uselist=False, lazy="joined"
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
