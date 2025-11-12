from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    username: str = Field(..., max_length=50)
    password: str = Field(..., min_length=8, max_length=128)
    name: str | None = Field(default=None, max_length=100)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=30)
    status: str = Field(default="ACTIVE", pattern=r"^[A-Z_]+$")


class UserRead(BaseModel):
    id: int
    username: str
    status: str

    model_config = {"from_attributes": True}
