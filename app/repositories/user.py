from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    def __init__(self, db: Session) -> None:
        super().__init__(db)

    def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email)
        return self.db.scalars(stmt).first()

    def get_by_google_id(self, google_id: str) -> User | None:
        stmt = select(User).where(User.google_id == google_id)
        return self.db.scalars(stmt).first()

    def get_by_id_with_role(self, id_: object, role: str | None = None) -> User | None:
        """Fetch a user, optionally filtering by role (used by reviewer endpoints)."""
        stmt = select(User).where(User.id == id_)
        if role:
            stmt = stmt.where(User.role == role)
        return self.db.scalars(stmt).first()