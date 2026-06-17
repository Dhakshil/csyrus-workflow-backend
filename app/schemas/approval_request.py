import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import Priority, RequestStatus
from app.schemas.review_action import ReviewActionRead
from app.schemas.user import UserBrief


class RequestCreate(BaseModel):
    """Payload for POST /requests."""
    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    priority: Priority = Priority.MEDIUM
    reviewer_id: uuid.UUID


class RequestUpdate(BaseModel):
    """Payload for PUT /requests/{id}. All fields optional (partial update)."""
    title: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, min_length=1)
    priority: Priority | None = None
    reviewer_id: uuid.UUID | None = None

    model_config = ConfigDict(extra="forbid")  # Reject unknown fields


class RequestRead(BaseModel):
    """Full request representation returned by GET endpoints."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    description: str
    priority: Priority
    status: RequestStatus
    created_by: uuid.UUID
    reviewer_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    creator: UserBrief
    reviewer: UserBrief
    review_actions: list[ReviewActionRead] = []


class RequestList(BaseModel):
    """Paginated list response."""
    items: list[RequestRead]
    total: int