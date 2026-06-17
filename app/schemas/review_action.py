import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ReviewActionType
from app.schemas.user import UserBrief


class ReviewDecision(BaseModel):
    """Payload for POST /reviewer/requests/{id}/approve and /reject."""
    comments: str = Field(..., min_length=1, max_length=5000)


class ReviewActionRead(BaseModel):
    """Returned embedded inside RequestRead."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    request_id: uuid.UUID
    action: ReviewActionType
    comments: str | None
    reviewed_by: uuid.UUID
    reviewed_at: datetime
    reviewer: UserBrief