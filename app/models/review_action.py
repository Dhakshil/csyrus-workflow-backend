import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base
from app.models.enums import ReviewActionType

if TYPE_CHECKING:
    from app.models.approval_request import ApprovalRequest
    from app.models.user import User


class ReviewAction(Base):
    """Records a single review decision (approve or reject).

    A request can have multiple review actions over its lifetime if we allow
    re-review (e.g. requester edits and resubmits). For this assessment,
    one action per request is the common case, but the schema supports more.
    """

    __tablename__ = "review_actions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("approval_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    action: Mapped[ReviewActionType] = mapped_column(nullable=False)
    comments: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    reviewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    request: Mapped["ApprovalRequest"] = relationship(
        "ApprovalRequest", back_populates="review_actions"
    )
    reviewer: Mapped["User"] = relationship("User", foreign_keys=[reviewed_by])

    def __repr__(self) -> str:
        return f"<ReviewAction id={self.id} action={self.action} by={self.reviewed_by}>"