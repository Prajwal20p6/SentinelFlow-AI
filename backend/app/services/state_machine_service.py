"""
SentinelFlow AI — Incident State Machine with Atomic Transitions
Provides transactional locking and enforces preconditions for incident status changes.
"""

from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy.orm import Session
from ..models.models import Incident, TimelineEvent, IncidentLog
from ..core.observability import logger

VALID_TRANSITIONS = {
    "DETECTED": ["ANALYZING", "ESCALATED"],
    "ANALYZING": ["PLANNED", "PENDING_APPROVAL", "BYPASSED", "ESCALATED", "REJECTED"],
    "PLANNED": ["PENDING_APPROVAL", "ESCALATED"],
    "PENDING_APPROVAL": ["APPROVED", "REJECTED", "ESCALATED"],
    "APPROVED": ["EXECUTING", "ESCALATED"],
    "EXECUTING": ["EXECUTED", "RESOLVED", "ESCALATED"],
    "ESCALATED": ["RESOLVED", "EXECUTED", "REJECTED"],
    "BYPASSED": ["EXECUTING", "EXECUTED"],
    "EXECUTED": [],
    "REJECTED": [],
    "RESOLVED": [],
}

class StateMachineService:
    """Enforces atomic transitions with SELECT FOR UPDATE locks and precondition checks."""

    @staticmethod
    def transition_status(
        db: Session,
        incident_id: int,
        new_status: str,
        actor: str = "system",
        reason: Optional[str] = None
    ) -> Incident:
        """
        Atomically queries an incident, validates preconditions, and updates its status.
        Uses SELECT FOR UPDATE for PostgreSQL (row-level isolation) and database lock emulation.
        """
        # Query with pessimistic write lock
        incident = db.query(Incident).filter(Incident.id == incident_id).with_for_update().first()
        if not incident:
            raise ValueError(f"Incident {incident_id} not found")

        current_status = incident.status or "DETECTED"
        
        # 1. Any -> ESCALATED path check
        if new_status == "ESCALATED":
            # Allowed from any non-terminal state
            if current_status in ["EXECUTED", "REJECTED", "RESOLVED"]:
                raise ValueError(f"Cannot escalate a resolved incident (current state: {current_status})")
        else:
            # 2. Check transition limits
            allowed = VALID_TRANSITIONS.get(current_status, [])
            if new_status not in allowed:
                raise ValueError(
                    f"Invalid state transition: {current_status} → {new_status}. "
                    f"Allowed next states: {allowed}"
                )

        # 3. Check Preconditions
        # Precondition A: ANALYZING → PLANNED / PENDING_APPROVAL requires RCA complete
        if current_status == "ANALYZING" and new_status in ("PLANNED", "PENDING_APPROVAL"):
            if not incident.root_cause_json:
                raise ValueError("Precondition failed: Root Cause Analysis (RCA) must be complete before planning remediation.")

        # Precondition B: PLANNED → PENDING_APPROVAL requires remediation selected
        if current_status == "PLANNED" and new_status == "PENDING_APPROVAL":
            if not incident.suggested_action:
                raise ValueError("Precondition failed: A suggested remediation command must be defined before requesting approval.")

        # Precondition C: PENDING_APPROVAL → APPROVED/EXECUTING requires approval (handled by SRE route authorization check)
        
        # 4. Perform Transition
        incident.status = new_status
        incident.updated_at = datetime.now(timezone.utc)

        if new_status in ("EXECUTED", "REJECTED", "RESOLVED"):
            incident.resolved_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(incident)

        logger.info(
            "incident_state_transitioned",
            incident_id=incident.id,
            old_status=current_status,
            new_status=new_status,
            actor=actor
        )

        # Add history audit log
        log_entry = IncidentLog(
            incident_id=incident.id,
            stage="STATE_TRANSITION",
            message=f"Transitioned status from {current_status} to {new_status}. Actor: {actor}. Reason: {reason or 'none'}."
        )
        db.add(log_entry)

        # Add Timeline event
        timeline_evt = TimelineEvent(
            incident_id=incident.id,
            event_type="STATUS_CHANGED",
            title=f"Incident status changed to {new_status}",
            description=reason or f"State transitioned to {new_status} by {actor}.",
            actor=actor
        )
        db.add(timeline_evt)
        db.commit()

        # Try triggering WebSocket updates
        try:
            from .websocket_service import broadcast_incident_update
            broadcast_incident_update(
                incident_id=incident.id,
                status=incident.status,
                severity=incident.severity,
                service=incident.source
            )
        except Exception:
            pass

        return incident
