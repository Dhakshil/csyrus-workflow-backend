from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.session import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """Generic CRUD operations for a SQLAlchemy model.

    Subclasses set `model` and inherit create/get/list/delete for free.
    Override or extend with entity-specific queries as needed.
    """

    model: type[ModelT]

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, id_: object) -> ModelT | None:
        return self.db.get(self.model, id_)

    def list(self, skip: int = 0, limit: int = 100) -> list[ModelT]:
        stmt = select(self.model).offset(skip).limit(limit)
        return list(self.db.scalars(stmt).all())

    def create(self, obj: ModelT) -> ModelT:
        self.db.add(obj)
        self.db.flush()  # Push to DB without committing (lets caller control txn)
        self.db.refresh(obj)
        return obj

    def delete(self, obj: ModelT) -> None:
        self.db.delete(obj)
        self.db.flush()

    def commit(self) -> None:
        self.db.commit()