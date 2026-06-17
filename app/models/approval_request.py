import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base
from app.models.enums import Priority, RequestStatus
from app.models.user import User


class ApprovalRequest(Base):
    """An approval request submitted by a Requester.

    Lifecycle:
        PENDING  → APPROVED   (reviewer approves)
        PENDING  → REJECTED   (reviewer rejects)

    Once a decision is made, the status is final. A new ReviewAction row is
    created recording who decided what, when, and any comments.
    """

    __tablename__ = "approval_requests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[Priority] = mapped_column(nullable=False, default=Priority.MEDIUM)
    status: Mapped[RequestStatus] = mapped_column(
        nullable=False, default=RequestStatus.PENDING
    )

    # Foreign keys
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reviewer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships (lazy='select' is the default; explicit for clarity)
    creator: Mapped["User"] = relationship(
        "User", foreign_keys=[created_by], backref="created_requests"
    )
    reviewer: Mapped["User"] = relationship(
        "User", foreign_keys=[reviewer_id], backref="assigned_requests"
    )
    review_actions: Mapped[list["ReviewAction"]] = relationship(
        "ReviewAction",
        back_populates="request",
        cascade="all, delete-orphan",
        order_by="ReviewAction.reviewed_at.desc()",
    )

    def __repr__(self) -> str:
        return f"<ApprovalRequest id={self.id} title={self.title!r} status={self.status}>"