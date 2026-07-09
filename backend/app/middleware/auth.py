"""
SentinelFlow AI — Authentication Middleware
JWT token extraction, validation, and RBAC enforcement.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.security import decode_token
from ..models.models import User

security_scheme = HTTPBearer()

# Role hierarchy: admin > responder/engineer > executive > viewer
ROLE_HIERARCHY = {
    "admin": 4,
    "responder": 3,
    "engineer": 3,
    "executive": 2,
    "viewer": 1,
}


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Extract and validate JWT token, return the authenticated user."""
    token = credentials.credentials
    try:
        payload = decode_token(token)
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
            )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )
    return user


def require_role(minimum_role: str):
    """Dependency factory that enforces minimum RBAC role."""
    min_level = ROLE_HIERARCHY.get(minimum_role, 0)

    def _check(user: User = Depends(get_current_user)) -> User:
        user_level = ROLE_HIERARCHY.get(user.role, 0)
        if user_level < min_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {minimum_role}, Current: {user.role}",
            )
        return user

    return _check
