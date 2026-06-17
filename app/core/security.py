"""JWT helpers. We use python-jose for JWT creation/verification.

JWT structure:
    header:  {"alg": "HS256", "typ": "JWT"}
    payload: {"sub": "<user-uuid>", "exp": <unix-timestamp>, "iat": <unix-timestamp>}
    signature: HMAC-SHA256 of (header + "." + payload) using SECRET_KEY

The frontend sends this token in the Authorization header:
    Authorization: Bearer <token>
"""
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt

from app.core.config import settings


def create_access_token(subject: str, extra_claims: dict[str, Any] | None = None) -> str:
    """Create a signed JWT for the given subject (user ID).

    Args:
        subject: The user's UUID as a string.
        extra_claims: Optional additional claims (e.g. role).

    Returns:
        Encoded JWT string.
    """
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.JWT_EXPIRES_MINUTES)).timestamp()),
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and verify a JWT. Raises JWTError if invalid or expired.

    Returns the full payload dict (includes 'sub', 'iat', 'exp', and any extras).
    """
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except JWTError as e:
        raise ValueError(f"Invalid token: {e}") from e