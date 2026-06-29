from pydantic import BaseModel, Field
from datetime import datetime
from app.models.user import UserRole


class UserRead(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    username: str
    role: UserRole
    is_active: bool
    created_at: datetime


class UserCreate(BaseModel):
    username: str
    password: str = Field(..., min_length=8)
    role: UserRole = UserRole.user


class UserUpdate(BaseModel):
    role: UserRole | None = None
    is_active: bool | None = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)


class MeResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    username: str
    role: UserRole
