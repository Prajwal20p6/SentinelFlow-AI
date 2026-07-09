"""
SentinelFlow AI — Feature Flag API Router
Exposes endpoints to view and toggle runtime feature flags.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from ..core.database import get_db
from ..middleware.auth import require_role
from ..models.models import User
from ..services.feature_flag_service import list_all_flags, toggle_flag, FeatureFlagKey

router = APIRouter(prefix="/feature-flags", tags=["Feature Flags"])

@router.get("")
def get_feature_flags(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Retrieve all registered feature flags. Restricted to Admin."""
    return list_all_flags(db)

@router.post("/{key}/toggle")
def toggle_feature_flag(
    key: str,
    body: Dict[str, bool],
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Toggle a feature flag value. Restricted to Admin."""
    try:
        flag_key = FeatureFlagKey(key)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid feature flag key: {key}")
        
    value = body.get("value", False)
    new_val = toggle_flag(db, flag_key, value, updated_by=current_user.email)
    return {
        "key": key,
        "value": new_val,
        "message": f"Feature flag {key} successfully set to {new_val}."
    }
