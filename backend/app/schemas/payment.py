from pydantic import BaseModel, Field


class PayInitRequest(BaseModel):
    """Optional buyer-facing choices when initiating a payment."""


class PayResult(BaseModel):
    order_id: int
    gateway: str
    provider_ref: str
    payment_url: str | None = None
    amount: float
    currency: str
    status: str


class SimulateRequest(BaseModel):
    provider_ref: str = Field(min_length=1, max_length=128)
    approved: bool = True
