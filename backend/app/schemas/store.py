from pydantic import BaseModel, ConfigDict, Field


class StoreCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    slug: str | None = Field(default=None, max_length=120, pattern=r"^[a-z0-9-]+$")


class StoreUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    slug: str | None = Field(default=None, max_length=120, pattern=r"^[a-z0-9-]+$")
    is_active: bool | None = None


class StorePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    is_active: bool
    created_at: str | None = None
    plan: str = "starter"
    features: dict = Field(default_factory=dict)
    product_count: int = 0
