import datetime as dt

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import OrderStatus, PaymentMethod, PaymentStatus


class CheckoutRequest(BaseModel):
    payment_method: PaymentMethod
    recipient_name: str = Field(min_length=1, max_length=120)
    recipient_phone: str = Field(min_length=1, max_length=32)
    delivery_address: str = Field(min_length=5, max_length=2000)
    delivery_note: str | None = Field(default=None, max_length=2000)
    transaction_ref: str | None = Field(default=None, max_length=128)
    coupon_code: str | None = Field(default=None, max_length=32)


class OrderItemPublic(BaseModel):
    id: int
    product_id: int | None
    variant_id: int | None = None
    product_name: str
    variant_name: str | None = None
    image_url: str | None
    unit_price: float
    quantity: int
    total: float


class OrderStatusLogPublic(BaseModel):
    id: int
    from_status: str | None
    to_status: str
    note: str | None
    actor_id: int | None
    created_at: str | None


class OrderPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_number: str
    status: OrderStatus
    payment_method: PaymentMethod
    payment_status: PaymentStatus
    receipt_image: str | None = None
    transaction_ref: str | None = None
    paid_at: str | None = None
    subtotal: float
    delivery_fee: float
    discount: float
    total: float
    coupon_code: str | None = None
    recipient_name: str
    recipient_phone: str
    delivery_address: str
    delivery_note: str | None = None
    cancel_reason: str | None = None
    admin_note: str | None = None
    refund_amount: float | None = None
    refund_reason: str | None = None
    refunded_at: str | None = None
    created_at: dt.datetime
    updated_at: dt.datetime
    items: list[OrderItemPublic] = []
    status_logs: list[OrderStatusLogPublic] = []


class PaymentProofRequest(BaseModel):
    transaction_ref: str = Field(min_length=3, max_length=128)
    receipt_image: str | None = Field(default=None, max_length=512)


class OrderStatusUpdate(BaseModel):
    status: OrderStatus
    note: str | None = Field(default=None, max_length=2000)


class RefundRequest(BaseModel):
    amount: float = Field(gt=0)
    reason: str = Field(default="", max_length=2000)
