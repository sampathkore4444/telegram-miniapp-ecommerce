from pydantic import BaseModel, ConfigDict, Field


class ReviewCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=3000)
    images: list[str] = Field(default_factory=list, max_length=6)


class ReviewPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    rating: int
    comment: str | None = None
    images: list[str] = []
    user_id: int
    user_name: str = "Anonymous"
    created_at: object | None = None


class ReviewModerate(BaseModel):
    is_approved: bool
