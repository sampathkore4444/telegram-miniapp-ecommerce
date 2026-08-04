from pydantic import BaseModel, ConfigDict, Field


class CartAdd(BaseModel):
    product_id: int
    variant_id: int | None = None
    quantity: int = Field(default=1, ge=1, le=99)


class CartUpdate(BaseModel):
    quantity: int = Field(ge=0, le=99)


class CartItemPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    quantity: int
    product: dict
    variant: dict | None = None
    unit_price: float

    @classmethod
    def from_item(cls, item, unit_price: float) -> "CartItemPublic":
        return cls(
            id=item.id,
            quantity=item.quantity,
            product=item.product.to_public_dict(),
            variant=item.variant.to_public_dict() if item.variant else None,
            unit_price=unit_price,
        )


class CartPublic(BaseModel):
    items: list[CartItemPublic]
    item_count: int
    subtotal: float
    currency_symbol: str = "$"
