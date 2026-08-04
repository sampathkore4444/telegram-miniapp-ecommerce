import datetime as dt

from pydantic import BaseModel, Field

from app.models.enums import UserRole


class CustomerPublic(BaseModel):
    id: int
    telegram_id: int
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    display_name: str
    role: UserRole
    is_active: bool
    phone: str | None = None
    orders_count: int = 0
    total_spent: float = 0.0
    last_order_at: str | None = None
    created_at: str | None = None


class CustomerUpdate(BaseModel):
    is_active: bool | None = None
    note: str | None = Field(default=None, max_length=2000)


class CustomerDetail(CustomerPublic):
    orders: list[dict] = Field(default_factory=list)
