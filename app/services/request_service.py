import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.models.approval_request import ApprovalRequest
from app.models.enums import RequestStatus
from app.models.user import User
from app.repositories.approval_request import ApprovalRequestRepository
from app.repositories.user import UserRepository
from app.schemas.approval_request import RequestCreate, RequestUpdate


class RequestService:
    """Business logic for approval requests owned by a Requester.

    Rules enforced:
    - Only the creator can view/edit/delete their own request
    - A request cannot be edited once a decision is made (APPROVED/REJECTED)
    - Reviewer must exist and have role=Reviewer
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self.request_repo = ApprovalRequestRepository(db)
        self.user_repo = UserRepository(db)

    def create_request(
        self, current_user: User, payload: RequestCreate
    ) -> ApprovalRequest:
        """Create a new approval request on behalf of current_user."""
        if current_user.role.value != "Requester":
            raise ForbiddenError("Only requesters can create approval requests")

        reviewer = self.user_repo.get_by_id(payload.reviewer_id)
        if reviewer is None:
            raise NotFoundError("Reviewer not found")
        if reviewer.role.value != "Reviewer":
            raise ConflictError("Assigned user is not a reviewer")

        request = ApprovalRequest(
            title=payload.title,
            description=payload.description,
            priority=payload.priority,
            status=RequestStatus.PENDING,
            created_by=current_user.id,
            reviewer_id=payload.reviewer_id,
        )
        self.request_repo.create(request)
        self.db.commit()
        return self.request_repo.get_by_id(request.id)  # return with relationships loaded

    def get_request(self, current_user: User, request_id: uuid.UUID) -> ApprovalRequest:
        """Fetch a single request. Both creator and assigned reviewer can view."""
        request = self.request_repo.get_by_id(request_id)
        if request is None:
            raise NotFoundError("Request not found")
        self._assert_view_permission(current_user, request)
        return request

    def list_my_requests(
        self, current_user: User, skip: int = 0, limit: int = 50
    ) -> tuple[list[ApprovalRequest], int]:
        """List requests created by current_user."""
        items = self.request_repo.list_by_creator(current_user.id, skip, limit)
        total = self.request_repo.count_by_creator(current_user.id)
        return items, total

    def update_request(
        self, current_user: User, request_id: uuid.UUID, payload: RequestUpdate
    ) -> ApprovalRequest:
        """Update a request. Only the creator can edit, and only if PENDING."""
        request = self.request_repo.get_by_id(request_id)
        if request is None:
            raise NotFoundError("Request not found")
        if request.created_by != current_user.id:
            raise ForbiddenError("You can only edit your own requests")
        if request.status != RequestStatus.PENDING:
            raise ConflictError(
                f"Cannot edit a request that has been {request.status.value}"
            )

        # Apply only the fields that were provided (partial update)
        update_data = payload.model_dump(exclude_unset=True)
        if "reviewer_id" in update_data and update_data["reviewer_id"]:
            reviewer = self.user_repo.get_by_id(update_data["reviewer_id"])
            if reviewer is None:
                raise NotFoundError("Reviewer not found")
            if reviewer.role.value != "Reviewer":
                raise ConflictError("Assigned user is not a reviewer")

        for field, value in update_data.items():
            setattr(request, field, value)

        self.db.flush()
        self.db.commit()
        return self.request_repo.get_by_id(request.id)

    def delete_request(
        self, current_user: User, request_id: uuid.UUID
    ) -> None:
        """Delete a request. Only the creator can delete, and only if PENDING."""
        request = self.request_repo.get_by_id(request_id)
        if request is None:
            raise NotFoundError("Request not found")
        if request.created_by != current_user.id:
            raise ForbiddenError("You can only delete your own requests")
        if request.status != RequestStatus.PENDING:
            raise ConflictError(
                f"Cannot delete a request that has been {request.status.value}"
            )

        self.request_repo.delete(request)
        self.db.commit()

    def _assert_view_permission(
        self, user: User, request: ApprovalRequest
    ) -> None:
        """Either the creator or the assigned reviewer can view a request."""
        if request.created_by != user.id and request.reviewer_id != user.id:
            raise ForbiddenError("You do not have access to this request")