"""Reviewer endpoints — list assigned requests and approve/reject them.

All endpoints require authentication (JWT) + role=Reviewer.
"""
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database.session import get_db
from app.models.enums import RequestStatus
from app.models.user import User
from app.schemas.approval_request import RequestList, RequestRead
from app.schemas.review_action import ReviewDecision
from app.services.reviewer_service import ReviewerService

router = APIRouter(prefix="/reviewer", tags=["reviewer"])


@router.get(
    "/requests",
    response_model=RequestList,
    summary="List requests assigned to me",
)
def list_assigned_requests(
    status_filter: RequestStatus | None = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RequestList:
    """List all approval requests assigned to the current reviewer.

    Optional query param `status=PENDING|APPROVED|REJECTED` filters by state.
    """
    service = ReviewerService(db)
    items, total = service.list_assigned_requests(
        current_user, status=status_filter, skip=skip, limit=limit
    )
    return RequestList(
        items=[RequestRead.model_validate(r) for r in items],
        total=total,
    )


@router.post(
    "/requests/{request_id}/approve",
    response_model=RequestRead,
    summary="Approve a request",
)
def approve_request(
    request_id: uuid.UUID,
    payload: ReviewDecision,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RequestRead:
    """Approve an assigned request. Comments are required."""
    service = ReviewerService(db)
    request = service.approve_request(current_user, request_id, payload)
    return RequestRead.model_validate(request)


@router.post(
    "/requests/{request_id}/reject",
    response_model=RequestRead,
    summary="Reject a request",
)
def reject_request(
    request_id: uuid.UUID,
    payload: ReviewDecision,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RequestRead:
    """Reject an assigned request. Comments are required."""
    service = ReviewerService(db)
    request = service.reject_request(current_user, request_id, payload)
    return RequestRead.model_validate(request)