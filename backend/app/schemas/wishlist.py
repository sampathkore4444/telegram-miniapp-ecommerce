from pydantic import BaseModel, ConfigDict


class WishlistItemPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    created_at: object | None = None
    product: dict | None = None


class WishlistAdd(BaseModel):
    product_id: int
