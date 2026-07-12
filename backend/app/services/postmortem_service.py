"""
SentinelFlow AI — Postmortem Generation Service
Automatically generates comprehensive postmortem reports after incident resolution.
"""

import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from ..core.observability import logger
from ..models.models import Incident, IncidentLog, TimelineEvent, AuditTrail


def generate_postmortem(db: Session, incident_id: int) -> Dict[str, Any]:
    """
    Generate a comprehensive postmortem report for a resolved incident.
    Includes timeline, root cause analysis, impact assessment, and action items.
    """
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise ValueError(f"Incident {incident_id} not found")
    
    # Gather incident data
    logs = db.query(IncidentLog).filter(IncidentLog.incident_id == incident_id).order_by(IncidentLog.created_at.asc()).all()
    timeline = db.query(TimelineEvent).filter(TimelineEvent.incident_id == incident_id).order_by(TimelineEvent.timestamp.asc()).all()
    audits = db.query(AuditTrail).filter(AuditTrail.incident_id == incident_id).order_by(AuditTrail.timestamp.asc()).all()
    
    # Calculate duration
    start_time = incident.created_at
    end_time = incident.resolved_at or datetime.now(timezone.utc)
    duration = (end_time - start_time).total_seconds() if start_time else 0
    
    # Extract root cause
    root_cause = "Unknown"
    if incident.root_cause_json:
        try:
            rca_data = json.loads(incident.root_cause_json)
            root_cause = rca_data.get("root_cause", rca_data.get("primary_cause", "Unknown"))
        except Exception:
            root_cause = incident.root_cause_json[:200]
    
    # Build timeline summary
    timeline_summary = []
    for event in timeline:
        timeline_summary.append({
            "timestamp": event.timestamp.isoformat() if event.timestamp else None,
            "event_type": event.event_type,
            "description": event.description,
            "actor": event.actor,
            "decision_rationale": event.decision_rationale
        })
    
    # Build action items from logs
    action_items = []
    for log in logs:
        if log.stage in ["REASONING", "REMEDIATION", "EXECUTION"]:
            action_items.append({
                "stage": log.stage,
                "message": log.message,
                "timestamp": log.created_at.isoformat() if log.created_at else None
            })
    
    # Build audit trail summary
    audit_summary = []
    for audit in audits:
        audit_summary.append({
            "command": audit.command_checked,
            "status": audit.status,
            "risk_score": audit.risk_score,
            "timestamp": audit.timestamp.isoformat() if audit.timestamp else None
        })
    
    # Generate executive summary
    executive_summary = f"""
Incident #{incident.id}: {incident.title}
Severity: {incident.severity}
Duration: {duration:.0f} seconds ({duration/60:.1f} minutes)
Root Cause: {root_cause}
Resolution: {incident.suggested_action or 'No action specified'}
Status: {incident.status}
"""
    
    # Generate technical summary
    technical_summary = {
        "incident_id": incident.id,
        "correlation_id": incident.correlation_id,
        "metric_type": incident.metric_type,
        "severity": incident.severity,
        "confidence_score": incident.confidence_score,
        "priority_score": incident.priority_score,
        "sla_target": incident.sla_target,
        "duration_seconds": duration,
        "timeline_events": len(timeline),
        "audit_entries": len(audits),
        "action_items": len(action_items)
    }
    
    # Generate recommendations
    recommendations = []
    if "CPU" in incident.metric_type:
        recommendations.append("Review HPA autoscaling configuration")
        recommendations.append("Investigate resource limits and requests")
    elif "MEMORY" in incident.metric_type:
        recommendations.append("Profile application for memory leaks")
        recommendations.append("Consider increasing memory limits")
    elif "DISK" in incident.metric_type:
        recommendations.append("Implement log rotation policies")
        recommendations.append("Set up disk usage monitoring alerts")
    elif "UNAUTHORIZED" in incident.metric_type:
        recommendations.append("Review RBAC policies")
        recommendations.append("Implement network policies")
        recommendations.append("Enable audit logging")
    
    postmortem = {
        "incident_id": incident_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "executive_summary": executive_summary.strip(),
        "technical_summary": technical_summary,
        "timeline": timeline_summary,
        "action_items": action_items,
        "audit_trail": audit_summary,
        "root_cause": root_cause,
        "resolution": incident.suggested_action,
        "recommendations": recommendations,
        "metadata": {
            "similar_incidents": [],  # Could be populated by searching similar incidents
            "affected_services": [incident.source],
            "business_impact": "Medium" if incident.severity == "WARNING" else "High"
        }
    }
    
    # Store postmortem in incident
    incident.postmortem_json = json.dumps(postmortem)
    db.commit()
    
    logger.info("postmortem_generated", incident_id=incident_id, duration_seconds=duration)
    
    return postmortem


def get_postmortem(db: Session, incident_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve existing postmortem for an incident."""
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident or not incident.postmortem_json:
        return None
    
    try:
        return json.loads(incident.postmortem_json)
    except Exception:
        return None
