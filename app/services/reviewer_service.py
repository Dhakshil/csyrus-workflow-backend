import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.models.approval_request import ApprovalRequest
from app.models.enums import RequestStatus, ReviewActionType
from app.models.review_action import ReviewAction
from app.models.user import User
from app.repositories.approval_request import ApprovalRequestRepository
from app.repositories.review_action import ReviewActionRepository
from app.schemas.review_action import ReviewDecision


class ReviewerService:
    """Business logic for reviewer actions on approval requests.

    Rules enforced:
    - Only users with role=Reviewer can act on requests
    - A reviewer can only act on requests assigned to them
    - A reviewer can only act on PENDING requests (no double-decisions)
    - Approving/Rejecting creates a ReviewAction row AND flips the request status
    - Both ops happen in one DB transaction (atomic)
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self.request_repo = ApprovalRequestRepository(db)
        self.action_repo = ReviewActionRepository(db)

    def list_assigned_requests(
        self,
        current_user: User,
        status: RequestStatus | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[ApprovalRequest], int]:
        """List all requests assigned to current_user (optionally filtered by status)."""
        if current_user.role.value != "Reviewer":
            raise ForbiddenError("Only reviewers can view the reviewer dashboard")

        items = self.request_repo.list_by_reviewer(
            current_user.id, status, skip, limit
        )
        total = self.request_repo.count_by_reviewer(current_user.id, status)
        return items, total

    def approve_request(
        self, current_user: User, request_id: uuid.UUID, payload: ReviewDecision
    ) -> ApprovalRequest:
        return self._decide(
            current_user, request_id, payload, ReviewActionType.APPROVED
        )

    def reject_request(
        self, current_user: User, request_id: uuid.UUID, payload: ReviewDecision
    ) -> ApprovalRequest:
        return self._decide(
            current_user, request_id, payload, ReviewActionType.REJECTED
        )

    def _decide(
        self,
        current_user: User,
        request_id: uuid.UUID,
        payload: ReviewDecision,
        action: ReviewActionType,
    ) -> ApprovalRequest:
        """Shared logic for approve/reject. Atomic: create action + flip status."""
        if current_user.role.value != "Reviewer":
            raise ForbiddenError("Only reviewers can approve or reject requests")

        request = self.request_repo.get_by_id(request_id)
        if request is None:
            raise NotFoundError("Request not found")
        if request.reviewer_id != current_user.id:
            raise ForbiddenError("This request is not assigned to you")
        if request.status != RequestStatus.PENDING:
            raise ConflictError(
                f"Request has already been {request.status.value}"
            )

        # 1. Create the review action record
        review_action = ReviewAction(
            request_id=request.id,
            action=action,
            comments=payload.comments,
            reviewed_by=current_user.id,
        )
        self.action_repo.create(review_action)

        # 2. Flip the request status
        new_status = (
            RequestStatus.APPROVED
            if action == ReviewActionType.APPROVED
            else RequestStatus.REJECTED
        )
        request.status = new_status
        self.db.flush()
        self.db.commit()

        # 3. Return the request with relationships refreshed
        return self.request_repo.get_by_id(request.id)