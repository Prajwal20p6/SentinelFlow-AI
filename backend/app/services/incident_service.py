"""
SentinelFlow AI — Incident Management Service
Full CRUD operations, status lifecycle, and workflow integration.
"""

import json
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

from ..core.security import generate_correlation_id
from ..core.vector_db import add_resolution_to_qdrant
from ..models.models import Incident, IncidentLog, TimelineEvent, IncidentComment


# ── Status Machine ───────────────────────────────────────────
VALID_TRANSITIONS = {
    "DETECTED": ["ANALYZING"],
    "ANALYZING": ["PENDING_APPROVAL", "BYPASSED"],
    "PENDING_APPROVAL": ["APPROVED", "REJECTED"],
    "APPROVED": ["EXECUTING"],
    "EXECUTING": ["EXECUTED"],
    "EXECUTED": [],  # Terminal state
    "REJECTED": [],  # Terminal state
    "BYPASSED": ["EXECUTING", "EXECUTED"],  # Auto-pilot path
}


def create_incident(
    db: Session,
    source: str,
    metric_type: str,
    severity: str,
    title: str,
    description: str,
    confidence_score: float = 0.0,
    suggested_action: Optional[str] = None,
    correlation_id: Optional[str] = None,
) -> Incident:
    """Create a new incident with a unique correlation ID."""
    from .prioritization_agent import IncidentPrioritizationAgent
    pri_data = IncidentPrioritizationAgent.calculate_priority(
        metric_type=metric_type,
        severity=severity,
        description=description
    )

    incident = Incident(
        correlation_id=correlation_id or generate_correlation_id(),
        source=source,
        metric_type=metric_type,
        severity=severity,
        title=title,
        description=description,
        status="DETECTED",
        confidence_score=confidence_score,
        suggested_action=suggested_action,
        priority_score=pri_data["score"],
        sla_target=pri_data["sla_target"],
        sla_breach_at=pri_data["sla_breach_at"]
    )
    db.add(incident)
    db.commit()
    db.refresh(incident)

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

    from ..core.observability import track_incident_created
    track_incident_created(severity, "DETECTED", metric_type)

    # Add initial timeline event
    add_timeline_event(
        db, incident.id, "DETECTED",
        f"Incident detected: {title}",
        f"Source: {source}, Type: {metric_type}, Severity: {severity}",
        actor="system",
    )

    return incident


def get_incident(db: Session, incident_id: int) -> Optional[Incident]:
    """Get an incident by ID."""
    return db.query(Incident).filter(Incident.id == incident_id).first()


def get_incident_by_correlation(db: Session, correlation_id: str) -> Optional[Incident]:
    """Get an incident by correlation ID."""
    return db.query(Incident).filter(Incident.correlation_id == correlation_id).first()


def list_incidents(
    db: Session,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[Incident], int]:
    """List incidents with optional filtering and pagination."""
    query = db.query(Incident)

    if status:
        query = query.filter(Incident.status == status)
    if severity:
        query = query.filter(Incident.severity == severity)

    total = query.count()
    incidents = (
        query.order_by(desc(Incident.created_at))
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    return incidents, total


def update_incident_status(
    db: Session,
    incident_id: int,
    new_status: str,
    actor: str = "system",
    reason: Optional[str] = None,
) -> Incident:
    """Update incident status with lifecycle validation through StateMachineService."""
    from .state_machine_service import StateMachineService
    incident = StateMachineService.transition_status(db, incident_id, new_status, actor, reason)

    if incident.resolved_at:
        try:
            from .memory_service import sync_resolved_incident_to_org_memory
            sync_resolved_incident_to_org_memory(db, incident.id)
        except Exception as sync_err:
            logger.warning("org_memory_sync_failed", error=str(sync_err))

    # Sync resolved incidents to vector DB for future RAG
    if new_status in ("EXECUTED", "RESOLVED") and incident.suggested_action:
        add_resolution_to_qdrant(
            incident.id,
            incident.title,
            f"{incident.description}. Resolution: {incident.suggested_action}",
            [incident.metric_type.lower()],
            category="resolved",
        )

    return incident


def add_incident_log(
    db: Session,
    incident_id: int,
    stage: str,
    message: str,
    metadata: Optional[dict] = None,
) -> IncidentLog:
    """Add a processing log entry to an incident."""
    log = IncidentLog(
        incident_id=incident_id,
        stage=stage,
        message=message,
        metadata_json=json.dumps(metadata) if metadata else None,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def add_timeline_event(
    db: Session,
    incident_id: int,
    event_type: str,
    title: str,
    description: Optional[str] = None,
    actor: str = "system",
    decision_rationale: Optional[str] = None,
    confidence_at_step: Optional[float] = None,
    duration_ms: Optional[float] = None,
    mitre_technique: Optional[str] = None,
    source_system: Optional[str] = None,
    event_severity: Optional[str] = None,
    parent_event_id: Optional[int] = None,
) -> TimelineEvent:
    """Add a timeline event for incident explainability, auto-mapping to MITRE and parent causality links."""
    
    # Auto-resolve parent event id to build causal chain
    if not parent_event_id:
        last_evt = db.query(TimelineEvent).filter(
            TimelineEvent.incident_id == incident_id
        ).order_by(TimelineEvent.id.desc()).first()
        if last_evt:
            parent_event_id = last_evt.id

    # Auto-map mitre technique based on incident type
    if not mitre_technique:
        incident = db.query(Incident).filter(Incident.id == incident_id).first()
        if incident:
            from .mitre_service import map_incident_to_mitre
            mitre_technique = map_incident_to_mitre(incident.metric_type)

    if not source_system:
        source_system = "SentinelFlowEngine"

    if not event_severity:
        incident = db.query(Incident).filter(Incident.id == incident_id).first()
        event_severity = incident.severity.upper() if (incident and incident.severity) else "MEDIUM"

    event = TimelineEvent(
        incident_id=incident_id,
        event_type=event_type,
        title=title,
        description=description,
        actor=actor,
        decision_rationale=decision_rationale,
        confidence_at_step=confidence_at_step,
        duration_ms=duration_ms,
        mitre_technique=mitre_technique,
        source_system=source_system,
        event_severity=event_severity,
        parent_event_id=parent_event_id,
    )
    db.add(event)
    db.commit()
    db.refresh(event)

    try:
        from .websocket_service import broadcast_timeline_event
        broadcast_timeline_event(
            incident_id=incident_id,
            event_type=event_type,
            title=title
        )
    except Exception:
        pass

    if event_type == "HITL_REQUESTED":
        try:
            from .websocket_service import broadcast_approval_request
            broadcast_approval_request(
                approval_id=event.id,
                incident_id=incident_id,
                decision_required_by="admin"
            )
        except Exception:
            pass

    return event


def add_incident_comment(
    db: Session,
    incident_id: int,
    author: str,
    content: str,
) -> IncidentComment:
    """Add a new comment/note to an incident."""
    comment = IncidentComment(
        incident_id=incident_id,
        author=author,
        content=content,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)

    # Add timeline event for comment creation
    add_timeline_event(
        db, incident_id, "COMMENT_ADDED",
        f"Comment added by {author}",
        content[:100] + ("..." if len(content) > 100 else ""),
        actor=author,
    )

    return comment


def get_incident_comments(db: Session, incident_id: int) -> list[IncidentComment]:
    """Get all comments associated with an incident."""
    return (
        db.query(IncidentComment)
        .filter(IncidentComment.incident_id == incident_id)
        .order_by(IncidentComment.created_at.asc())
        .all()
    )

