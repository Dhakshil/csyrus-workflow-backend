"""Tests for /requests endpoints (Requester CRUD)."""
import uuid


class TestCreateRequest:
    """POST /requests"""

    def test_create_request_success(
        self, client, auth_headers, reviewer
    ):
        payload = {
            "title": "Leave request",
            "description": "Need a day off",
            "priority": "MEDIUM",
            "reviewer_id": str(reviewer.id),
        }
        response = client.post("/requests", json=payload, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Leave request"
        assert data["status"] == "PENDING"
        assert data["priority"] == "MEDIUM"
        assert data["reviewer_id"] == str(reviewer.id)
        assert "id" in data
        assert "created_at" in data

    def test_create_request_without_auth(self, client, reviewer):
        payload = {
            "title": "Test",
            "description": "Test",
            "priority": "LOW",
            "reviewer_id": str(reviewer.id),
        }
        response = client.post("/requests", json=payload)
        assert response.status_code == 401

    def test_create_request_with_nonexistent_reviewer(
        self, client, auth_headers
    ):
        payload = {
            "title": "Test",
            "description": "Test",
            "priority": "LOW",
            "reviewer_id": str(uuid.uuid4()),
        }
        response = client.post("/requests", json=payload, headers=auth_headers)
        assert response.status_code == 404

    def test_create_request_with_requester_as_reviewer(
        self, client, auth_headers, requester
    ):
        """Assigning a Requester (not Reviewer) as reviewer fails."""
        payload = {
            "title": "Test",
            "description": "Test",
            "priority": "LOW",
            "reviewer_id": str(requester.id),
        }
        response = client.post("/requests", json=payload, headers=auth_headers)
        assert response.status_code == 409

    def test_create_request_with_invalid_priority(
        self, client, auth_headers, reviewer
    ):
        payload = {
            "title": "Test",
            "description": "Test",
            "priority": "URGENT",  # not in enum
            "reviewer_id": str(reviewer.id),
        }
        response = client.post("/requests", json=payload, headers=auth_headers)
        assert response.status_code == 422

    def test_create_request_with_empty_title(
        self, client, auth_headers, reviewer
    ):
        payload = {
            "title": "",
            "description": "Test",
            "priority": "LOW",
            "reviewer_id": str(reviewer.id),
        }
        response = client.post("/requests", json=payload, headers=auth_headers)
        assert response.status_code == 422


class TestListRequests:
    """GET /requests"""

    def test_list_empty(self, client, auth_headers):
        response = client.get("/requests", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_list_returns_only_my_requests(
        self, client, auth_headers, requester, second_requester, reviewer
    ):
        # Create a request as the main requester
        client.post(
            "/requests",
            json={
                "title": "Mine",
                "description": "owned by requester",
                "priority": "LOW",
                "reviewer_id": str(reviewer.id),
            },
            headers=auth_headers,
        )

        # Create a request directly in DB as the other requester
        from app.models.approval_request import ApprovalRequest
        from app.models.enums import Priority, RequestStatus
        from tests.conftest import TestingSessionLocal

        # Use a fresh session to insert as the other user
        db = TestingSessionLocal()
        other_request = ApprovalRequest(
            title="Not mine",
            description="owned by second_requester",
            priority=Priority.LOW,
            status=RequestStatus.PENDING,
            created_by=second_requester.id,
            reviewer_id=reviewer.id,
        )
        db.add(other_request)
        db.commit()
        db.close()

        response = client.get("/requests", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["title"] == "Mine"


class TestGetRequest:
    """GET /requests/{id}"""

    def test_get_request_success(
        self, client, auth_headers, reviewer
    ):
        create = client.post(
            "/requests",
            json={
                "title": "Get me",
                "description": "test",
                "priority": "LOW",
                "reviewer_id": str(reviewer.id),
            },
            headers=auth_headers,
        )
        request_id = create.json()["id"]

        response = client.get(f"/requests/{request_id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["title"] == "Get me"

    def test_get_nonexistent_request(self, client, auth_headers):
        response = client.get(
            f"/requests/{uuid.uuid4()}", headers=auth_headers
        )
        assert response.status_code == 404

    def test_get_request_as_reviewer(
        self, client, auth_headers, reviewer_headers, reviewer
    ):
        """Reviewer can view a request assigned to them."""
        create = client.post(
            "/requests",
            json={
                "title": "For review",
                "description": "test",
                "priority": "LOW",
                "reviewer_id": str(reviewer.id),
            },
            headers=auth_headers,
        )
        request_id = create.json()["id"]

        response = client.get(
            f"/requests/{request_id}", headers=reviewer_headers
        )
        assert response.status_code == 200


class TestUpdateRequest:
    """PUT /requests/{id}"""

    def test_update_request_success(
        self, client, auth_headers, reviewer
    ):
        create = client.post(
            "/requests",
            json={
                "title": "Original",
                "description": "test",
                "priority": "LOW",
                "reviewer_id": str(reviewer.id),
            },
            headers=auth_headers,
        )
        request_id = create.json()["id"]

        response = client.put(
            f"/requests/{request_id}",
            json={"priority": "HIGH", "title": "Updated"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["priority"] == "HIGH"
        assert data["title"] == "Updated"

    def test_update_request_after_decision_fails(
        self, client, auth_headers, reviewer_headers, reviewer
    ):
        """Cannot edit a request that's already APPROVED."""
        create = client.post(
            "/requests",
            json={
                "title": "Approved one",
                "description": "test",
                "priority": "LOW",
                "reviewer_id": str(reviewer.id),
            },
            headers=auth_headers,
        )
        request_id = create.json()["id"]

        # Reviewer approves
        client.post(
            f"/reviewer/requests/{request_id}/approve",
            json={"comments": "ok"},
            headers=reviewer_headers,
        )

        # Requester tries to edit
        response = client.put(
            f"/requests/{request_id}",
            json={"title": "New title"},
            headers=auth_headers,
        )
        assert response.status_code == 409


class TestDeleteRequest:
    """DELETE /requests/{id}"""

    def test_delete_request_success(
        self, client, auth_headers, reviewer
    ):
        create = client.post(
            "/requests",
            json={
                "title": "Delete me",
                "description": "test",
                "priority": "LOW",
                "reviewer_id": str(reviewer.id),
            },
            headers=auth_headers,
        )
        request_id = create.json()["id"]

        response = client.delete(
            f"/requests/{request_id}", headers=auth_headers
        )
        assert response.status_code == 204

        # Verify it's gone
        get = client.get(f"/requests/{request_id}", headers=auth_headers)
        assert get.status_code == 404

    def test_delete_request_after_decision_fails(
        self, client, auth_headers, reviewer_headers, reviewer
    ):
        create = client.post(
            "/requests",
            json={
                "title": "Will be rejected",
                "description": "test",
                "priority": "LOW",
                "reviewer_id": str(reviewer.id),
            },
            headers=auth_headers,
        )
        request_id = create.json()["id"]

        client.post(
            f"/reviewer/requests/{request_id}/reject",
            json={"comments": "no"},
            headers=reviewer_headers,
        )

        response = client.delete(
            f"/requests/{request_id}", headers=auth_headers
        )
        assert response.status_code == 409