"""
SentinelFlow AI — Mastra Execution Center API Router
Provides REST endpoints for querying active and historical Mastra workflow execution states.
"""

import json
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from ..core.database import get_db
from ..models.models import Incident, MastraWorkflowState, MastraWorkflowStep, TimelineEvent, User
from ..api.router_auth import get_current_user
from ..core.observability import logger

router = APIRouter(prefix="/mastra", tags=["mastra"])

STEP_KEYS = [
    "DETECT_ANOMALY",
    "RETRIEVE_CONTEXT",
    "RETRIEVE_RUNBOOKS",
    "PLAN_REMEDIATION",
    "CONTRADICTION_CHECK",
    "VALIDATE",
    "APPROVE_DECISION",
    "EXECUTE_REMEDIATION"
]

STEP_LABELS: Dict[str, str] = {
    "DETECT_ANOMALY": "Anomaly Detection & Agent Selection",
    "RETRIEVE_CONTEXT": "CRISPE Prompt Template Lookup",
    "RETRIEVE_RUNBOOKS": "RAG Knowledge Retrieval",
    "PLAN_REMEDIATION": "LLM Multi-Agent Reasoning",
    "CONTRADICTION_CHECK": "Mastra Contradiction Analysis",
    "VALIDATE": "Enkrypt AI Safety Validation",
    "APPROVE_DECISION": "Confidence Gate & Governance",
    "EXECUTE_REMEDIATION": "Autonomous Remediation Execution",
}

def _build_execution_payload(db: Session, incident: Incident) -> Dict[str, Any]:
    """Helper to assemble a complete Mastra execution payload for an incident."""
    wf_state = None
    if incident.correlation_id:
        wf_state = db.query(MastraWorkflowState).filter(
            MastraWorkflowState.correlation_id == incident.correlation_id
        ).first()

    steps = []
    if wf_state:
        steps = db.query(MastraWorkflowStep).filter(
            MastraWorkflowStep.workflow_state_id == wf_state.id
        ).order_by(MastraWorkflowStep.id.asc()).all()

    # Parse context JSON
    context = {}
    if wf_state and wf_state.context_data_json:
        try:
            context = json.loads(wf_state.context_data_json)
        except Exception:
            context = {}

    # Build 8-step pipeline
    pipeline = []
    step_dict = {s.step_name: s for s in steps}

    for idx, key in enumerate(STEP_KEYS, start=1):
        step_obj = step_dict.get(key)
        status = "pending"
        duration_sec = 0.0
        error_msg = None

        if step_obj:
            status = step_obj.status
            error_msg = step_obj.error_message
            if step_obj.started_at and step_obj.ended_at:
                s_naive = step_obj.started_at.replace(tzinfo=None)
                e_naive = step_obj.ended_at.replace(tzinfo=None)
                duration_sec = round((e_naive - s_naive).total_seconds(), 2)
        elif wf_state and wf_state.is_completed:
            status = "completed"
        elif idx == 1 and incident:
            status = "completed"

        pipeline.append({
            "step_number": idx,
            "step_key": key,
            "label": STEP_LABELS.get(key, key),
            "status": status,
            "duration_seconds": duration_sec,
            "error_message": error_msg,
        })

    # Timeline events
    timeline_events = []
    t_events = db.query(TimelineEvent).filter(
        TimelineEvent.incident_id == incident.id
    ).order_by(TimelineEvent.timestamp.asc()).all()

    for te in t_events:
        timeline_events.append({
            "id": te.id,
            "event_type": te.event_type,
            "title": te.title,
            "description": te.description,
            "actor": te.actor,
            "decision_rationale": te.decision_rationale,
            "timestamp": te.timestamp.isoformat() if te.timestamp else datetime.now(timezone.utc).isoformat(),
        })

    # Agent routing metadata
    agent_name = context.get("agent_routed") or "K8s SecOps Agent"
    agent_sub_type = context.get("agent_sub_type") or "sre_remediation"
    agent_domain = context.get("agent_domain") or "infrastructure"

    # Remediation options
    remediation_options = []
    if incident.remediation_options_json:
        try:
            remediation_options = json.loads(incident.remediation_options_json)
        except Exception:
            remediation_options = []

    # Root cause analysis
    rca = {}
    if incident.root_cause_json:
        try:
            rca = json.loads(incident.root_cause_json)
        except Exception:
            rca = {}

    is_active = incident.status in ["DETECTED", "ANALYZING", "PENDING_APPROVAL", "APPROVED", "EXECUTING"]

    return {
        "active": is_active,
        "incident": {
            "id": incident.id,
            "title": incident.title,
            "metric_type": incident.metric_type,
            "severity": incident.severity or "MEDIUM",
            "status": incident.status,
            "suggested_action": incident.suggested_action or "",
            "description": incident.description or "",
            "correlation_id": incident.correlation_id or "",
            "is_simulated": incident.is_simulated or False,
            "simulation_reason": incident.simulation_reason or "",
            "remediation_options_json": incident.remediation_options_json or "[]",
            "root_cause_json": incident.root_cause_json or "{}",
            "created_at": incident.created_at.isoformat() if incident.created_at else datetime.now(timezone.utc).isoformat(),
        },
        "workflow": {
            "name": wf_state.workflow_name if wf_state else "IncidentResponseWorkflow",
            "is_completed": wf_state.is_completed if wf_state else (incident.status in ["EXECUTED", "RESOLVED"]),
            "current_step": len([p for p in pipeline if p["status"] == "completed"]),
            "total_steps": 8,
        },
        "agent": {
            "name": agent_name,
            "sub_type": agent_sub_type,
            "domain": agent_domain,
        },
        "ai_provider": "Gemini 2.5 Flash (Primary)" if not incident.is_simulated else "Simulated AI Engine",
        "confidence": incident.confidence_score or 0.85,
        "safety": {
            "status": "APPROVED" if incident.status != "REJECTED" else "BLOCKED",
            "risk_score": 12.0 if incident.status != "REJECTED" else 95.0,
        },
        "pipeline": pipeline,
        "timeline_events": timeline_events,
        "remediation_options": remediation_options,
        "rca": rca,
    }


@router.get("/execution/active")
def get_active_execution(db: Session = Depends(get_db)):
    """Get current active Mastra workflow execution or latest incident."""
    active_incident = db.query(Incident).filter(
        Incident.status.in_(["DETECTED", "ANALYZING", "PENDING_APPROVAL", "APPROVED", "EXECUTING"])
    ).order_by(Incident.id.desc()).first()

    if not active_incident:
        # If no active incident, fall back to most recent incident
        active_incident = db.query(Incident).order_by(Incident.id.desc()).first()

    if not active_incident:
        return {
            "active": False,
            "message": "No incidents currently active or found in database.",
            "incident": None,
            "workflow": None,
            "pipeline": [],
        }

    return _build_execution_payload(db, active_incident)


@router.get("/execution/{incident_id}")
def get_incident_execution(incident_id: int, db: Session = Depends(get_db)):
    """Get Mastra workflow execution details for a specific incident ID."""
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail=f"Incident #{incident_id} not found.")

    return _build_execution_payload(db, incident)
