"""FastAPI dependencies shared across routes."""
import uuid

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.core.exceptions import AuthenticationError
from app.core.security import decode_access_token
from app.database.session import get_db
from app.models.user import User
from app.repositories.user import UserRepository


def get_current_user(
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
) -> User:
    """Extract and verify the JWT from the Authorization header, return the User.

    Usage in a route:
        @router.get("/me")
        def me(current_user: User = Depends(get_current_user)):
            return current_user

    The header must look like:
        Authorization: Bearer <jwt-token>
    """
    if not authorization:
        raise AuthenticationError("Missing Authorization header")

    # Parse "Bearer <token>"
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise AuthenticationError("Invalid Authorization header format")
    token = parts[1]

    # Decode and verify the JWT
    try:
        payload = decode_access_token(token)
    except ValueError as e:
        raise AuthenticationError(str(e)) from e

    # Extract user ID from the 'sub' claim
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise AuthenticationError("Token missing 'sub' claim")

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError as e:
        raise AuthenticationError("Token has invalid user ID") from e

    # Fetch the user from DB (ensures user still exists / isn't deleted)
    user = UserRepository(db).get_by_id(user_id)
    if user is None:
        raise AuthenticationError("User not found")
    return user