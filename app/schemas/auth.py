from pydantic import BaseModel

from app.schemas.user import UserRead


class GoogleLoginURL(BaseModel):
    """Response of GET /auth/google/login — frontend redirects to this URL."""
    authorization_url: str


class TokenResponse(BaseModel):
    """Returned after successful Google OAuth callback."""
    access_token: str
    token_type: str = "bearer"
    user: UserRead


class GoogleCallbackRequest(BaseModel):
    """Frontend sends the OAuth code to the backend for exchange."""
    code: str
    role: str | None = None  # Optional: "Requester" or "Reviewer" for new users