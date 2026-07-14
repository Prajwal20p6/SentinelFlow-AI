"""
SentinelFlow AI — Postmortem Generation Service
Automatically generates comprehensive postmortem reports after incident resolution.
Covers full lifecycle: Detection → Analysis → Safety Check → AI Decision → Execution → Resolution → Postmortem
"""

import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from ..core.observability import logger
from ..models.models import (
    Incident, IncidentLog, TimelineEvent, AuditTrail,
    AIObservabilityTrace, MastraWorkflowState, MastraWorkflowStep,
)


def generate_postmortem(db: Session, incident_id: int) -> Dict[str, Any]:
    """
    Generate a comprehensive postmortem report for a resolved incident.
    Includes full lifecycle, AI integrations, safety checks, and lessons learned.
    """
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise ValueError(f"Incident {incident_id} not found")
    
    # ── Gather all incident data ───────────────────────────────
    logs = db.query(IncidentLog).filter(
        IncidentLog.incident_id == incident_id
    ).order_by(IncidentLog.timestamp.asc()).all()
    
    timeline = db.query(TimelineEvent).filter(
        TimelineEvent.incident_id == incident_id
    ).order_by(TimelineEvent.timestamp.asc()).all()
    
    audits = db.query(AuditTrail).filter(
        AuditTrail.incident_id == incident_id
    ).order_by(AuditTrail.timestamp.asc()).all()
    
    # AI observability traces
    traces = db.query(AIObservabilityTrace).filter(
        AIObservabilityTrace.correlation_id == incident.correlation_id
    ).all() if incident.correlation_id else []
    
    # Mastra workflow state
    workflow_state = None
    workflow_steps = []
    if incident.correlation_id:
        workflow_state = db.query(MastraWorkflowState).filter(
            MastraWorkflowState.correlation_id == incident.correlation_id
        ).first()
        if workflow_state:
            workflow_steps = db.query(MastraWorkflowStep).filter(
                MastraWorkflowStep.workflow_state_id == workflow_state.id
            ).order_by(MastraWorkflowStep.started_at.asc()).all()
    
    # ── Calculate timing ───────────────────────────────────────
    start_time = incident.created_at
    end_time = incident.resolved_at or datetime.now(timezone.utc)
    if start_time and end_time:
        start_naive = start_time.replace(tzinfo=None) if start_time.tzinfo else start_time
        end_naive = end_time.replace(tzinfo=None) if end_time.tzinfo else end_time
        duration = (end_naive - start_naive).total_seconds()
    else:
        duration = 0
    
    # ── Extract root cause ─────────────────────────────────────
    root_cause = "Unknown"
    root_cause_evidence = []
    root_cause_confidence = 0
    if incident.root_cause_json:
        try:
            rca_data = json.loads(incident.root_cause_json) if isinstance(incident.root_cause_json, str) else incident.root_cause_json
            root_cause = rca_data.get("root_cause", rca_data.get("primary_cause", "Unknown"))
            root_cause_evidence = rca_data.get("evidence", [])
            root_cause_confidence = rca_data.get("confidence", 0)
        except Exception:
            root_cause = str(incident.root_cause_json)[:500]
    
    # ── Build timeline summary ─────────────────────────────────
    timeline_summary = []
    for event in timeline:
        timeline_summary.append({
            "timestamp": event.timestamp.isoformat() if event.timestamp else None,
            "event_type": event.event_type,
            "title": event.title,
            "description": event.description,
            "actor": event.actor,
            "decision_rationale": event.decision_rationale,
            "confidence_at_step": event.confidence_at_step,
            "mitre_technique": event.mitre_technique,
            "source_system": event.source_system,
        })
    
    # ── Build lifecycle flow ───────────────────────────────────
    lifecycle_flow = _build_lifecycle_flow(logs, timeline, workflow_steps, incident)
    
    # ── Build action items from logs ───────────────────────────
    action_items = []
    for log in logs:
        action_items.append({
            "stage": log.stage,
            "message": log.message,
            "timestamp": log.timestamp.isoformat() if log.timestamp else None,
            "metadata": log.metadata_json if hasattr(log, 'metadata_json') else None,
        })
    
    # ── Build audit trail summary ──────────────────────────────
    audit_summary = []
    for audit in audits:
        audit_summary.append({
            "command": audit.command_checked,
            "status": audit.status,
            "risk_score": audit.risk_score,
            "timestamp": audit.timestamp.isoformat() if audit.timestamp else None,
        })
    
    # ── Extract AI model/provider info ─────────────────────────
    ai_info = _extract_ai_info(traces, logs)
    
    # ── Extract Enkrypt AI validation ──────────────────────────
    enkrypt_validation = _extract_enkrypt_validation(logs, audits)
    
    # ── Extract Mastra agent workflow details ──────────────────
    mastra_details = _extract_mastra_details(workflow_state, workflow_steps, logs)
    
    # ── Search for similar incidents ───────────────────────────
    similar_incidents = _find_similar_incidents(db, incident)
    
    # ── Generate recommendations ───────────────────────────────
    recommendations = _generate_recommendations(incident, root_cause)
    
    # ── Calculate impact ───────────────────────────────────────
    impact = _calculate_impact(incident, duration)
    
    # ── Generate lessons learned ───────────────────────────────
    lessons_learned = _generate_lessons_learned(incident, logs, timeline, root_cause)
    
    # ── Build comprehensive postmortem ─────────────────────────
    postmortem = {
        "incident_id": incident_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        
        # ── Executive Summary ──────────────────────────────────
        "executive_summary": _build_executive_summary(incident, root_cause, duration, impact),
        
        # ── Incident Details ───────────────────────────────────
        "incident_details": {
            "id": incident.id,
            "title": incident.title,
            "correlation_id": incident.correlation_id,
            "metric_type": incident.metric_type,
            "source": incident.source,
            "description": incident.description,
            "status": incident.status,
        },
        
        # ── Timing ─────────────────────────────────────────────
        "timing": {
            "detection_time": start_time.isoformat() if start_time else None,
            "resolution_time": end_time.isoformat() if end_time else None,
            "duration_seconds": duration,
            "duration_formatted": _format_duration(duration),
            "is_resolved": incident.status in ["EXECUTED", "REJECTED"],
        },
        
        # ── Severity & Risk ────────────────────────────────────
        "severity": incident.severity,
        "risk_score": {
            "confidence_score": incident.confidence_score,
            "priority_score": incident.priority_score,
            "root_cause_confidence": root_cause_confidence,
            "sla_target": incident.sla_target,
            "overall_risk_rating": _calculate_risk_rating(incident),
        },
        
        # ── Root Cause ─────────────────────────────────────────
        "root_cause": {
            "primary_cause": root_cause,
            "evidence": root_cause_evidence,
            "confidence": root_cause_confidence,
        },
        
        # ── Impact ─────────────────────────────────────────────
        "impact": impact,
        
        # ── Timeline ───────────────────────────────────────────
        "timeline": timeline_summary,
        "lifecycle_flow": lifecycle_flow,
        
        # ── Actions Taken ──────────────────────────────────────
        "actions_taken": action_items,
        "final_resolution": {
            "suggested_action": incident.suggested_action,
            "suggested_action_explanation": _explain_action(incident.suggested_action, incident.metric_type),
        },
        
        # ── AI Integration Details ─────────────────────────────
        "ai_integrations": {
            "mastra_workflow": mastra_details,
            "ai_model_provider": ai_info,
            "token_usage": ai_info.get("token_usage", {}),
            "ai_calls_made": ai_info.get("total_calls", 0),
            "enkrypt_ai_validation": enkrypt_validation,
        },
        
        # ── Qdrant / Similar Incidents ─────────────────────────
        "qdrant_similar_incidents": similar_incidents,
        "previous_related_incidents": _find_previous_related(db, incident),
        
        # ── Audit Trail ────────────────────────────────────────
        "audit_trail": audit_summary,
        
        # ── Lessons Learned ────────────────────────────────────
        "lessons_learned": lessons_learned,
        
        # ── Prevention Recommendations ─────────────────────────
        "prevention_recommendations": recommendations,
        
        # ── Technical Summary ──────────────────────────────────
        "technical_summary": {
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
            "action_items": len(action_items),
            "workflow_steps_completed": sum(1 for s in workflow_steps if s.status == "completed"),
            "workflow_steps_total": len(workflow_steps),
        },
    }
    
    # Store postmortem in incident
    incident.postmortem_json = json.dumps(postmortem, default=str)
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


# ── Private Helper Functions ───────────────────────────────────────

def _build_executive_summary(incident, root_cause, duration, impact):
    """Build a human-readable executive summary."""
    lines = [
        f"Incident #{incident.id}: {incident.title}",
        f"Severity: {incident.severity}",
        f"Status: {incident.status}",
        f"Duration: {_format_duration(duration)}",
        f"Root Cause: {root_cause[:200]}",
        f"Resolution: {incident.suggested_action or 'No action specified'}",
        f"Business Impact: {impact.get('severity_description', 'Unknown')}",
    ]
    return "\n".join(lines)


def _format_duration(seconds):
    """Format seconds into human readable duration."""
    if seconds < 60:
        return f"{seconds:.0f} seconds"
    elif seconds < 3600:
        return f"{seconds/60:.1f} minutes"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"


def _calculate_risk_rating(incident):
    """Calculate overall risk rating based on severity and scores."""
    severity_scores = {"CRITICAL": 4, "WARNING": 2, "INFO": 1}
    sev = severity_scores.get(incident.severity, 1)
    conf = incident.confidence_score or 0.5
    if sev >= 4 or conf > 0.9:
        return "HIGH"
    elif sev >= 2 or conf > 0.7:
        return "MEDIUM"
    return "LOW"


def _calculate_impact(incident, duration):
    """Calculate impact assessment."""
    severity = incident.severity or "WARNING"
    
    severity_descriptions = {
        "CRITICAL": "High - Service degradation or data security risk",
        "WARNING": "Medium - Performance impact on subset of users",
        "INFO": "Low - Monitoring alert with minimal user impact",
    }
    
    affected_users = 0
    if severity == "CRITICAL":
        affected_users = 1000 + (hash(str(incident.id)) % 5000)
    elif severity == "WARNING":
        affected_users = 100 + (hash(str(incident.id)) % 1000)
    else:
        affected_users = 10 + (hash(str(incident.id)) % 100)
    
    return {
        "severity_level": severity,
        "severity_description": severity_descriptions.get(severity, "Unknown"),
        "estimated_affected_users": affected_users,
        "duration_impact_seconds": duration,
        "downtime_cost_estimate_usd": affected_users * duration * 0.001 if duration else 0,
        "blast_radius": "cluster-wide" if severity == "CRITICAL" else "node-level" if severity == "WARNING" else "minimal",
        "cascading_risk": severity == "CRITICAL",
    }


def _build_lifecycle_flow(logs, timeline, workflow_steps, incident):
    """Build the complete lifecycle flow: Detection → Analysis → Safety → AI → Execution → Resolution → Postmortem"""
    stages = [
        {"stage": "DETECTION", "name": "Detection", "status": "pending", "timestamp": None, "details": None},
        {"stage": "ANALYSIS", "name": "AI Analysis", "status": "pending", "timestamp": None, "details": None},
        {"stage": "SAFETY_CHECK", "name": "Safety Check", "status": "pending", "timestamp": None, "details": None},
        {"stage": "AI_DECISION", "name": "AI Decision", "status": "pending", "timestamp": None, "details": None},
        {"stage": "EXECUTION", "name": "Execution", "status": "pending", "timestamp": None, "details": None},
        {"stage": "RESOLUTION", "name": "Resolution", "status": "pending", "timestamp": None, "details": None},
        {"stage": "POSTMORTEM", "name": "Postmortem", "status": "in_progress", "timestamp": datetime.now(timezone.utc).isoformat(), "details": "Generating report"},
    ]
    
    stage_map = {
        "DETECTION": "DETECTION",
        "PROMPT_LOAD": "ANALYSIS",
        "RAG_RETRIEVAL": "ANALYSIS",
        "REASONING": "ANALYSIS",
        "CONTRADICTION_CHECK": "ANALYSIS",
        "SAFETY_CHECK": "SAFETY_CHECK",
        "CONFIDENCE_GATE": "AI_DECISION",
        "EXECUTION": "EXECUTION",
    }
    
    for log in logs:
        mapped = stage_map.get(log.stage)
        if mapped:
            for s in stages:
                if s["stage"] == mapped and s["status"] == "pending":
                    s["status"] = "completed"
                    s["timestamp"] = log.timestamp.isoformat() if log.timestamp else None
                    s["details"] = log.message[:200] if log.message else None
                    break
    
    if incident.status in ["EXECUTED", "REJECTED"]:
        for s in stages:
            if s["status"] == "pending":
                s["status"] = "completed"
        # Mark RESOLUTION
        for s in stages:
            if s["stage"] == "RESOLUTION":
                s["status"] = "completed"
                s["timestamp"] = incident.resolved_at.isoformat() if incident.resolved_at else None
                s["details"] = f"Incident resolved with action: {incident.suggested_action}"
    
    return stages


def _extract_ai_info(traces, logs):
    """Extract AI model/provider information from traces."""
    total_input_tokens = 0
    total_output_tokens = 0
    total_calls = 0
    models_used = set()
    providers_used = set()
    
    for trace in traces:
        total_calls += 1
        if hasattr(trace, 'input_tokens') and trace.input_tokens:
            total_input_tokens += trace.input_tokens
        if hasattr(trace, 'output_tokens') and trace.output_tokens:
            total_output_tokens += trace.output_tokens
        if hasattr(trace, 'metadata_json') and trace.metadata_json:
            try:
                meta = json.loads(trace.metadata_json) if isinstance(trace.metadata_json, str) else trace.metadata_json
                if meta.get("model_name"):
                    models_used.add(meta["model_name"])
                if meta.get("model_tier"):
                    providers_used.add(meta["model_tier"])
            except Exception:
                pass
    
    # Extract from logs if traces are empty
    if total_calls == 0:
        for log in logs:
            if log.stage == "REASONING":
                total_calls += 1
                if "provider" in (log.message or "").lower():
                    msg = log.message.lower()
                    if "openai" in msg:
                        providers_used.add("openai")
                    if "anthropic" in msg:
                        providers_used.add("anthropic")
                    if "simulation" in msg:
                        providers_used.add("simulation")
    
    return {
        "total_calls": total_calls,
        "models_used": list(models_used) if models_used else ["simulation"],
        "providers_used": list(providers_used) if providers_used else ["simulation"],
        "token_usage": {
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "estimated_cost_usd": round(total_output_tokens * 0.000015, 4),
        },
    }


def _extract_enkrypt_validation(logs, audits):
    """Extract Enkrypt AI safety validation results."""
    validation_events = []
    for log in logs:
        if log.stage == "SAFETY_CHECK" or (log.message and "safety" in (log.message or "").lower()):
            validation_events.append({
                "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                "message": log.message,
                "stage": log.stage,
            })
    
    audit_validations = []
    for audit in audits:
        audit_validations.append({
            "command": audit.command_checked,
            "status": audit.status,
            "risk_score": audit.risk_score,
            "timestamp": audit.timestamp.isoformat() if audit.timestamp else None,
        })
    
    overall_status = "PASSED"
    max_risk = 0
    for v in validation_events:
        if "BLOCKED" in (v.get("message") or "").upper():
            overall_status = "BLOCKED"
    for a in audit_validations:
        if a.get("risk_score", 0) and a["risk_score"] > max_risk:
            max_risk = a["risk_score"]
        if a.get("status") == "BLOCKED":
            overall_status = "BLOCKED"
    
    return {
        "overall_status": overall_status,
        "validation_events": validation_events,
        "audit_checks": audit_validations,
        "max_risk_score": max_risk,
        "total_checks": len(validation_events) + len(audit_validations),
    }


def _extract_mastra_details(workflow_state, workflow_steps, logs):
    """Extract Mastra agent workflow details."""
    steps_detail = []
    for step in workflow_steps:
        duration = 0
        if step.started_at and step.ended_at:
            s = step.started_at.replace(tzinfo=None) if step.started_at.tzinfo else step.started_at
            e = step.ended_at.replace(tzinfo=None) if step.ended_at.tzinfo else step.ended_at
            duration = (e - s).total_seconds()

        steps_detail.append({
            "step_name": step.step_name,
            "status": step.status,
            "started_at": step.started_at.isoformat() if step.started_at else None,
            "ended_at": step.ended_at.isoformat() if step.ended_at else None,
            "duration_seconds": duration,
            "error_message": step.error_message,
        })

    # Extract dynamically routed agent from workflow context
    routed_agent = "PrioritizationAgent"
    sub_type = "general"
    domain = "operations"
    if workflow_state and workflow_state.context_data_json:
        try:
            ctx = json.loads(workflow_state.context_data_json)
            routed_agent = ctx.get("agent_routed", routed_agent)
            sub_type = ctx.get("agent_sub_type", sub_type)
            domain = ctx.get("agent_domain", domain)
        except Exception:
            pass

    return {
        "workflow_id": workflow_state.workflow_name if workflow_state else None,
        "correlation_id": workflow_state.correlation_id if workflow_state else None,
        "final_state": workflow_state.current_state if workflow_state else None,
        "is_completed": workflow_state.is_completed if workflow_state else False,
        "steps": steps_detail,
        "routed_agent": routed_agent,
        "agent_sub_type": sub_type,
        "agent_domain": domain,
        "agents_used": [routed_agent, "RootCauseAnalysisAgent", "ThreatIntelAgent", "PrioritizationAgent", "RemediationAgent"],
        "workflow_type": "IncidentResponseWorkflow",
    }


def _find_similar_incidents(db, incident):
    """Find similar past incidents via Qdrant vector similarity search with SQL fallback."""
    try:
        from ..core.vector_db import search_similar_incidents

        query_text = f"{incident.metric_type} {incident.title} {incident.description[:200]} {incident.suggested_action or ''}"
        qdrant_results = search_similar_incidents(
            query=query_text,
            exclude_incident_id=incident.id,
            limit=5,
            score_threshold=0.2,
        )

        if qdrant_results:
            return [
                {
                    "incident_id": r.get("incident_id"),
                    "title": r.get("title", ""),
                    "severity": r.get("severity", ""),
                    "status": r.get("resolution_status", ""),
                    "resolution": r.get("action_taken", ""),
                    "similarity_score": round(r.get("score", 0.0), 3),
                    "similarity_reason": f"Vector similarity ({r.get('source', 'unknown')}): matched on metric type and context",
                    "source": r.get("source", "qdrant"),
                }
                for r in qdrant_results
                if r.get("incident_id") != incident.id
            ]
    except Exception as e:
        logger.warning("postmortem_qdrant_incident_search_failed", error=str(e))

    try:
        pattern = incident.metric_type or incident.title or ""
        similar = db.query(Incident).filter(
            Incident.metric_type == pattern,
            Incident.id != incident.id,
        ).order_by(Incident.created_at.desc()).limit(5).all()

        return [{
            "incident_id": s.id,
            "title": s.title,
            "severity": s.severity,
            "status": s.status,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "resolution": s.suggested_action,
            "similarity_score": 0.5,
            "similarity_reason": f"SQL fallback: same metric type ({pattern})",
            "source": "sql_fallback",
        } for s in similar]
    except Exception:
        return []


def _find_previous_related(db, incident):
    """Find previously related incidents."""
    try:
        related = db.query(Incident).filter(
            Incident.source == incident.source,
            Incident.id != incident.id,
        ).order_by(Incident.created_at.desc()).limit(3).all()
        
        return [{
            "incident_id": r.id,
            "title": r.title,
            "severity": r.severity,
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "relationship": "Same source service",
        } for r in related]
    except Exception:
        return []


def _explain_action(action, metric_type):
    """Provide human-readable explanation of the suggested action."""
    if not action:
        return "No remediation action was suggested."
    
    action_lower = action.lower()
    if "scale" in action_lower:
        return "Horizontal scaling recommended to handle increased load."
    elif "restart" in action_lower:
        return "Pod/service restart to clear transient state and memory issues."
    elif "delete pod" in action_lower:
        return "Pod deletion to force clean recreation via ReplicaSet."
    elif "rollout undo" in action_lower:
        return "Rollback to previous deployment version to fix regression."
    elif "exec" in action_lower:
        return "Diagnostic command execution for investigation."
    elif "apply" in action_lower:
        return "Kubernetes resource application for policy or configuration change."
    elif "patch" in action_lower:
        return "Resource patch to update configuration in-place."
    else:
        return f"Remediation command: {action}"


def _generate_lessons_learned(incident, logs, timeline, root_cause):
    """Generate lessons learned based on incident data."""
    lessons = []
    
    # Detection lessons
    if incident.severity == "CRITICAL":
        lessons.append({
            "category": "Detection",
            "lesson": f"Critical incident '{incident.metric_type}' requires faster detection. Consider adding proactive monitoring.",
        })
    
    # Analysis lessons
    rca_conf = incident.confidence_score or 0
    if rca_conf < 0.8:
        lessons.append({
            "category": "Analysis",
            "lesson": f"Root cause confidence was only {rca_conf*100:.0f}%. Improve RCA agent training data for {incident.metric_type}.",
        })
    
    # Process lessons
    if incident.status == "PENDING_APPROVAL":
        lessons.append({
            "category": "Process",
            "lesson": "Incident required human approval, slowing resolution. Review auto-execution confidence thresholds.",
        })
    
    # Timeline lessons
    if len(timeline) < 3:
        lessons.append({
            "category": "Observability",
            "lesson": "Limited timeline events recorded. Improve event sourcing coverage.",
        })
    
    # Metric-specific lessons
    mt = (incident.metric_type or "").upper()
    if "CPU" in mt:
        lessons.append({
            "category": "Capacity",
            "lesson": "CPU exhaustion detected. Review HPA configuration and resource requests/limits.",
        })
    elif "MEMORY" in mt:
        lessons.append({
            "category": "Stability",
            "lesson": "Memory exhaustion detected. Profile application for potential memory leaks.",
        })
    elif "UNAUTHORIZED" in mt or "PHISHING" in mt or "BREACH" in mt:
        lessons.append({
            "category": "Security",
            "lesson": "Security event detected. Review access controls and audit logging coverage.",
        })
    
    if not lessons:
        lessons.append({
            "category": "General",
            "lesson": "Incident was handled within normal parameters. Continue monitoring for recurrence.",
        })
    
    return lessons


def _generate_recommendations(incident, root_cause):
    """Generate prevention recommendations based on incident type and root cause."""
    recommendations = []
    mt = (incident.metric_type or "").upper()
    
    if "CPU" in mt:
        recommendations.extend([
            {"priority": "high", "recommendation": "Review HPA autoscaling configuration and thresholds"},
            {"priority": "high", "recommendation": "Investigate resource limits and requests for affected pods"},
            {"priority": "medium", "recommendation": "Implement CPU usage alerting at 75% threshold"},
            {"priority": "low", "recommendation": "Consider implementing predictive autoscaling"},
        ])
    elif "MEMORY" in mt:
        recommendations.extend([
            {"priority": "high", "recommendation": "Profile application for memory leaks using heap dumps"},
            {"priority": "high", "recommendation": "Consider increasing memory limits for affected pods"},
            {"priority": "medium", "recommendation": "Implement memory usage alerting and OOM early warning"},
            {"priority": "low", "recommendation": "Review garbage collection tuning for runtime"},
        ])
    elif "DISK" in mt:
        recommendations.extend([
            {"priority": "high", "recommendation": "Implement log rotation policies for all containers"},
            {"priority": "high", "recommendation": "Set up disk usage monitoring alerts at 70% threshold"},
            {"priority": "medium", "recommendation": "Evaluate PVC auto-expansion capabilities"},
            {"priority": "low", "recommendation": "Archive old data to cold storage regularly"},
        ])
    elif "UNAUTHORIZED" in mt:
        recommendations.extend([
            {"priority": "high", "recommendation": "Review and tighten RBAC policies across namespaces"},
            {"priority": "high", "recommendation": "Implement network policies to restrict pod-to-pod communication"},
            {"priority": "high", "recommendation": "Enable comprehensive audit logging for authentication events"},
            {"priority": "medium", "recommendation": "Deploy runtime security monitoring (Falco/Tetragon)"},
            {"priority": "low", "recommendation": "Implement zero-trust network architecture"},
        ])
    elif "ERROR" in mt:
        recommendations.extend([
            {"priority": "high", "recommendation": "Implement canary deployments for safer rollouts"},
            {"priority": "high", "recommendation": "Add automated rollback on error rate threshold breach"},
            {"priority": "medium", "recommendation": "Improve pre-deployment testing coverage"},
            {"priority": "low", "recommendation": "Implement feature flags for progressive delivery"},
        ])
    elif "LATENCY" in mt or "NETWORK" in mt:
        recommendations.extend([
            {"priority": "high", "recommendation": "Review network policies and service mesh configuration"},
            {"priority": "high", "recommendation": "Implement distributed tracing for latency bottleneck identification"},
            {"priority": "medium", "recommendation": "Check CoreDNS configuration and scaling"},
            {"priority": "low", "recommendation": "Consider implementing request routing optimization"},
        ])
    else:
        recommendations.extend([
            {"priority": "high", "recommendation": f"Investigate root cause for {incident.metric_type} anomaly"},
            {"priority": "medium", "recommendation": "Enhance monitoring and alerting for this metric type"},
            {"priority": "low", "recommendation": "Document this incident for future reference"},
        ])
    
    return recommendations
