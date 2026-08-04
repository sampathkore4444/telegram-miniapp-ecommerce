from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import CatalogStatus


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    slug: str | None = Field(default=None, max_length=100, pattern=r"^[a-z0-9-]+$")
    description: str | None = Field(default=None, max_length=2000)
    image_url: str | None = None
    sort_order: int = 0
    is_active: bool = True


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    slug: str | None = Field(default=None, max_length=100, pattern=r"^[a-z0-9-]+$")
    description: str | None = Field(default=None, max_length=2000)
    image_url: str | None = None
    sort_order: int | None = None
    is_active: bool | None = None


class CategoryPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    description: str | None = None
    image_url: str | None = None
    sort_order: int
    is_active: bool
    product_count: int = 0


class ProductVariantInput(BaseModel):
    id: int | None = None
    name: str = Field(min_length=1, max_length=160)
    options: dict = Field(default_factory=dict)
    price: float | None = Field(default=None, ge=0)
    compare_at_price: float | None = Field(default=None, ge=0)
    sku: str | None = Field(default=None, max_length=64)
    stock: int = Field(default=0, ge=0)
    is_active: bool = True


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    slug: str | None = Field(default=None, max_length=180, pattern=r"^[a-z0-9-]+$")
    description: str | None = Field(default=None, max_length=10000)
    price: float = Field(gt=0)
    compare_at_price: float | None = Field(default=None, ge=0)
    category_id: int | None = None
    sku: str | None = Field(default=None, max_length=64)
    stock: int = Field(default=0, ge=0)
    images: list[str] = Field(default_factory=list)
    status: CatalogStatus = CatalogStatus.ACTIVE
    is_featured: bool = False
    price_tiers: list[dict] = Field(default_factory=list)
    variants: list[ProductVariantInput] = Field(default_factory=list)


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    slug: str | None = Field(default=None, max_length=180, pattern=r"^[a-z0-9-]+$")
    description: str | None = Field(default=None, max_length=10000)
    price: float | None = Field(default=None, gt=0)
    compare_at_price: float | None = Field(default=None, ge=0)
    category_id: int | None = None
    sku: str | None = Field(default=None, max_length=64)
    stock: int | None = Field(default=None, ge=0)
    images: list[str] | None = None
    status: CatalogStatus | None = None
    is_featured: bool | None = None
    price_tiers: list[dict] | None = None
    variants: list[ProductVariantInput] | None = None
