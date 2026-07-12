"""
SentinelFlow AI — Incident Management API Router
CRUD operations, status transitions, timeline, and explainability.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from ..core.database import get_db
from ..middleware.auth import get_current_user, require_role
from ..models.models import User, Incident
from ..schemas.schemas import (
    IncidentResponse, IncidentDetailResponse, IncidentStatusUpdate,
    IncidentListResponse, IncidentLogResponse, TimelineEventResponse,
    CommentCreate, CommentResponse, FeedbackCreateRequest, FeedbackResponse,
    RunbookFeedbackRequest, ExecuteRemediationRequest,
)
from ..services.incident_service import (
    get_incident, list_incidents, update_incident_status,
    add_incident_comment, get_incident_comments,
)

router = APIRouter(prefix="/incidents", tags=["Incidents"])


@router.get("", response_model=IncidentListResponse)
def list_all_incidents(
    status: Optional[str] = Query(None, description="Filter by status"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all incidents with optional filtering and pagination."""
    incidents, total = list_incidents(db, status=status, severity=severity, page=page, per_page=per_page)
    return IncidentListResponse(
        incidents=[IncidentResponse.model_validate(i) for i in incidents],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/stats/analytics")
def get_incident_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get metrics and analytics including MTTR, resolution rate, and severities."""
    total_count = db.query(Incident).count()
    if total_count == 0:
        return {
            "total_count": 0,
            "resolved_count": 0,
            "resolution_rate": 0.0,
            "mttr_seconds": 0.0,
            "by_severity": {},
            "by_status": {},
        }

    # Counts by severity
    by_severity = {}
    for severity in ["CRITICAL", "WARNING", "INFO"]:
        by_severity[severity] = db.query(Incident).filter(Incident.severity == severity).count()

    # Counts by status
    statuses = ["DETECTED", "ANALYZING", "PENDING_APPROVAL", "APPROVED", "EXECUTING", "EXECUTED", "REJECTED", "BYPASSED"]
    by_status = {}
    for status in statuses:
        by_status[status] = db.query(Incident).filter(Incident.status == status).count()

    # Resolved count
    resolved_incidents = db.query(Incident).filter(Incident.resolved_at.isnot(None)).all()
    resolved_count = len(resolved_incidents)
    resolution_rate = (resolved_count / total_count) * 100.0

    # Calculate MTTR (Mean Time to Resolution)
    mttr_seconds = 0.0
    if resolved_count > 0:
        durations = []
        for inc in resolved_incidents:
            if inc.resolved_at and inc.created_at:
                durations.append((inc.resolved_at - inc.created_at).total_seconds())
        if durations:
            import numpy as np
            mttr_seconds = float(np.mean(durations))

    return {
        "total_count": total_count,
        "resolved_count": resolved_count,
        "resolution_rate": round(resolution_rate, 2),
        "mttr_seconds": round(mttr_seconds, 2),
        "by_severity": by_severity,
        "by_status": by_status,
    }


@router.get("/{incident_id}", response_model=IncidentDetailResponse)
def get_incident_detail(
    incident_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get detailed incident information including logs and timeline."""
    incident = get_incident(db, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    from ..schemas.schemas import AlertFingerprintResponse
    return IncidentDetailResponse(
        **{c.key: getattr(incident, c.key) for c in incident.__table__.columns},
        logs=[IncidentLogResponse.model_validate(log) for log in incident.logs],
        timeline_events=[TimelineEventResponse.model_validate(evt) for evt in incident.timeline_events],
        fingerprints=[AlertFingerprintResponse.model_validate(fp) for fp in incident.fingerprints],
    )


@router.patch("/{incident_id}/status")
def update_status(
    incident_id: int,
    body: IncidentStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("engineer")),
):
    """Update incident status. Requires engineer or admin role."""
    try:
        incident = update_incident_status(
            db, incident_id, body.status,
            actor=current_user.email,
            reason=body.reason,
        )
        return IncidentResponse.model_validate(incident)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{incident_id}/approve")
def approve_incident(
    incident_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("engineer")),
):
    """Approve an incident for execution (HITL approval)."""
    try:
        incident = update_incident_status(
            db, incident_id, "APPROVED",
            actor=current_user.email,
            reason="Human-in-the-loop approval",
        )
        # Auto-transition to EXECUTING
        incident = update_incident_status(db, incident_id, "EXECUTING", actor="workflow")
        
        # Execute the suggested command via safety gate
        if incident.suggested_action:
            from ..services.safety_service import execute_guarded_command
            execute_guarded_command(
                db=db,
                command=incident.suggested_action,
                incident_id=incident.id,
                performed_by=current_user.email,
            )
            
        incident = update_incident_status(db, incident_id, "EXECUTED", actor="executor")
        return {"message": "Incident approved and executed.", "incident": IncidentResponse.model_validate(incident)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{incident_id}/reject")
def reject_incident(
    incident_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("engineer")),
):
    """Reject an incident (HITL rejection)."""
    try:
        incident = update_incident_status(
            db, incident_id, "REJECTED",
            actor=current_user.email,
            reason="Human-in-the-loop rejection",
        )
        return {"message": "Incident rejected.", "incident": IncidentResponse.model_validate(incident)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{incident_id}/comments", response_model=list[CommentResponse])
def get_comments(
    incident_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all comments/notes for an incident."""
    incident = get_incident(db, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    comments = get_incident_comments(db, incident_id)
    return [CommentResponse.model_validate(c) for c in comments]


@router.post("/{incident_id}/comments", response_model=CommentResponse, status_code=201)
def create_comment(
    incident_id: int,
    body: CommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a new comment/note to an incident."""
    incident = get_incident(db, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    comment = add_incident_comment(
        db=db,
        incident_id=incident_id,
        author=current_user.email,
        content=body.content,
    )
    return CommentResponse.model_validate(comment)


@router.get("/{incident_id}/postmortem")
def get_postmortem(
    incident_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve the postmortem report for a resolved incident."""
    from ..services.postmortem_service import get_postmortem, generate_postmortem
    
    incident = get_incident(db, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    # Generate postmortem if not exists and incident is resolved
    postmortem = get_postmortem(db, incident_id)
    if not postmortem and incident.status in ["EXECUTED", "RESOLVED"]:
        postmortem = generate_postmortem(db, incident_id)
    
    if not postmortem:
        raise HTTPException(status_code=404, detail="Postmortem not available. Incident must be resolved first.")
    
    return postmortem


@router.post("/{incident_id}/postmortem/generate")
def generate_postmortem_endpoint(
    incident_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("engineer")),
):
    """Manually trigger postmortem generation for an incident."""
    from ..services.postmortem_service import generate_postmortem
    
    incident = get_incident(db, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    postmortem = generate_postmortem(db, incident_id)
    return {
        "status": "success",
        "incident_id": incident_id,
        "postmortem": postmortem
    }


@router.get("/{incident_id}/timeline")
def get_timeline(
    incident_id: int,
    event_type: Optional[str] = None,
    format: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve event-sourced timeline logs for an incident with optional MITRE causal format."""
    incident = get_incident(db, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    from ..services.timeline_service import get_incident_timeline
    events = get_incident_timeline(db, incident_id, event_type=event_type)

    from ..services.mitre_service import (
        build_causal_timeline,
        build_kill_chain_timeline,
        analyze_timeline_forensics,
        lookup_mitre_technique
    )

    def serialize_event(e):
        tech = lookup_mitre_technique(e.mitre_technique) if e.mitre_technique else None
        return {
            "id": e.id,
            "event_type": e.event_type,
            "title": e.title,
            "description": e.description,
            "actor": e.actor,
            "decision_rationale": e.decision_rationale,
            "confidence_at_step": e.confidence_at_step,
            "duration_ms": e.duration_ms,
            "mitre_technique": e.mitre_technique,
            "mitre_details": tech,
            "source_system": e.source_system,
            "event_severity": e.event_severity,
            "parent_event_id": e.parent_event_id,
            "timestamp": e.timestamp.isoformat() if e.timestamp else None
        }

    if format == "causal":
        sorted_events = build_causal_timeline(events)
        return [serialize_event(e) for e in sorted_events]
    elif format == "kill_chain":
        return build_kill_chain_timeline(events)
    elif format == "full":
        chronological_serialized = [serialize_event(e) for e in events]
        causal_serialized = [serialize_event(e) for e in build_causal_timeline(events)]
        kill_chain_grouped = build_kill_chain_timeline(events)
        forensics_analysis = analyze_timeline_forensics(events)
        return {
            "chronological": chronological_serialized,
            "causal": causal_serialized,
            "kill_chain": kill_chain_grouped,
            "forensics": forensics_analysis
        }

    return [serialize_event(e) for e in events]


@router.post("/{incident_id}/timeline/simulate-phishing", status_code=201)
def simulate_phishing_scenario(
    incident_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Seed and simulate a full E2E phishing attack scenario with MITRE mappings."""
    from ..services.mitre_service import seed_phishing_scenario
    events = seed_phishing_scenario(db, incident_id)
    return {"status": "seeded", "event_count": len(events)}


@router.get("/{incident_id}/forensics")
def get_forensics(
    incident_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve complete forensics reconstruction audit logs for an incident."""
    from ..services.timeline_service import reconstruct_incident_forensics
    data = reconstruct_incident_forensics(db, incident_id)
    if "error" in data:
        raise HTTPException(status_code=404, detail=data["error"])
    return data


@router.post("/{incident_id}/feedback", response_model=FeedbackResponse, status_code=201)
def submit_recommendation_feedback(
    incident_id: int,
    body: FeedbackCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("engineer")),
):
    """Submit engineer correction/feedback for incident suggested action recommendation."""
    from ..models.models import RecommendationFeedback
    incident = get_incident(db, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    # Override suggestion action to enable executing corrected command
    incident.suggested_action = body.engineer_correction
    
    feedback = RecommendationFeedback(
        incident_id=incident_id,
        original_recommendation=body.original_recommendation,
        engineer_correction=body.engineer_correction,
        reasoning=body.reasoning
    )
    db.add(feedback)
    
    # Log correction event on timeline
    from ..services.incident_service import add_timeline_event
    add_timeline_event(
        db, incident_id, "RECOMMENDATION_CORRECTED",
        "AI suggested action corrected by engineer",
        f"Corrected `{body.original_recommendation}` -> `{body.engineer_correction}`. Reasoning: {body.reasoning or 'None'}",
        actor=current_user.email
    )
    db.commit()
    db.refresh(feedback)
    return feedback


@router.get("/{incident_id}/executive-report")
def get_executive_report(
    incident_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve or generate the high-level executive report for an incident."""
    incident = get_incident(db, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    from ..services.executive_service import generate_executive_summary
    return generate_executive_summary(db, incident)


@router.get("/{incident_id}/simulation")
def get_incident_simulation(
    incident_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get predicted downtime and what-if simulation parameters."""
    incident = get_incident(db, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    import json
    if incident.simulation_json:
        return json.loads(incident.simulation_json)
        
    from ..services.simulation_service import SimulationEngine
    action = incident.suggested_action or "kubectl rollout restart deployment/generic-service"
    sim = SimulationEngine.simulate(action, incident.metric_type)
    return sim


@router.get("/{incident_id}/remediation-options")
def get_incident_remediation_options(
    incident_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve ranked remediation repair candidates generated by RemediationAgent."""
    incident = get_incident(db, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
        
    import json
    if incident.remediation_options_json:
        return json.loads(incident.remediation_options_json)
        
    from ..services.remediation_agent import RemediationAgent
    rem_agent = RemediationAgent()
    options = rem_agent.rank_options(
        anomaly_type=incident.metric_type,
        pod_name="payment-gateway-9f7d2e4a1",
        deployment_name="payment-gateway"
    )
    return options


@router.get("/{incident_id}/replay")
def get_incident_replay(
    incident_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get chronological events for incident replay mode."""
    from ..services.replay_service import IncidentReplayEngine
    return IncidentReplayEngine.get_replay_stream(db, incident_id)


@router.get("/{incident_id}/decision-graph")
def get_incident_decision_graph(
    incident_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve Direct Acyclic Graph representation of AI decision paths."""
    incident = get_incident(db, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
        
    import json
    if incident.decision_graph_json:
        return json.loads(incident.decision_graph_json)
        
    from ..services.decision_graph_service import DecisionGraphService
    graph = DecisionGraphService.build_graph(incident, db)
    return graph


@router.get("/{incident_id}/runbooks")
def get_incident_runbooks(
    incident_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get intelligently recommended runbooks matched to symptoms."""
    incident = get_incident(db, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
        
    import json
    if incident.recommended_runbooks_json:
        return json.loads(incident.recommended_runbooks_json)
        
    from ..services.runbook_recommendation_service import RunbookRecommendationService
    runbooks = RunbookRecommendationService.get_recommendations(
        anomaly_type=incident.metric_type,
        root_cause=incident.title,
        severity=incident.severity
    )
    return runbooks


@router.get("/{incident_id}/attack-graph")
def get_incident_attack_graph(
    incident_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve node-edge graph representation of lateral compromise flows."""
    incident = get_incident(db, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
        
    import json
    if incident.attack_graph_json:
        return json.loads(incident.attack_graph_json)
        
    from ..services.attack_graph_service import AttackGraphService
    graph = AttackGraphService.generate_attack_graph(incident.metric_type, incident.severity)
    return graph


@router.post("/{incident_id}/execute-remediation")
async def execute_remediation_option(
    incident_id: int,
    body: ExecuteRemediationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("engineer")),
):
    """Execute selected ranked option with official Enkrypt AI validation."""
    incident = get_incident(db, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
        
    import json
    options = []
    if incident.remediation_options_json:
        options = json.loads(incident.remediation_options_json)
        
    selected_option = next((o for o in options if o["id"] == body.option_id), None)
    if not selected_option:
        raise HTTPException(status_code=400, detail="Invalid remediation option selected")

    command = selected_option["command"]

    from ..core.config import get_settings
    settings = get_settings()

    if settings.ENKRYPTAI_ENABLED:
        from ..services.enkrypt_service import EnkryptSafetyService
        enkrypt = EnkryptSafetyService(
            api_key=settings.ENKRYPTAI_API_KEY,
            base_url=settings.ENKRYPTAI_BASE_URL
        )
        try:
            validation = await enkrypt.validate_command(
                command=command,
                context={
                    "incident_id": incident_id,
                    "incident_type": incident.metric_type,
                    "severity": incident.severity
                }
            )
            if not validation.get("is_safe", True):
                raise HTTPException(
                    status_code=403,
                    detail={
                        "message": "Command blocked by Enkrypt AI guardrails",
                        "risk_score": validation.get("risk_score", 0.99),
                        "violations": validation.get("violations", [])
                    }
                )
        except HTTPException:
            raise
        except Exception as e:
            # Fallback to keep cluster resilient when safety API is down
            from ..core.observability import logger
            logger.warning(f"Enkrypt API unreachable during remediation check: {str(e)}")

    # Update incident suggested action to selected command
    incident.suggested_action = command
    db.commit()

    # Trigger actual action execution logic
    from ..services.incident_service import update_incident_status
    update_incident_status(db, incident.id, "APPROVED", actor=current_user.email)
    
    return {
        "success": True,
        "message": f"Remediation option '{selected_option['name']}' selected and queued for run.",
        "command": command
    }


@router.post("/{incident_id}/runbook-feedback")
def submit_runbook_feedback(
    incident_id: int,
    body: RunbookFeedbackRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Record success feedback for RAG runbook recommendation weights."""
    from ..services.runbook_recommendation_service import RunbookRecommendationService
    res = RunbookRecommendationService.record_feedback(body.runbook_id, body.success)
    
    # Log timeline event of SRE selecting this playbook
    from ..services.incident_service import add_timeline_event
    add_timeline_event(
        db, incident_id, "RUNBOOK_SELECTED",
        f"Operator executed recommended runbook {body.runbook_id}",
        f"Recorded SRE feedback success status: {body.success}.",
        actor=current_user.email
    )
    
    return res


@router.get("/sla/metrics")
def get_sla_metrics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve aggregate SLA compliance metrics over the incidents."""
    from ..services.sla_service import SLAService
    return SLAService.get_sla_summary_metrics(db)


@router.get("/{incident_id}/sla")
def get_incident_sla(
    incident_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve SLA metrics and status for a specific incident."""
    incident = get_incident(db, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    from ..services.sla_service import SLAService
    return SLAService.calculate_incident_sla(db, incident)


@router.get("/{incident_id}/compliance")
def get_incident_compliance(
    incident_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve compliance checklist and mapped regulations for an incident."""
    incident = get_incident(db, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    from ..services.compliance_service import ComplianceService
    return ComplianceService.generate_compliance_checklist(db, incident)


@router.get("/{incident_id}/compliance-report")
def get_incident_compliance_report(
    incident_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve full regulatory audit report for an incident."""
    incident = get_incident(db, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    from ..services.compliance_service import ComplianceService
    return ComplianceService.generate_regulatory_report(db, incident)


