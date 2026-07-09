"""
SentinelFlow AI — Alert Fingerprinting & Deduplication Service
Generates cryptographic fingerprints, deduplicates identical alerts,
and performs message similarity matching to group related logs into single incidents.
"""

import hashlib
import re
from difflib import SequenceMatcher
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session
from ..models.models import AlertFingerprint, Alert, Incident
from ..core.observability import logger

class AlertFingerprintingService:
    """Orchestrates fingerprint hashing, sliding-window deduplication, and service groupings."""

    @staticmethod
    def generate_fingerprint(source: str, alert_type: str, service: str, message: str) -> str:
        """Constructs a canonical string and MD5 hash representing the alert."""
        msg_lower = message.lower()
        
        # Categorize issue
        issue_category = "general"
        if "cpu" in msg_lower:
            issue_category = "cpu"
        elif "memory" in msg_lower or "oom" in msg_lower:
            issue_category = "memory"
        elif "disk" in msg_lower or "storage" in msg_lower or "pv" in msg_lower:
            issue_category = "disk"
        elif "network" in msg_lower or "rx" in msg_lower or "tx" in msg_lower:
            issue_category = "network"
        elif "unauthorized" in msg_lower or "access" in msg_lower or "auth" in msg_lower:
            issue_category = "security"

        # Extract metric patterns (e.g. CPU > 80% or 94.5%)
        metric_part = ""
        metric_match = re.search(r"(\d+(\.\d+)?%)|(\d+(\.\d+)?\s*(ms|mb|gb|tx|rx|kb))", msg_lower)
        if metric_match:
            metric_part = metric_match.group(0)

        # Build canonical signature
        canonical = (
            f"source:{source.strip().lower()}|"
            f"type:{alert_type.strip().lower()}|"
            f"service:{service.strip().lower()}|"
            f"category:{issue_category}|"
            f"metric:{metric_part}"
        )
        return hashlib.md5(canonical.encode("utf-8")).hexdigest()

    @staticmethod
    def process_incoming_alert(
        db: Session,
        source: str,
        alert_type: str,
        service: str,
        message: str
    ) -> Tuple[Optional[int], bool, AlertFingerprint]:
        """
        Deduplicates incoming alerts.
        Returns:
            (incident_id, is_new, fingerprint_record)
        """
        fingerprint_hash = AlertFingerprintingService.generate_fingerprint(source, alert_type, service, message)
        five_mins_ago = datetime.now(timezone.utc) - timedelta(minutes=5)

        # 1. Exact match deduplication in a 5-minute sliding window
        existing = db.query(AlertFingerprint).filter(
            AlertFingerprint.fingerprint_hash == fingerprint_hash,
            AlertFingerprint.last_alert_time >= five_mins_ago
        ).first()

        if existing:
            existing.alert_count += 1
            existing.last_alert_time = datetime.now(timezone.utc)
            if existing.incident_id:
                incident = db.query(Incident).filter(Incident.id == existing.incident_id).first()
                if incident:
                    incident.alert_count += 1
            db.commit()

            raw_alert = Alert(
                fingerprint_id=existing.id,
                source=source,
                alert_type=alert_type,
                service=service,
                message=message,
                timestamp=datetime.now(timezone.utc)
            )
            db.add(raw_alert)
            db.commit()
            
            logger.info("alert_deduplicated", fingerprint_hash=fingerprint_hash, incident_id=existing.incident_id, count=existing.alert_count)
            return existing.incident_id, False, existing

        # 2. Similarity overlap check (> 85% similarity on the same service in the last 5 minutes)
        recent_fingerprints = db.query(AlertFingerprint).filter(
            AlertFingerprint.last_alert_time >= five_mins_ago
        ).all()

        for fp in recent_fingerprints:
            first_raw_alert = db.query(Alert).filter(Alert.fingerprint_id == fp.id).first()
            if first_raw_alert and first_raw_alert.service.lower() == service.lower():
                similarity = SequenceMatcher(None, first_raw_alert.message.lower(), message.lower()).ratio()
                if similarity >= 0.85:
                    fp.alert_count += 1
                    fp.last_alert_time = datetime.now(timezone.utc)
                    if fp.incident_id:
                        incident = db.query(Incident).filter(Incident.id == fp.incident_id).first()
                        if incident:
                            incident.alert_count += 1
                    db.commit()

                    raw_alert = Alert(
                        fingerprint_id=fp.id,
                        source=source,
                        alert_type=alert_type,
                        service=service,
                        message=message,
                        timestamp=datetime.now(timezone.utc)
                    )
                    db.add(raw_alert)
                    db.commit()
                    
                    logger.info("alert_grouped_by_similarity", similarity=similarity, incident_id=fp.incident_id, count=fp.alert_count)
                    return fp.incident_id, False, fp

        # 3. Completely unique alert: Initialize new fingerprint container
        fp = AlertFingerprint(
            fingerprint_hash=fingerprint_hash,
            first_alert=datetime.now(timezone.utc),
            last_alert_time=datetime.now(timezone.utc),
            alert_count=1
        )
        db.add(fp)
        db.commit()
        db.refresh(fp)

        raw_alert = Alert(
            fingerprint_id=fp.id,
            source=source,
            alert_type=alert_type,
            service=service,
            message=message,
            timestamp=datetime.now(timezone.utc)
        )
        db.add(raw_alert)
        db.commit()

        logger.info("new_alert_fingerprint_created", fingerprint_hash=fingerprint_hash)
        return None, True, fp
