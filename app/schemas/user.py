import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.enums import UserRole


class UserBase(BaseModel):
    """Shared fields across user schemas."""
    name: str
    email: EmailStr
    role: UserRole


class UserRead(UserBase):
    """Schema returned by GET /auth/me and other endpoints exposing user info."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    google_id: str
    created_at: datetime


class UserBrief(BaseModel):
    """Minimal user info for embedding inside other schemas (e.g. request.creator)."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    email: EmailStr
    role: UserRole