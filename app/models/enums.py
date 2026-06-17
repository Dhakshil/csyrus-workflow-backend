from enum import Enum


class UserRole(str, Enum):
    """User roles. Maps to the 'role' column in the users table."""
    REQUESTER = "Requester"
    REVIEWER = "Reviewer"


class Priority(str, Enum):
    """Request urgency level. Maps to 'priority' column in approval_requests."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class RequestStatus(str, Enum):
    """Current state of an approval request. Maps to 'status' column."""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ReviewActionType(str, Enum):
    """Decision taken by a reviewer. Maps to 'action' column in review_actions."""
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"