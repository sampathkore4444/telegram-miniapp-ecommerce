from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

from app.models.enums import OrderStatus


class SettingsUpdate(BaseModel):
    store_name: str | None = Field(default=None, min_length=1, max_length=120)
    store_description: str | None = Field(default=None, max_length=5000)
    welcome_message: str | None = Field(default=None, max_length=5000)
    currency_code: str | None = Field(default=None, max_length=8)
    currency_symbol: str | None = Field(default=None, max_length=8)
    contact_phone: str | None = Field(default=None, max_length=32)
    contact_email: str | None = Field(default=None, max_length=120)
    store_address: str | None = Field(default=None, max_length=2000)
    delivery_fee: float | None = Field(default=None, ge=0)
    free_delivery_threshold: float | None = Field(default=None, ge=0)
    bank_qr_enabled: bool | None = None
    cod_enabled: bool | None = None
    online_payments_enabled: bool | None = None
    low_stock_threshold: int | None = Field(default=None, ge=0, le=1000)
    bank_name: str | None = Field(default=None, max_length=120)
    bank_account_name: str | None = Field(default=None, max_length=120)
    bank_account_number: str | None = Field(default=None, max_length=64)
    bank_qr_image: str | None = None
    payment_instructions: str | None = Field(default=None, max_length=5000)


class DashboardStats(BaseModel):
    total_revenue: Decimal
    total_orders: int
    pending_orders: int
    products_count: int
    low_stock_count: int
    customers_count: int
    today_revenue: Decimal
    today_orders: int
    recent_orders: list[dict]
    top_products: list[dict]
    sales_last_14_days: list[dict]
    orders_by_status: dict[str, int]
    avg_order_value: Decimal
    repeat_customer_rate: float
    revenue_by_category: list[dict]
    coupon_redemptions: list[dict]
    total_discount_given: Decimal
