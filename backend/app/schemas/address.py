from pydantic import BaseModel, Field


class AddressCreate(BaseModel):
    label: str | None = Field(default=None, max_length=40)
    recipient_name: str = Field(min_length=1, max_length=120)
    recipient_phone: str = Field(min_length=1, max_length=32)
    address: str = Field(min_length=5, max_length=2000)
    is_default: bool = False


class AddressUpdate(BaseModel):
    label: str | None = Field(default=None, max_length=40)
    recipient_name: str | None = Field(default=None, min_length=1, max_length=120)
    recipient_phone: str | None = Field(default=None, min_length=1, max_length=32)
    address: str | None = Field(default=None, min_length=5, max_length=2000)
    is_default: bool | None = None


class AddressPublic(BaseModel):
    id: int
    label: str | None = None
    recipient_name: str
    recipient_phone: str
    address: str
    is_default: bool
