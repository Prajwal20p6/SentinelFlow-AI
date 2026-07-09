"""
SentinelFlow AI — Incident Timeline & Explainability Service
Implements event-sourced forensic incident timelines and decision explainability.
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from ..models.models import TimelineEvent, Incident, AIObservabilityTrace, RemediationExecution
from .incident_service import add_timeline_event

# ── Explainability Generator ────────────────────────────────
def generate_decision_explanation(
    step_name: str,
    metadata: Dict[str, Any]
) -> str:
    """
    Generate markdown-formatted, human-readable explanations of automated actions,
    LLM reasoning steps, confidence gates, and safety evaluations.
    """
    if step_name == "LLM_REASONING":
        provider = metadata.get("provider", "Simulation Model")
        confidence = metadata.get("confidence", 0.0)
        confidence_label = "HIGH CONFIDENCE (Cleared)" if confidence >= 0.70 else "LOW CONFIDENCE (Escalated to HITL)"
        contradictions = metadata.get("contradictions", "None detected")
        reasoning = metadata.get("reasoning", "No detailed reasoning text provided.")
        plan = metadata.get("remediation_plan", "No plan provided.")

        return f"""### AI Reasoner & Diagnosis Explanation
- **Model Provider:** {provider}
- **Confidence Level:** {confidence:.2f} — *{confidence_label}*
- **Contradiction Verification:** {contradictions}

#### AI Internal Reasoning Chain
{reasoning}

#### Proposed Action Steps
{plan}
"""

    elif step_name == "SAFETY_CHECK":
        status = metadata.get("status", "UNKNOWN")
        risk_score = metadata.get("risk_score", 0.0)
        assessment = metadata.get("assessment", "No assessment available.")
        command = metadata.get("command", "No command verified.")
        
        status_label = "🚨 BLOCKED (Dangerous Operation)" if status == "BLOCKED" else "✅ ALLOWED (Clean Command)"

        return f"""### Safety Envelope Evaluation
- **Verdict:** {status_label}
- **Calculated Risk Score:** {risk_score:.2f}
- **Safety Policy Log:** {assessment}
- **Evaluated Command:** `{command}`
"""

    elif step_name == "HITL_DECISION":
        action = metadata.get("action", "PENDING")
        actor = metadata.get("actor", "system")
        rationale = metadata.get("rationale", "No explanation entered by administrator.")

        return f"""### HITL Action & Sign-Off Explanation
- **Action Taken:** {action}
- **Authorized Actor:** {actor}
- **Handoff Rationale:** {rationale}
"""

    elif step_name == "RCA_ANALYSIS":
        primary = metadata.get("primary_cause", "Unknown Cause")
        secondary = metadata.get("secondary_cause", "None")
        confidence = metadata.get("confidence", 0)
        remediation = metadata.get("remediation_action", "No remediation suggested")
        evidence = metadata.get("evidence", [])
        evidence_list = "\n".join([f"- {ev}" for ev in evidence])

        return f"""### Root Cause Analysis Diagnostic Report
- **Primary Root Cause:** {primary} ({confidence}% confidence)
- **Secondary Contributor:** {secondary}

#### Supporting Forensic Evidence
{evidence_list if evidence_list else "No metrics anomalies or error log patterns detected."}

#### Suggested Recovery Remedy
`{remediation}`
"""

    # Generic default fallback format
    desc = metadata.get("description", "Automated step execution.")
    return f"""### Automated Step Detail: {step_name}
- **Action:** {desc}
- **Status:** SUCCESS
"""


# ── Timeline Queries & Forensics ────────────────────────────

def get_incident_timeline(
    db: Session,
    incident_id: int,
    event_type: Optional[str] = None
) -> List[TimelineEvent]:
    """Retrieve event-sourced timeline logs for an incident."""
    query = db.query(TimelineEvent).filter(TimelineEvent.incident_id == incident_id)
    if event_type:
        query = query.filter(TimelineEvent.event_type == event_type)
    return query.order_by(TimelineEvent.timestamp.asc()).all()


def reconstruct_incident_forensics(
    db: Session,
    incident_id: int
) -> Dict[str, Any]:
    """Reconstruct a full forensic audit trail of an incident for auditing and learning."""
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        return {"error": f"Incident {incident_id} not found."}

    # Fetch timeline events
    timeline_events = get_incident_timeline(db, incident_id)

    # Fetch AI traces matching the incident's correlation id
    ai_traces = []
    if incident.correlation_id:
        traces = db.query(AIObservabilityTrace).filter(
            AIObservabilityTrace.correlation_id == incident.correlation_id
        ).all()
        ai_traces = [
            {
                "id": t.id,
                "step_name": t.step_name,
                "provider": t.provider,
                "prompt_tokens": t.prompt_tokens,
                "completion_tokens": t.completion_tokens,
                "cost_usd": t.cost_usd,
                "duration_sec": t.duration_sec,
                "timestamp": t.timestamp.isoformat() if t.timestamp else None
            }
            for t in traces
        ]

    # Fetch remediation execution log if available
    remediations = db.query(RemediationExecution).filter(
        RemediationExecution.incident_id == incident_id
    ).all()
    remediation_logs = [
        {
            "id": r.id,
            "command": r.command,
            "status": r.status,
            "output": r.output,
            "duration_ms": r.duration_ms,
            "executed_at": r.executed_at.isoformat() if r.executed_at else None
        }
        for r in remediations
    ]

    import json
    explainability_report = None
    if incident.explainability_json:
        try:
            explainability_report = json.loads(incident.explainability_json)
        except Exception:
            pass

    return {
        "incident_id": incident.id,
        "title": incident.title,
        "source": incident.source,
        "status": incident.status,
        "correlation_id": incident.correlation_id,
        "created_at": incident.created_at.isoformat() if incident.created_at else None,
        "timeline": [
            {
                "id": e.id,
                "event_type": e.event_type,
                "title": e.title,
                "description": e.description,
                "actor": e.actor,
                "decision_rationale": e.decision_rationale,
                "confidence_at_step": e.confidence_at_step,
                "duration_ms": e.duration_ms,
                "timestamp": e.timestamp.isoformat() if e.timestamp else None
            }
            for e in timeline_events
        ],
        "ai_observability_traces": ai_traces,
        "remediation_logs": remediation_logs,
        "explainability_report": explainability_report
    }


def record_timeline_event_with_explanation(
    db: Session,
    incident_id: int,
    event_type: str,
    title: str,
    step_name: str,
    metadata: Dict[str, Any],
    description: Optional[str] = None,
    actor: str = "system",
    confidence_at_step: Optional[float] = None,
    duration_ms: Optional[float] = None
) -> TimelineEvent:
    """Record an incident timeline event with automated markdown explanation generator."""
    rationale = generate_decision_explanation(step_name, metadata)
    return add_timeline_event(
        db=db,
        incident_id=incident_id,
        event_type=event_type,
        title=title,
        description=description,
        actor=actor,
        decision_rationale=rationale,
        confidence_at_step=confidence_at_step,
        duration_ms=duration_ms
    )
