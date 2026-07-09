"""
SentinelFlow AI — Incident Correlation Service
Correlates active incidents using temporal, spatial, causal, and pattern overlap.
Automatically groups cascading incidents under a root-cause primary parent incident.
"""

import json
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from ..models.models import Incident, TimelineEvent, IncidentLog
from ..core.observability import logger
from ..services.websocket_service import broadcast_incident_update

# Simple microservice dependency map
DEPENDENCY_MAP = {
    "notification-service": ["payment-api", "user-service"],
    "frontend": ["payment-api", "catalog-service", "notification-service"],
    "payment-api": ["database", "auth-service", "postgres-db"],
    "catalog-service": ["database", "postgres-db"],
    "auth-service": ["database", "postgres-db"],
    "cache-service": ["database"],
}

class IncidentCorrelationService:
    """Enforces spatial, temporal, and causal correlation scoring across incidents."""

    @staticmethod
    def calculate_correlation_score(inc1: Incident, inc2: Incident) -> float:
        """
        Calculates correlation score between two incidents (0-100 scale).
        """
        score = 0.0

        # 1. Temporal Score (Max 35 pts)
        t1 = inc1.created_at.replace(tzinfo=timezone.utc) if inc1.created_at.tzinfo is None else inc1.created_at
        t2 = inc2.created_at.replace(tzinfo=timezone.utc) if inc2.created_at.tzinfo is None else inc2.created_at
        diff_seconds = abs((t1 - t2).total_seconds())

        if diff_seconds <= 60:
            score += 35
        elif diff_seconds <= 180:
            score += 25
        elif diff_seconds <= 300:
            score += 15

        # 2. Spatial Score (Max 40 pts)
        # Parse titles/details to extract services
        title1 = inc1.title.lower()
        title2 = inc2.title.lower()

        # Shared telemetry parameters
        if inc1.metric_type == inc2.metric_type:
            score += 15

        # Shared pod/node components
        if inc1.description.lower() == inc2.description.lower():
            score += 25
        elif any(term in title1 and term in title2 for term in ["node", "pod", "payment", "database", "auth", "notification"]):
            score += 15

        # 3. Causal Score (Max 30 pts)
        # Check service dependency mapping
        svc1 = None
        svc2 = None
        for key in DEPENDENCY_MAP.keys():
            if key in title1:
                svc1 = key
            if key in title2:
                svc2 = key

        if svc1 and svc2:
            if svc1 in DEPENDENCY_MAP.get(svc2, []) or svc2 in DEPENDENCY_MAP.get(svc1, []):
                score += 30

        # Normalization
        return min(score, 100.0)

    @staticmethod
    def correlate_incident(db: Session, target_incident_id: int) -> Optional[int]:
        """
        Scans active incidents, determines correlation groups, and sets primary root links.
        Returns the root parent incident ID if grouped, otherwise None.
        """
        target = db.query(Incident).filter(Incident.id == target_incident_id).first()
        if not target:
            return None

        # Fetch other active (non-closed) incidents within a 15-minute window
        fifteen_mins_ago = target.created_at - timedelta(minutes=15)
        active_incidents = db.query(Incident).filter(
            Incident.id != target_incident_id,
            Incident.status != "RESOLVED",
            Incident.created_at >= fifteen_mins_ago
        ).all()

        best_root = None
        highest_score = 0.0

        for inc in active_incidents:
            score = IncidentCorrelationService.calculate_correlation_score(target, inc)
            if score >= 70.0 and score > highest_score:
                highest_score = score
                # Root is the one created EARLIER
                best_root = inc if inc.created_at < target.created_at else target

        if best_root and best_root.id != target.id:
            # Set target parent link
            target.parent_incident_id = best_root.id
            db.commit()

            # Record Timeline & Logs for root cause linking
            log_desc = f"Correlated cascading failure: Linked to root cause incident #{best_root.id} (Confidence: {highest_score}%)."
            logger.info("incident_correlated", child_id=target.id, root_id=best_root.id, score=highest_score)

            # Audit logs
            log1 = IncidentLog(
                incident_id=target.id,
                stage="CORRELATION",
                message=log_desc
            )
            log2 = IncidentLog(
                incident_id=best_root.id,
                stage="CORRELATION",
                message=f"Cascading consequence incident #{target.id} linked to this root event."
            )
            db.add_all([log1, log2])

            # Timeline Events
            evt = TimelineEvent(
                incident_id=target.id,
                event_type="CORRELATION_LINK",
                title="Casading Failure Linked to Root Cause",
                description=f"Automated correlation model grouped this failure under root incident #{best_root.id}.",
                actor="correlation-service",
                confidence_at_step=highest_score / 100.0
            )
            db.add(evt)
            db.commit()

            # Send WS alerts
            broadcast_incident_update(target.id, target.status, target.severity)
            broadcast_incident_update(best_root.id, best_root.status, best_root.severity)

            return best_root.id

        return None
