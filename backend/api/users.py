"""User management endpoints with ownership boundaries."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User
from backend.schemas import UserRead
from backend.security.dependencies import get_current_user

users_router = APIRouter(prefix="/users", tags=["Users"])


@users_router.get(
    "/me",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
    summary="Retrieve profile of the currently authenticated user",
)
def get_my_profile(
    current_user: User = Depends(get_current_user),
) -> UserRead:
    """Return profile details for the authenticated user."""
    return UserRead.model_validate(current_user)


@users_router.get(
    "/{user_id}",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
    summary="Retrieve user profile by ID with strict ownership boundary enforcement",
)
def get_user_by_id(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserRead:
    """Retrieve user by ID.

    Ownership boundary: Regular users are strictly forbidden from viewing another user's profile.
    Admin privileges do not bypass user data boundary for user profile endpoints.
    """
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: cannot access other users' resources.",
        )

    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    return UserRead.model_validate(target_user)
