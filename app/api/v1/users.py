"""User-related endpoints — currently just listing reviewers (for the request form)."""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database.session import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.user import UserBrief

router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "/reviewers",
    response_model=list[UserBrief],
    summary="List all reviewers (for the request form dropdown)",
)
def list_reviewers(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[UserBrief]:
    """Return all users with role=Reviewer. Used to populate the reviewer dropdown."""
    stmt = select(User).where(User.role == UserRole.REVIEWER).order_by(User.name)
    users = db.scalars(stmt).all()
    return [UserBrief.model_validate(u) for u in users]