import datetime as dt

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import DiscountType


class DiscountCodeCreate(BaseModel):
    code: str = Field(min_length=2, max_length=32, pattern=r"^[A-Za-z0-9_-]+$")
    discount_type: DiscountType = DiscountType.PERCENT
    value: float = Field(gt=0)
    min_subtotal: float = Field(default=0, ge=0)
    max_uses: int | None = Field(default=None, ge=0)
    per_user_limit: int = Field(default=1, ge=1)
    active_from: dt.datetime | None = None
    active_until: dt.datetime | None = None
    is_active: bool = True

    @model_validator(mode="after")
    def _check_value(self):
        if self.discount_type == DiscountType.PERCENT and self.value > 100:
            raise ValueError("Percent discount cannot exceed 100")
        if self.active_from and self.active_until and self.active_until < self.active_from:
            raise ValueError("active_until must be after active_from")
        return self


class DiscountCodeUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=2, max_length=32, pattern=r"^[A-Za-z0-9_-]+$")
    discount_type: DiscountType | None = None
    value: float | None = Field(default=None, gt=0)
    min_subtotal: float | None = Field(default=None, ge=0)
    max_uses: int | None = Field(default=None, ge=0)
    per_user_limit: int | None = Field(default=None, ge=1)
    active_from: dt.datetime | None = None
    active_until: dt.datetime | None = None
    is_active: bool | None = None


class DiscountCodePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    discount_type: DiscountType
    value: float
    min_subtotal: float
    max_uses: int | None = None
    used_count: int
    per_user_limit: int
    active_from: dt.datetime | None = None
    active_until: dt.datetime | None = None
    is_active: bool


class DiscountCheckResponse(BaseModel):
    code: str
    discount_type: DiscountType
    value: float
    discount_amount: float
    min_subtotal: float
    message: str
