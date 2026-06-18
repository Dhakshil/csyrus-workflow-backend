"""Tests for /reviewer endpoints."""
import uuid


class TestReviewerList:
    """GET /reviewer/requests"""

    def test_list_assigned_requests(
        self, client, auth_headers, reviewer_headers, reviewer
    ):
        # Create a request as requester
        client.post(
            "/requests",
            json={
                "title": "Review me",
                "description": "test",
                "priority": "LOW",
                "reviewer_id": str(reviewer.id),
            },
            headers=auth_headers,
        )

        response = client.get("/reviewer/requests", headers=reviewer_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["title"] == "Review me"

    def test_requester_cannot_access_reviewer_endpoints(
        self, client, auth_headers
    ):
        """A Requester calling /reviewer/requests gets 403."""
        response = client.get("/reviewer/requests", headers=auth_headers)
        assert response.status_code == 403

    def test_filter_by_status(
        self, client, auth_headers, reviewer_headers, reviewer
    ):
        # Create three requests
        created_ids = []
        for title in ["A", "B", "C"]:
            resp = client.post(
                "/requests",
                json={
                    "title": title,
                    "description": "x",
                    "priority": "LOW",
                    "reviewer_id": str(reviewer.id),
                },
                headers=auth_headers,
            )
            created_ids.append(resp.json()["id"])

        # Approve one specific request (the middle one)
        client.post(
            f"/reviewer/requests/{created_ids[1]}/approve",
            json={"comments": "ok"},
            headers=reviewer_headers,
        )

        # Filter by PENDING — should return 2 (A and C)
        pending = client.get(
            "/reviewer/requests?status=PENDING", headers=reviewer_headers
        )
        assert pending.status_code == 200
        assert pending.json()["total"] == 2
        pending_titles = {item["title"] for item in pending.json()["items"]}
        assert pending_titles == {"A", "C"}

        # Filter by APPROVED — should return 1 (B)
        approved = client.get(
            "/reviewer/requests?status=APPROVED", headers=reviewer_headers
        )
        assert approved.json()["total"] == 1
        assert approved.json()["items"][0]["title"] == "B"


class TestApproveReject:
    """POST /reviewer/requests/{id}/approve and /reject"""

    def test_approve_request_success(
        self, client, auth_headers, reviewer_headers, reviewer
    ):
        create = client.post(
            "/requests",
            json={
                "title": "Approve me",
                "description": "test",
                "priority": "LOW",
                "reviewer_id": str(reviewer.id),
            },
            headers=auth_headers,
        )
        request_id = create.json()["id"]

        response = client.post(
            f"/reviewer/requests/{request_id}/approve",
            json={"comments": "Looks good"},
            headers=reviewer_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "APPROVED"
        assert len(data["review_actions"]) == 1
        assert data["review_actions"][0]["action"] == "APPROVED"
        assert data["review_actions"][0]["comments"] == "Looks good"

    def test_reject_request_success(
        self, client, auth_headers, reviewer_headers, reviewer
    ):
        create = client.post(
            "/requests",
            json={
                "title": "Reject me",
                "description": "test",
                "priority": "LOW",
                "reviewer_id": str(reviewer.id),
            },
            headers=auth_headers,
        )
        request_id = create.json()["id"]

        response = client.post(
            f"/reviewer/requests/{request_id}/reject",
            json={"comments": "Insufficient info"},
            headers=reviewer_headers,
        )
        assert response.status_code == 200
        assert response.json()["status"] == "REJECTED"

    def test_double_approve_fails(
        self, client, auth_headers, reviewer_headers, reviewer
    ):
        create = client.post(
            "/requests",
            json={
                "title": "Already approved",
                "description": "test",
                "priority": "LOW",
                "reviewer_id": str(reviewer.id),
            },
            headers=auth_headers,
        )
        request_id = create.json()["id"]

        client.post(
            f"/reviewer/requests/{request_id}/approve",
            json={"comments": "first"},
            headers=reviewer_headers,
        )

        # Second approve attempt
        response = client.post(
            f"/reviewer/requests/{request_id}/approve",
            json={"comments": "second"},
            headers=reviewer_headers,
        )
        assert response.status_code == 409

    def test_approve_nonexistent_request(
        self, client, reviewer_headers
    ):
        response = client.post(
            f"/reviewer/requests/{uuid.uuid4()}/approve",
            json={"comments": "test"},
            headers=reviewer_headers,
        )
        assert response.status_code == 404

    def test_approve_without_comments_fails(
        self, client, auth_headers, reviewer_headers, reviewer
    ):
        create = client.post(
            "/requests",
            json={
                "title": "Need comments",
                "description": "test",
                "priority": "LOW",
                "reviewer_id": str(reviewer.id),
            },
            headers=auth_headers,
        )
        request_id = create.json()["id"]

        # Empty comments
        response = client.post(
            f"/reviewer/requests/{request_id}/approve",
            json={"comments": ""},
            headers=reviewer_headers,
        )
        assert response.status_code == 422