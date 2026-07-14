"""
SentinelFlow AI — Mastra Execution Monitor API
Provides REST endpoints for the Live Mastra Execution Monitor dashboard.
"""

import json
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..middleware.auth import get_current_user
from ..models.models import (
    Incident, MastraWorkflowState, MastraWorkflowStep, TimelineEvent,
)

router = APIRouter(prefix="/monitor", tags=["Mastra Execution Monitor"])


@router.get("/active")
def get_active_execution(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get the most recently active incident with full execution state.
    Includes active incidents OR recently completed ones (last 120s)."""
    active_statuses = ["DETECTED", "ANALYZING", "PENDING_APPROVAL", "APPROVED", "EXECUTING", "BYPASSED"]
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=120)
    incident = (
        db.query(Incident)
        .filter(
            (Incident.status.in_(active_statuses)) |
            (Incident.created_at >= cutoff)
        )
        .order_by(Incident.created_at.desc())
        .first()
    )
    if not incident:
        return {"active": False, "incident": None}

    return _build_execution_response(db, incident)


@router.get("/{incident_id}/execution")
def get_incident_execution(
    incident_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get full execution state for a specific incident."""
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    return _build_execution_response(db, incident)


def _build_execution_response(db: Session, incident: Incident) -> dict:
    """Build the full execution state response for an incident."""

    # Get workflow state
    workflow_state = (
        db.query(MastraWorkflowState)
        .filter(MastraWorkflowState.correlation_id == incident.correlation_id)
        .first()
    )

    # Get workflow steps
    workflow_steps = []
    if workflow_state:
        steps = (
            db.query(MastraWorkflowStep)
            .filter(MastraWorkflowStep.workflow_state_id == workflow_state.id)
            .order_by(MastraWorkflowStep.id.asc())
            .all()
        )
        for s in steps:
            duration = 0.0
            if s.started_at and s.ended_at:
                from datetime import timezone as _tz
                s_naive = s.started_at.replace(tzinfo=None) if s.started_at.tzinfo else s.started_at
                e_naive = s.ended_at.replace(tzinfo=None) if s.ended_at.tzinfo else s.ended_at
                duration = (e_naive - s_naive).total_seconds()
            workflow_steps.append({
                "step_name": s.step_name,
                "status": s.status,
                "started_at": s.started_at.isoformat() if s.started_at else None,
                "ended_at": s.ended_at.isoformat() if s.ended_at else None,
                "duration_seconds": round(duration, 3),
                "error_message": s.error_message,
            })

    # Parse context for agent/provider/safety info
    context = {}
    if workflow_state and workflow_state.context_data_json:
        try:
            context = json.loads(workflow_state.context_data_json)
        except Exception:
            pass

    agent_name = context.get("agent_routed", "")
    agent_sub_type = context.get("agent_sub_type", "")
    agent_domain = context.get("agent_domain", "")
    reasoning_result = context.get("reasoning_result", {})
    if isinstance(reasoning_result, dict):
        ai_provider = reasoning_result.get("provider", "simulation")
        confidence = reasoning_result.get("confidence", 0.0)
    else:
        ai_provider = "simulation"
        confidence = 0.0
    safety_status = context.get("safety_status", "")
    safety_risk = context.get("safety_risk", 0.0)

    # Determine the current step
    current_step_num = 1
    step_name_map = {
        "DETECT_ANOMALY": 1, "RETRIEVE_CONTEXT": 2, "RETRIEVE_RUNBOOKS": 3,
        "PLAN_REMEDIATION": 4, "CONTRADICTION_CHECK": 5, "VALIDATE": 6,
        "APPROVE_DECISION": 7, "EXECUTE_REMEDIATION": 8,
    }
    for s in workflow_steps:
        if s["status"] == "running":
            current_step_num = step_name_map.get(s["step_name"], current_step_num)
            break
        elif s["status"] == "completed":
            current_step_num = step_name_map.get(s["step_name"], current_step_num) + 1

    # Build step labels
    step_labels = {
        "DETECT_ANOMALY": "Anomaly Detection & Agent Selection",
        "RETRIEVE_CONTEXT": "CRISPE Prompt Template Lookup",
        "RETRIEVE_RUNBOOKS": "RAG Knowledge Retrieval",
        "PLAN_REMEDIATION": "LLM Multi-Agent Reasoning",
        "CONTRADICTION_CHECK": "Mastra Contradiction Analysis",
        "VALIDATE": "Enkrypt AI Safety Validation",
        "APPROVE_DECISION": "Confidence Gate & Governance",
        "EXECUTE_REMEDIATION": "Autonomous Remediation Execution",
    }

    pipeline = []
    for i, (skey, slabel) in enumerate(step_labels.items(), 1):
        step_entry = None
        for ws in workflow_steps:
            if ws["step_name"] == skey:
                step_entry = ws
                break
        if step_entry:
            pipeline.append({
                "step_number": i,
                "step_key": skey,
                "label": slabel,
                "status": step_entry["status"],
                "duration_seconds": step_entry["duration_seconds"],
                "error_message": step_entry.get("error_message"),
            })
        else:
            pipeline.append({
                "step_number": i,
                "step_key": skey,
                "label": slabel,
                "status": "pending",
                "duration_seconds": 0.0,
                "error_message": None,
            })

    # Get timeline events
    timeline_events = (
        db.query(TimelineEvent)
        .filter(TimelineEvent.incident_id == incident.id)
        .order_by(TimelineEvent.timestamp.asc())
        .all()
    )
    events = [
        {
            "event_type": te.event_type,
            "title": te.title,
            "description": (te.description or "")[:200],
            "actor": te.actor or "",
            "timestamp": te.timestamp.isoformat() if te.timestamp else None,
            "duration_ms": te.duration_ms,
        }
        for te in timeline_events
    ]

    return {
        "active": incident.status in ["DETECTED", "ANALYZING", "PENDING_APPROVAL", "APPROVED", "EXECUTING"],
        "incident": {
            "id": incident.id,
            "title": incident.title,
            "metric_type": incident.metric_type,
            "severity": incident.severity,
            "status": incident.status,
            "source": incident.source,
            "confidence_score": incident.confidence_score,
            "suggested_action": incident.suggested_action,
            "created_at": incident.created_at.isoformat() if incident.created_at else None,
            "resolved_at": incident.resolved_at.isoformat() if incident.resolved_at else None,
            "root_cause_json": incident.root_cause_json,
            "explainability_json": incident.explainability_json,
            "simulation_json": incident.simulation_json,
            "remediation_options_json": incident.remediation_options_json,
            "recommended_runbooks_json": incident.recommended_runbooks_json,
        },
        "workflow": {
            "name": "IncidentResponseWorkflow",
            "is_completed": workflow_state.is_completed if workflow_state else False,
            "current_step": current_step_num,
            "total_steps": 8,
        },
        "agent": {
            "name": agent_name,
            "sub_type": agent_sub_type,
            "domain": agent_domain,
        },
        "ai_provider": ai_provider,
        "confidence": round(confidence, 3),
        "safety": {
            "status": safety_status,
            "risk_score": round(safety_risk, 3),
        },
        "pipeline": pipeline,
        "timeline_events": events,
    }
