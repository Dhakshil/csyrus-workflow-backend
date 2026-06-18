import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.approval_request import ApprovalRequest
from app.models.enums import RequestStatus
from app.repositories.base import BaseRepository


class ApprovalRequestRepository(BaseRepository[ApprovalRequest]):
    model = ApprovalRequest

    def __init__(self, db: Session) -> None:
        super().__init__(db)

    def _with_relationships(self, stmt):
        """Eager-load creator, reviewer, and review_actions to avoid N+1 queries."""
        return stmt.options(
            selectinload(ApprovalRequest.creator),
            selectinload(ApprovalRequest.reviewer),
            selectinload(ApprovalRequest.review_actions).selectinload(
                ApprovalRequest.review_actions.property.mapper.class_.reviewer
            ),
        )

    def get_by_id(self, id_: uuid.UUID) -> ApprovalRequest | None:
        stmt = self._with_relationships(
            select(ApprovalRequest).where(ApprovalRequest.id == id_)
        )
        return self.db.scalars(stmt).first()

    def list_by_creator(
        self, creator_id: uuid.UUID, skip: int = 0, limit: int = 50
    ) -> list[ApprovalRequest]:
        stmt = self._with_relationships(
            select(ApprovalRequest)
            .where(ApprovalRequest.created_by == creator_id)
            .order_by(ApprovalRequest.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def list_by_reviewer(
        self,
        reviewer_id: uuid.UUID,
        status: RequestStatus | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[ApprovalRequest]:
        stmt = self._with_relationships(
            select(ApprovalRequest)
            .where(ApprovalRequest.reviewer_id == reviewer_id)
            .order_by(ApprovalRequest.created_at.desc())
        )
        if status:
            stmt = stmt.where(ApprovalRequest.status == status)
        stmt = stmt.offset(skip).limit(limit)
        return list(self.db.scalars(stmt).all())

    def count_by_creator(self, creator_id: uuid.UUID) -> int:
        stmt = select(func.count()).select_from(ApprovalRequest).where(
            ApprovalRequest.created_by == creator_id
        )
        return int(self.db.scalar(stmt) or 0)

    def count_by_reviewer(
        self, reviewer_id: uuid.UUID, status: RequestStatus | None = None
    ) -> int:
        stmt = select(func.count()).select_from(ApprovalRequest).where(
            ApprovalRequest.reviewer_id == reviewer_id
        )
        if status:
            stmt = stmt.where(ApprovalRequest.status == status)
        return int(self.db.scalar(stmt) or 0)