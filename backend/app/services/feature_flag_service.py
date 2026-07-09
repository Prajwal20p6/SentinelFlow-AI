"""
SentinelFlow AI — Dynamic Feature Flag Service
Combines environment variables, database overrides, cache lookups, and hot reloading.
"""

import time
from enum import Enum
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from ..core.config import get_settings
from ..core.observability import logger
from ..models.models import FeatureFlag

settings = get_settings()

# ── Feature Flag Keys ────────────────────────────────────────
class FeatureFlagKey(str, Enum):
    DEMO_MODE = "FF_DEMO_MODE"
    SLACK_NOTIFICATIONS = "FF_SLACK_NOTIFICATIONS"
    CLOUD_REMEDIATION = "FF_CLOUD_REMEDIATION"
    MFA_REQUIRED = "FF_MFA_REQUIRED"
    WEBSOCKET_UPDATES = "FF_WEBSOCKET_UPDATES"


# In-memory local cache with TTL verification
_FLAG_CACHE: Dict[str, Dict[str, Any]] = {}
CACHE_TTL_SECONDS = 10.0


# ── Feature Flag Resolver ───────────────────────────────────
def is_enabled(db: Session, key: FeatureFlagKey) -> bool:
    """
    Check if a feature flag is enabled.
    Resolution Order: Cache -> Database -> Env/Settings Config.
    """
    now = time.time()
    flag_str = key.value

    # 1. Cache hit check
    if flag_str in _FLAG_CACHE:
        cache_entry = _FLAG_CACHE[flag_str]
        if now - cache_entry["timestamp"] < CACHE_TTL_SECONDS:
            return cache_entry["value"]

    # 2. Database lookup check
    try:
        db_flag = db.query(FeatureFlag).filter(FeatureFlag.key == flag_str).first()
        if db_flag is not None:
            # Update cache and return
            _FLAG_CACHE[flag_str] = {
                "value": db_flag.value,
                "timestamp": now
            }
            return db_flag.value
    except Exception as e:
        logger.warning("feature_flag_db_error", error=str(e))

    # 3. Fallback to settings config
    default_val = getattr(settings, flag_str, False)
    
    # Auto-seed the database if it wasn't there (within a safe try-except)
    try:
        new_flag = FeatureFlag(
            key=flag_str,
            value=default_val,
            description=f"Auto-seeded default for {flag_str}"
        )
        db.add(new_flag)
        db.commit()
        db.refresh(new_flag)
    except Exception:
        # Rolled back database session in case of transaction issue (e.g. unique constraint)
        db.rollback()

    _FLAG_CACHE[flag_str] = {
        "value": default_val,
        "timestamp": now
    }
    return default_val


def toggle_flag(db: Session, key: FeatureFlagKey, value: bool, updated_by: str = "admin") -> bool:
    """Toggle a feature flag value in the database and clear cache."""
    flag_str = key.value
    db_flag = db.query(FeatureFlag).filter(FeatureFlag.key == flag_str).first()
    
    if db_flag is None:
        db_flag = FeatureFlag(
            key=flag_str,
            value=value,
            description=f"Custom flag for {flag_str}",
            updated_by=updated_by
        )
        db.add(db_flag)
    else:
        db_flag.value = value
        db_flag.updated_by = updated_by
        
    db.commit()
    db.refresh(db_flag)

    # Hot-reload: invalidate cache entry instantly
    if flag_str in _FLAG_CACHE:
        del _FLAG_CACHE[flag_str]
        
    return db_flag.value


def list_all_flags(db: Session) -> List[Dict[str, Any]]:
    """List details of all available feature flags."""
    # Seed missing flags first to ensure all enums are represented
    for key in FeatureFlagKey:
        _ = is_enabled(db, key)
        
    flags = db.query(FeatureFlag).all()
    return [
        {
            "key": f.key,
            "value": f.value,
            "description": f.description,
            "updated_by": f.updated_by,
            "updated_at": f.updated_at
        }
        for f in flags
    ]


def seed_feature_flags(db: Session) -> None:
    """Pre-seed all registered feature flags."""
    for key in FeatureFlagKey:
        is_enabled(db, key)
