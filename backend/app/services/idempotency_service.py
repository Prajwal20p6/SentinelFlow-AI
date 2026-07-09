"""
SentinelFlow AI — Idempotency & Deduplication Service
Caches request outcomes to prevent accidental double-execution of critical state changes.
"""

import json
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session
from ..models.models import IdempotencyKey
from ..core.observability import logger

class IdempotencyService:
    """Manages transactional deduplication keys and caches responses for 1 hour."""

    @staticmethod
    def get_cached_response(db: Session, key: str) -> Optional[Tuple[int, Dict[str, Any]]]:
        """
        Retrieves a non-expired cached response for a given key.
        Returns: Tuple of (status_code, response_body) or None.
        """
        record = db.query(IdempotencyKey).filter(IdempotencyKey.key == key).first()
        if not record:
            return None
            
        # Check expiration
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        if record.expires_at < now:
            logger.info("idempotency_key_expired", key=key)
            db.delete(record)
            db.commit()
            return None

        if not record.response_json:
            # Still processing or empty payload
            return None

        try:
            payload = json.loads(record.response_json)
            return payload.get("status_code", 200), payload.get("body", {})
        except Exception as e:
            logger.warning("idempotency_payload_parse_failed", key=key, error=str(e))
            return None

    @staticmethod
    def register_key(db: Session, key: str, incident_id: Optional[int] = None, action_type: Optional[str] = None) -> bool:
        """
        Registers a new idempotency key with 'PROCESSING' state.
        Returns True if successful, or False if key already exists (concurrent/duplicate).
        """
        # Clean up any expired keys first
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        db.query(IdempotencyKey).filter(IdempotencyKey.expires_at < now).delete()
        db.commit()

        # Check existing key
        existing = db.query(IdempotencyKey).filter(IdempotencyKey.key == key).first()
        if existing:
            return False

        # Add key with 1-hour expiry
        expires_at = now + timedelta(hours=1)
        record = IdempotencyKey(
            key=key,
            incident_id=incident_id,
            action_type=action_type,
            response_json=json.dumps({"status_code": 202, "body": {"message": "Request is being processed"}}),
            expires_at=expires_at,
            created_at=now
        )
        db.add(record)
        try:
            db.commit()
            return True
        except Exception:
            db.rollback()
            return False

    @staticmethod
    def save_response(db: Session, key: str, status_code: int, body: Dict[str, Any]) -> None:
        """Saves the final response payload for an active idempotency key."""
        record = db.query(IdempotencyKey).filter(IdempotencyKey.key == key).first()
        if record:
            try:
                record.response_json = json.dumps({
                    "status_code": status_code,
                    "body": body
                })
                db.commit()
                logger.info("idempotency_response_cached", key=key)
            except Exception as e:
                db.rollback()
                logger.error("idempotency_save_response_failed", key=key, error=str(e))
