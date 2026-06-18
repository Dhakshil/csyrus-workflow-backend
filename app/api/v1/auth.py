"""Google OAuth endpoints.

    GET /auth/google/login     -> returns the Google consent URL
    GET /auth/google/callback  -> Google redirects here with ?code=xxx
    GET /auth/me               -> returns the current user (requires JWT)
"""
from fastapi import APIRouter, Depends, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.schemas.auth import GoogleLoginURL, TokenResponse
from app.schemas.user import UserRead
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/google/login", response_model=GoogleLoginURL)
def google_login(
    role: str = Query(default="Requester", description="User role: Requester or Reviewer"),
    db: Session = Depends(get_db),
) -> GoogleLoginURL:
    """Returns the Google OAuth consent screen URL.

    Frontend should redirect the browser to this URL.
    """
    auth_service = AuthService(db)
    url = auth_service.get_google_login_url(role=role)
    return GoogleLoginURL(authorization_url=url)


@router.get("/google/callback")
def google_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    """Google redirects here after the user consents.

    We exchange the code for tokens, find/create the user, issue a JWT,
    then redirect the browser to the frontend with the token in the URL.
    """
    auth_service = AuthService(db)
    try:
        user, jwt_token = auth_service.handle_google_callback(code=code, state=state)
    except Exception as e:
        # On failure, redirect to frontend with an error param
        # (The user is in a browser context — we can't return JSON here)
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/auth/callback?error={str(e)[:200]}"
        )

    # Redirect to frontend with the token in the URL fragment.
    # Using # instead of ? keeps the token out of server logs and referrer headers.
    redirect = f"{settings.FRONTEND_URL}/auth/callback#token={jwt_token}"
    return RedirectResponse(url=redirect)


@router.get("/me", response_model=UserRead)
def me(current_user: User = Depends(get_current_user)) -> UserRead:
    """Returns the currently authenticated user's profile."""
    return UserRead.model_validate(current_user)