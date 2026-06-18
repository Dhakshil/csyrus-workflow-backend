"""Google OAuth 2.0 + JWT issuance.

Flow:
    1. get_google_login_url()  -> builds the URL the user visits on Google
    2. handle_google_callback() -> exchanges code for tokens, fetches user info,
                                   creates/finds User, issues JWT
"""
import json
import secrets
from typing import Any

from authlib.integrations.httpx_client import OAuth2Client
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AuthenticationError
from app.core.security import create_access_token
from app.models.enums import UserRole
from app.models.user import User
from app.repositories.user import UserRepository

# Google OAuth endpoints (well-known, hardcoded)
GOOGLE_DISCOVERY = "https://accounts.google.com/.well-known/openid-configuration"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


class AuthService:
    """Handles the Google OAuth flow and JWT issuance.

    Uses the authorization code flow (server-side), which is the recommended
    approach for web apps per Google's docs.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self.user_repo = UserRepository(db)

    # ---------- Step 1: Build the Google login URL ----------

    def get_google_login_url(self, role: str = "Requester") -> str:
        """Build the Google OAuth consent screen URL.

        Args:
            role: "Requester" or "Reviewer". Stored in OAuth state so it
                  survives the round-trip through Google.

        Returns:
            The full URL the frontend should redirect the browser to.
        """
        # Validate role
        try:
            UserRole(role)
        except ValueError as e:
            raise AuthenticationError(f"Invalid role: {role}") from e

        # State is a JSON blob that Google returns unchanged in the callback.
        # We use it for two purposes:
        #   1. CSRF protection (nonce must match on callback)
        #   2. Carrying the user's role choice across the OAuth redirect
        state = json.dumps({
            "nonce": secrets.token_urlsafe(16),
            "role": role,
        })

        client = OAuth2Client(
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
        )
        url, _ = client.create_authorization_url(
            "https://accounts.google.com/o/oauth2/v2/auth",
            redirect_uri=settings.GOOGLE_REDIRECT_URI,
            scope="openid email profile",
            state=state,
            prompt="consent",  # Always show consent screen (helpful during dev)
        )
        return url

    # ---------- Step 2: Handle the OAuth callback ----------

    def handle_google_callback(self, code: str, state: str) -> tuple[User, str]:
        """Exchange the OAuth code for user info, then issue a JWT.

        Args:
            code: The authorization code Google passed back in the callback URL.
            state: The state string we sent in step 1. Contains the role choice.

        Returns:
            Tuple of (User, jwt_token).
        """
        # 1. Decode state to get the role the user chose
        try:
            state_data = json.loads(state)
            role_str = state_data.get("role", "Requester")
            UserRole(role_str)  # validate
        except (json.JSONDecodeError, ValueError) as e:
            raise AuthenticationError("Invalid OAuth state") from e

        # 2. Exchange code for an access token (server-to-server)
        token_data = self._exchange_code_for_token(code)

        # 3. Use access token to fetch the user's Google profile
        google_user = self._fetch_google_userinfo(token_data["access_token"])

        # 4. Find or create the User row
        user = self._upsert_user(google_user, role_str)

        # 5. Issue a JWT containing the user's UUID
        jwt_token = create_access_token(
            subject=str(user.id),
            extra_claims={"role": user.role.value},
        )
        return user, jwt_token

    # ---------- Private helpers ----------

    def _exchange_code_for_token(self, code: str) -> dict[str, Any]:
        """Trade the authorization code for an access_token at Google's token endpoint."""
        client = OAuth2Client(
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
        )
        try:
            token = client.fetch_token(
                url="https://oauth2.googleapis.com/token",
                authorization_response=f"?code={code}",
                redirect_uri=settings.GOOGLE_REDIRECT_URI,
                grant_type="authorization_code",
            )
            if "access_token" not in token:
                raise AuthenticationError("Google did not return an access token")
            return token
        except Exception as e:
            raise AuthenticationError(f"Failed to exchange code: {e}") from e

    def _fetch_google_userinfo(self, access_token: str) -> dict[str, Any]:
        """Call Google's userinfo endpoint with the access token."""
        client = OAuth2Client(token={"access_token": access_token})
        try:
            resp = client.get(GOOGLE_USERINFO_URL)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            raise AuthenticationError(f"Failed to fetch user info: {e}") from e

    def _upsert_user(self, google_user: dict[str, Any], role: str) -> User:
        """Find an existing user by google_id, or create a new one.

        Google returns: {sub, email, email_verified, name, picture, ...}
        We use 'sub' as google_id (it's Google's stable user identifier).
        """
        google_id = google_user.get("sub")
        email = google_user.get("email")
        name = google_user.get("name") or email or "Unknown"

        if not google_id or not email:
            raise AuthenticationError("Google did not return required user fields")

        existing = self.user_repo.get_by_google_id(google_id)
        if existing:
            # Optionally update name/email in case they changed in Google
            existing.name = name
            existing.email = email
            self.db.commit()
            return existing

        # New user — create with the role they chose at login
        new_user = User(
            name=name,
            email=email,
            google_id=google_id,
            role=UserRole(role),
        )
        self.user_repo.create(new_user)
        self.db.commit()
        self.db.refresh(new_user)
        return new_user