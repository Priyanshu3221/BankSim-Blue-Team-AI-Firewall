"""Administrative endpoints protected by strict Role-Based Access Control (RBAC)."""

from typing import Any, Dict, List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import SecurityEvent, User
from backend.schemas import SecurityEventRead
from backend.security.dependencies import require_admin

admin_router = APIRouter(prefix="/admin", tags=["Admin RBAC"])


@admin_router.get(
    "/dashboard",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Admin dashboard overview (Admin privileges required)",
)
def get_admin_dashboard(
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Retrieve high-level administrative status and metrics.

    Accessible exclusively to users with the ADMIN role.
    """
    total_users = db.query(User).count()
    total_events = db.query(SecurityEvent).count()

    return {
        "status": "operational",
        "admin_username": current_admin.username,
        "role": current_admin.role,
        "metrics": {
            "total_users": total_users,
            "security_events_logged": total_events,
        },
    }


@admin_router.get(
    "/security-events",
    response_model=List[SecurityEventRead],
    status_code=status.HTTP_200_OK,
    summary="Retrieve audit logs of security events (Admin privileges required)",
)
def list_security_events(
    limit: int = 50,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> List[SecurityEventRead]:
    """List recent security and threat detection events for security administrators."""
    events = (
        db.query(SecurityEvent)
        .order_by(SecurityEvent.created_at.desc())
        .limit(limit)
        .all()
    )
    return [SecurityEventRead.model_validate(event) for event in events]
