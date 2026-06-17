import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.review_action import ReviewAction
from app.repositories.base import BaseRepository


class ReviewActionRepository(BaseRepository[ReviewAction]):
    model = ReviewAction

    def __init__(self, db: Session) -> None:
        super().__init__(db)

    def list_by_request(self, request_id: uuid.UUID) -> list[ReviewAction]:
        stmt = (
            select(ReviewAction)
            .where(ReviewAction.request_id == request_id)
            .options(selectinload(ReviewAction.reviewer))
            .order_by(ReviewAction.reviewed_at.desc())
        )
        return list(self.db.scalars(stmt).all())

    def get_by_id(self, id_: uuid.UUID) -> ReviewAction | None:
        stmt = (
            select(ReviewAction)
            .where(ReviewAction.id == id_)
            .options(selectinload(ReviewAction.reviewer))
        )
        return self.db.scalars(stmt).first()