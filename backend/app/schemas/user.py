from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import UserRole


class TelegramLoginRequest(BaseModel):
    init_data: str = Field(min_length=1)


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    telegram_id: int
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    photo_url: str | None = None
    phone: str | None = None
    address: str | None = None
    role: UserRole

    @property
    def display_name(self) -> str:  # pragma: no cover - frontend derives its own
        raise NotImplementedError


class AuthResponse(BaseModel):
    token: str
    token_type: str = "bearer"
    user: UserPublic


class UserUpdate(BaseModel):
    phone: str | None = Field(default=None, max_length=32)
    address: str | None = Field(default=None, max_length=1000)
    first_name: str | None = Field(default=None, max_length=64)
    last_name: str | None = Field(default=None, max_length=64)
