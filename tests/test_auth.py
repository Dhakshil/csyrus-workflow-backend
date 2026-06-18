"""Tests for /auth/me and JWT validation."""
from main import app
from app.core.security import create_access_token


class TestAuthMe:
    """GET /auth/me"""

    def test_get_current_user_with_valid_token(
        self, client, auth_headers, requester
    ):
        """Valid JWT returns the user's profile."""
        response = client.get("/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == requester.email
        assert data["role"] == "Requester"
        assert "google_id" in data
        assert "id" in data

    def test_get_current_user_without_token(self, client):
        """Missing Authorization header returns 401."""
        response = client.get("/auth/me")
        assert response.status_code == 401

    def test_get_current_user_with_malformed_header(self, client):
        """Malformed Authorization header returns 401."""
        response = client.get(
            "/auth/me",
            headers={"Authorization": "NotBearer abc123"},
        )
        assert response.status_code == 401

    def test_get_current_user_with_invalid_token(self, client):
        """Invalid JWT signature returns 401."""
        response = client.get(
            "/auth/me",
            headers={"Authorization": "Bearer invalid.jwt.token"},
        )
        assert response.status_code == 401

    def test_get_current_user_with_nonexistent_user(
        self, client, db, requester
    ):
        """Valid JWT but user was deleted from DB returns 401."""
        token = create_access_token(subject=str(requester.id))
        db.delete(requester)
        db.commit()
        response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 401