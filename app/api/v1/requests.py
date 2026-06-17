"""Requester endpoints — CRUD operations on approval requests.

All endpoints require authentication (JWT). The current user must have
role=Requester to create requests, and can only access their own requests.
"""
import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database.session import get_db
from app.models.enums import RequestStatus
from app.models.user import User
from app.schemas.approval_request import (
    RequestCreate,
    RequestList,
    RequestRead,
    RequestUpdate,
)
from app.services.request_service import RequestService

router = APIRouter(prefix="/requests", tags=["requests"])


@router.post(
    "",
    response_model=RequestRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new approval request",
)
def create_request(
    payload: RequestCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RequestRead:
    """Create a new approval request as the current user.

    The current user must have role=Requester. The reviewer_id must reference
    an existing user with role=Reviewer.
    """
    service = RequestService(db)
    request = service.create_request(current_user, payload)
    return RequestRead.model_validate(request)


@router.get(
    "",
    response_model=RequestList,
    summary="List my requests",
)
def list_my_requests(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RequestList:
    """List all approval requests created by the current user, paginated."""
    service = RequestService(db)
    items, total = service.list_my_requests(current_user, skip, limit)
    return RequestList(
        items=[RequestRead.model_validate(r) for r in items],
        total=total,
    )


@router.get(
    "/{request_id}",
    response_model=RequestRead,
    summary="Get a single request",
)
def get_request(
    request_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RequestRead:
    """Get a single approval request by ID.

    The current user must be either the creator or the assigned reviewer.
    """
    service = RequestService(db)
    request = service.get_request(current_user, request_id)
    return RequestRead.model_validate(request)


@router.put(
    "/{request_id}",
    response_model=RequestRead,
    summary="Update a request",
)
def update_request(
    request_id: uuid.UUID,
    payload: RequestUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RequestRead:
    """Update an approval request. Only the creator can edit, and only if PENDING."""
    service = RequestService(db)
    request = service.update_request(current_user, request_id, payload)
    return RequestRead.model_validate(request)


@router.delete(
    "/{request_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a request",
)
def delete_request(
    request_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Delete an approval request. Only the creator can delete, and only if PENDING."""
    service = RequestService(db)
    service.delete_request(current_user, request_id)