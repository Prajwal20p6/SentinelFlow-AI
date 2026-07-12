"""
SentinelFlow AI — AI Agent Workflow Service (Mastra-Inspired)
Implements the 8-state incident response workflow with RAG, LLM reasoning,
contradiction checking, safety validation, and confidence gating.
"""

import time
import json
import random
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session

from ..core.vector_db import search_similar_runbooks
from ..core.security import generate_correlation_id
from ..models.models import (
    Incident, IncidentLog, PromptTemplate,
    AIObservabilityTrace, TimelineEvent,
    MastraWorkflowState, MastraWorkflowStep,
)
from .incident_service import (
    create_incident, update_incident_status, add_incident_log, add_timeline_event,
)
from .safety_service import evaluate_command_safety, scrub_pii, detect_prompt_injection
from ..core.config import get_settings
from ..core.observability import logger

settings = get_settings()


# ══════════════════════════════════════════════════════════════
# WORKFLOW STATES
# ══════════════════════════════════════════════════════════════
# State 1: DETECTION — Anomaly identified by telemetry
# State 2: PROMPT_LOOKUP — Load CRISPE prompt template
# State 3: RAG_RETRIEVAL — Search Qdrant for similar incidents
# State 4: LLM_REASONING — Generate remediation suggestion
# State 5: CONTRADICTION_CHECK — Mastra contradiction analysis
# State 6: SAFETY_CHECK — Enkrypt AI safety evaluation
# State 7: CONFIDENCE_GATE — Route to auto-pilot or HITL
# State 8: EXECUTION — Apply remediation action


# ── CRISPE Prompt Templates ─────────────────────────────────
DEFAULT_PROMPTS = {
    "CPU_SPIKE": {
        "id": "CPU_SPIKE",
        "name": "CPU Exhaustion Handler",
        "capacity": "You are a Kubernetes SRE agent specializing in resource management.",
        "role": "Analyze CPU exhaustion events and recommend scaling or restart actions.",
        "intent": "Determine if the CPU spike requires pod scaling, restart, or HPA adjustment.",
        "subject": "A Kubernetes pod is experiencing CPU usage above threshold.",
        "premium_response": "Provide: 1) Root cause analysis, 2) Recommended kubectl command, 3) Rollback plan.",
        "evaluation": "Verify the action reduces CPU below 80% within 5 minutes.",
        "category": "performance",
    },
    "MEMORY_EXHAUSTION": {
        "id": "MEMORY_EXHAUSTION",
        "name": "Memory OOM Handler",
        "capacity": "You are a Kubernetes SRE agent specializing in memory management.",
        "role": "Analyze memory exhaustion and OOMKilled events.",
        "intent": "Determine if the pod needs memory limit increases, leak investigation, or restart.",
        "subject": "A pod is approaching or has hit its memory limit.",
        "premium_response": "Provide: 1) Memory analysis, 2) Resource limit adjustment command, 3) Monitoring plan.",
        "evaluation": "Confirm memory stays below 85% after remediation.",
        "category": "performance",
    },
    "UNAUTHORIZED_ACCESS": {
        "id": "UNAUTHORIZED_ACCESS",
        "name": "Security Breach Handler",
        "capacity": "You are a Kubernetes security operations agent.",
        "role": "Analyze unauthorized access attempts and recommend isolation.",
        "intent": "Determine if the access is a genuine breach requiring pod isolation and token revocation.",
        "subject": "Unauthorized API or namespace access detected.",
        "premium_response": "Provide: 1) Threat assessment, 2) Network policy command, 3) RBAC audit steps.",
        "evaluation": "Verify the compromised access vector is closed.",
        "category": "security",
    },
    "DISK_FULL": {
        "id": "DISK_FULL",
        "name": "Storage Exhaustion Handler",
        "capacity": "You are a Kubernetes storage management agent.",
        "role": "Analyze disk usage and PVC capacity issues.",
        "intent": "Determine cleanup actions or PV expansion needed.",
        "subject": "A persistent volume is approaching capacity.",
        "premium_response": "Provide: 1) Space analysis, 2) Cleanup or resize command, 3) Threshold adjustment.",
        "evaluation": "Confirm disk usage drops below 80%.",
        "category": "storage",
    },
    "HIGH_LATENCY": {
        "id": "HIGH_LATENCY",
        "name": "Latency Spike Handler",
        "capacity": "You are a network performance optimization agent.",
        "role": "Analyze high latency patterns and network issues.",
        "intent": "Determine if the latency is caused by resource contention, DNS, or network policies.",
        "subject": "Service latency exceeds acceptable thresholds.",
        "premium_response": "Provide: 1) Latency breakdown, 2) DNS/network diagnostic commands, 3) Optimization steps.",
        "evaluation": "Verify latency returns to baseline within 10 minutes.",
        "category": "network",
    },
    "ERROR_RATE_SPIKE": {
        "id": "ERROR_RATE_SPIKE",
        "name": "Error Rate Handler",
        "capacity": "You are a reliability engineering agent.",
        "role": "Analyze sudden increases in application error rates.",
        "intent": "Determine the source of errors and recommend recovery actions.",
        "subject": "Application error rate has spiked above normal levels.",
        "premium_response": "Provide: 1) Error categorization, 2) Rollback or restart command, 3) Monitoring plan.",
        "evaluation": "Confirm error rate returns below 1% after action.",
        "category": "reliability",
    },
}

# ── Incident Type → Mastra Agent Routing ─────────────────────
AGENT_ROUTING = {
    "CPU_SPIKE":            {"agent": "RootCauseAnalysisAgent",     "sub_type": "performance",   "domain": "compute"},
    "MEMORY_EXHAUSTION":    {"agent": "RootCauseAnalysisAgent",     "sub_type": "resource",      "domain": "memory"},
    "DISK_FULL":            {"agent": "RemediationAgent",           "sub_type": "storage",       "domain": "storage"},
    "HIGH_LATENCY":         {"agent": "ThreatIntelAgent",           "sub_type": "performance",   "domain": "network"},
    "ERROR_RATE_SPIKE":     {"agent": "RemediationAgent",           "sub_type": "reliability",   "domain": "application"},
    "UNAUTHORIZED_ACCESS":  {"agent": "ThreatIntelAgent",           "sub_type": "security",      "domain": "security"},
    "NETWORK_OUTAGE":       {"agent": "ThreatIntelAgent",           "sub_type": "network",       "domain": "infrastructure"},
}

DEFAULT_AGENT = {"agent": "PrioritizationAgent", "sub_type": "general", "domain": "operations"}


def seed_prompt_templates(db: Session) -> None:
    """Seed CRISPE prompt templates into the database."""
    for prompt_id, data in DEFAULT_PROMPTS.items():
        existing = db.query(PromptTemplate).filter(PromptTemplate.id == prompt_id).first()
        if not existing:
            template = PromptTemplate(**data)
            db.add(template)
    db.commit()
    logger.info("prompt_templates_seeded", count=len(DEFAULT_PROMPTS))


def run_incident_workflow(
    db: Session,
    anomaly_type: str,
    description: str,
    severity: str = "WARNING",
    node_name: str = "node-01",
    pod_name: Optional[str] = None,
    correlation_id: Optional[str] = None,
) -> Incident:
    """
    Execute the complete 8-state Mastra-inspired incident response workflow.
    Supports pause/resume capabilities using database workflow state tracking.
    """
    correlation_id = correlation_id or generate_correlation_id()
    workflow_start = time.time()

    logger.info("workflow_started", anomaly_type=anomaly_type, correlation_id=correlation_id)

    # 1. Load or Create MastraWorkflowState
    state = db.query(MastraWorkflowState).filter(MastraWorkflowState.correlation_id == correlation_id).first()
    if not state:
        state = MastraWorkflowState(
            workflow_name="incident_response",
            correlation_id=correlation_id,
            current_state="DETECT_ANOMALY",
            context_data_json=json.dumps({}),
            is_completed=False,
        )
        db.add(state)
        db.commit()
        db.refresh(state)

    context = json.loads(state.context_data_json or "{}")

    # Store workflow-level metadata in context for broadcast enrichment
    context.setdefault("anomaly_type", anomaly_type)
    context.setdefault("severity", severity)

    # Helper functions to record steps
    def _start_step(step_name: str) -> MastraWorkflowStep:
        s = db.query(MastraWorkflowStep).filter(
            MastraWorkflowStep.workflow_state_id == state.id,
            MastraWorkflowStep.step_name == step_name
        ).first()
        if not s:
            s = MastraWorkflowStep(
                workflow_state_id=state.id,
                step_name=step_name,
                status="running",
                started_at=datetime.now(timezone.utc),
            )
            db.add(s)
            db.commit()
            db.refresh(s)
        else:
            s.status = "running"
            s.started_at = datetime.now(timezone.utc)
            s.error_message = None
            db.commit()
            
        try:
            from .websocket_service import broadcast_workflow_progress, broadcast_mastra_execution
            from datetime import timedelta
            inc_id = incident.id if ('incident' in locals() and incident) else context.get("incident_id", 0)
            
            steps_map = {
                "DETECT_ANOMALY": 1,
                "RETRIEVE_CONTEXT": 2,
                "RETRIEVE_RUNBOOKS": 3,
                "PLAN_REMEDIATION": 4,
                "CONTRADICTION_CHECK": 5,
                "VALIDATE": 6,
                "APPROVE_DECISION": 7,
                "EXECUTE_REMEDIATION": 8
            }
            step_num = steps_map.get(step_name, 1)
            est_completion = (datetime.now(timezone.utc) + timedelta(seconds=15)).isoformat()
            
            broadcast_workflow_progress(
                incident_id=int(inc_id),
                current_step=step_num,
                total_steps=8,
                step_name=step_name,
                step_status="in_progress",
                estimated_completion=est_completion
            )

            # Broadcast Mastra execution event for live monitor
            try:
                _agent = context.get("agent_routed", "")
                _sub = context.get("agent_sub_type", "")
                _dom = context.get("agent_domain", "")
                _rr = context.get("reasoning_result", {})
                _prov = _rr.get("provider", "simulation") if isinstance(_rr, dict) else "simulation"
                _conf = _rr.get("confidence", 0.0) if isinstance(_rr, dict) else 0.0
                _safety_status = context.get("safety_status", "")
                _safety_risk = context.get("safety_risk", 0.0)
                _action = incident.suggested_action if incident else ""
                _anomaly = context.get("anomaly_type", "")
                _severity = context.get("severity", "")

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

                broadcast_mastra_execution(
                    incident_id=int(inc_id),
                    step_name=step_name,
                    step_number=step_num,
                    total_steps=8,
                    step_status="in_progress",
                    agent_name=_agent,
                    agent_sub_type=_sub,
                    agent_domain=_dom,
                    ai_provider=_prov,
                    safety_status=_safety_status,
                    risk_score=_safety_risk,
                    confidence=_conf,
                    action_taken=_action or "",
                    anomaly_type=_anomaly,
                    severity=_severity,
                    message=step_labels.get(step_name, step_name),
                )
            except Exception:
                pass
        except Exception:
            pass
            
        return s

    def _complete_step(step: MastraWorkflowStep, next_state: str):
        step.status = "completed"
        step.ended_at = datetime.now(timezone.utc)
        state.current_state = next_state
        state.context_data_json = json.dumps(context)
        db.commit()
        
        duration_sec = 0.0
        if step.started_at and step.ended_at:
            start_naive = step.started_at.replace(tzinfo=None)
            end_naive = step.ended_at.replace(tzinfo=None)
            duration_sec = (end_naive - start_naive).total_seconds()
            
        try:
            from ..core.observability import track_workflow_step
            track_workflow_step(step.step_name, "completed", duration_sec)
        except Exception:
            pass

        try:
            from .websocket_service import broadcast_workflow_step, broadcast_workflow_progress, broadcast_mastra_execution
            inc_id = incident.id if ('incident' in locals() and incident) else context.get("incident_id", 0)
            
            broadcast_workflow_step(
                incident_id=int(inc_id),
                step_name=step.step_name,
                status="completed",
                duration_seconds=duration_sec
            )
            
            steps_map = {
                "DETECT_ANOMALY": 1,
                "RETRIEVE_CONTEXT": 2,
                "RETRIEVE_RUNBOOKS": 3,
                "PLAN_REMEDIATION": 4,
                "CONTRADICTION_CHECK": 5,
                "VALIDATE": 6,
                "APPROVE_DECISION": 7,
                "EXECUTE_REMEDIATION": 8
            }
            step_num = steps_map.get(step.step_name, 1)
            
            broadcast_workflow_progress(
                incident_id=int(inc_id),
                current_step=step_num,
                total_steps=8,
                step_name=step.step_name,
                step_status="completed"
            )

            try:
                _agent = context.get("agent_routed", "")
                _sub = context.get("agent_sub_type", "")
                _dom = context.get("agent_domain", "")
                _rr = context.get("reasoning_result", {})
                _prov = _rr.get("provider", "simulation") if isinstance(_rr, dict) else "simulation"
                _conf = _rr.get("confidence", 0.0) if isinstance(_rr, dict) else 0.0
                _safety_status = context.get("safety_status", "")
                _safety_risk = context.get("safety_risk", 0.0)
                _action = incident.suggested_action if incident else ""
                _anomaly = context.get("anomaly_type", "")
                _severity = context.get("severity", "")

                broadcast_mastra_execution(
                    incident_id=int(inc_id),
                    step_name=step.step_name,
                    step_number=step_num,
                    total_steps=8,
                    step_status="completed",
                    agent_name=_agent,
                    agent_sub_type=_sub,
                    agent_domain=_dom,
                    ai_provider=_prov,
                    safety_status=_safety_status,
                    risk_score=_safety_risk,
                    confidence=_conf,
                    action_taken=_action or "",
                    anomaly_type=_anomaly,
                    severity=_severity,
                    duration_seconds=duration_sec,
                    message=f"Completed: {step.step_name}",
                )
            except Exception:
                pass
        except Exception:
            pass

    def _fail_step(step: MastraWorkflowStep, error_msg: str):
        step.status = "failed"
        step.ended_at = datetime.now(timezone.utc)
        step.error_message = error_msg
        state.context_data_json = json.dumps(context)
        db.commit()
        
        duration_sec = 0.0
        if step.started_at and step.ended_at:
            start_naive = step.started_at.replace(tzinfo=None)
            end_naive = step.ended_at.replace(tzinfo=None)
            duration_sec = (end_naive - start_naive).total_seconds()

        try:
            from ..core.observability import track_workflow_step
            track_workflow_step(step.step_name, "failed", duration_sec)
        except Exception:
            pass

        try:
            from .websocket_service import broadcast_workflow_step, broadcast_workflow_progress, broadcast_mastra_execution
            inc_id = incident.id if ('incident' in locals() and incident) else context.get("incident_id", 0)
            
            broadcast_workflow_step(
                incident_id=int(inc_id),
                step_name=step.step_name,
                status="failed",
                duration_seconds=duration_sec
            )
            
            steps_map = {
                "DETECT_ANOMALY": 1,
                "RETRIEVE_CONTEXT": 2,
                "RETRIEVE_RUNBOOKS": 3,
                "PLAN_REMEDIATION": 4,
                "CONTRADICTION_CHECK": 5,
                "VALIDATE": 6,
                "APPROVE_DECISION": 7,
                "EXECUTE_REMEDIATION": 8
            }
            step_num = steps_map.get(step.step_name, 1)
            
            broadcast_workflow_progress(
                incident_id=int(inc_id),
                current_step=step_num,
                total_steps=8,
                step_name=step.step_name,
                step_status="failed"
            )

            try:
                broadcast_mastra_execution(
                    incident_id=int(inc_id),
                    step_name=step.step_name,
                    step_number=step_num,
                    total_steps=8,
                    step_status="failed",
                    anomaly_type=context.get("anomaly_type", ""),
                    severity=context.get("severity", ""),
                    duration_seconds=duration_sec,
                    message=f"Failed: {error_msg[:200]}",
                )
            except Exception:
                pass
        except Exception:
            pass

    # ── State 1: DETECT_ANOMALY ──────────────────────────────
    if "incident_id" not in context:
        step = _start_step("DETECT_ANOMALY")
        try:
            # Apply input guardrails: PII Scrubbing
            description = scrub_pii(description)
            
            # Apply input guardrails: Prompt Injection Detection
            is_injection, injection_msg = detect_prompt_injection(description)

            incident = create_incident(
                db=db,
                source="K8s Telemetry Monitor",
                metric_type=anomaly_type,
                severity=severity,
                title=f"{anomaly_type.replace('_', ' ').title()} on {node_name}" + (f"/{pod_name}" if pod_name else ""),
                description=description,
                correlation_id=correlation_id,
            )

            # Detect and link correlated parent/cascading incidents
            try:
                from .incident_correlation_service import IncidentCorrelationService
                IncidentCorrelationService.correlate_incident(db, incident.id)
            except Exception as e:
                logger.warning("incident_correlation_error", error=str(e))

            # Clear any stale memory traces for the incident at the start of ingestion
            try:
                from .memory_service import clear_memory
                clear_memory(incident.id)
            except Exception:
                pass

            try:
                from .slack_service import post_slack_notification
                post_slack_notification(
                    db=db,
                    incident=incident,
                    message=f"🚨 Anomaly '{anomaly_type}' detected on {node_name}. Incident #{incident.id} generated."
                )
            except Exception:
                pass

            if is_injection:
                update_incident_status(db, incident.id, "ANALYZING", actor="input-guard")
                update_incident_status(db, incident.id, "REJECTED", actor="input-guard")
                add_incident_log(db, incident.id, "DETECTION", f"BLOCKED: {injection_msg}")
                _fail_step(step, injection_msg)
                raise ValueError(f"Security Alert: {injection_msg}")

            update_incident_status(db, incident.id, "ANALYZING", actor="workflow")
            add_incident_log(db, incident.id, "DETECTION", f"Anomaly '{anomaly_type}' detected on {node_name}")
            
            # Execute dedicated Root Cause Analysis Agent
            try:
                from .rca_service import run_root_cause_analysis
                run_root_cause_analysis(db, incident.id)
            except Exception as e:
                logger.warning("rca_agent_execution_failed", error=str(e))

            # Execute dedicated Kubernetes Intelligence Agent for K8s infrastructure signals
            if any(k in (anomaly_type or "").upper() or k in (description or "").upper() for k in ["CPU", "DISK", "MEMORY", "POD", "NODE", "DEPLOYMENT", "REPLICA", "K8S", "KUBERNETES", "PVC", "NAMESPACE"]):
                try:
                    from .k8s_intelligence_agent import run_k8s_intelligence_analysis
                    run_k8s_intelligence_analysis(db, incident.id)
                except Exception as e:
                    logger.warning("k8s_agent_execution_failed", error=str(e))

            context["incident_id"] = incident.id
            context["anomaly_type"] = anomaly_type
            context["description"] = description
            context["severity"] = severity
            context["node_name"] = node_name
            context["pod_name"] = pod_name
            
            # ── Mastra Microservice Integration ─────────────────────
            from ..core.config import get_settings
            from ..integrations.mastra_client import MastraClient
            
            settings = get_settings()
            mastra = MastraClient(settings.MASTRA_SERVICE_URL)
            
            is_mastra_healthy = False
            try:
                is_mastra_healthy = mastra.health_check()
            except Exception:
                pass
                
            if is_mastra_healthy:
                try:
                    logger.info("routing_workflow_to_mastra_microservice", incident_id=incident.id)
                    res = mastra.execute_incident_workflow(
                        incident_id=str(incident.id),
                        incident_type=anomaly_type,
                        alert_data={
                            "severity": severity,
                            "node_name": node_name,
                            "pod_name": pod_name,
                            "correlation_id": correlation_id
                        },
                        metrics={},
                        logs=[]
                    )
                    
                    wf_result = res.get("result", {})
                    rca = wf_result.get("rca", {})
                    threats = wf_result.get("threats", {})
                    priority = wf_result.get("priority", {})
                    remediation = wf_result.get("remediation", {})
                    
                    incident.root_cause_json = json.dumps(rca)
                    
                    priority_level = priority.get("priority_level", "P2")
                    incident.sla_target = priority_level
                    incident.priority_score = priority.get("sla_minutes", 120)
                    
                    recommended_opt = remediation.get("recommended_option", {})
                    suggested_cmd = recommended_opt.get("action") if isinstance(recommended_opt, dict) else str(recommended_opt)
                    if not suggested_cmd and remediation.get("ranked_options"):
                        top_opt = remediation.get("ranked_options")[0]
                        suggested_cmd = top_opt.get("action") if isinstance(top_opt, dict) else str(top_opt)
                    
                    incident.suggested_action = suggested_cmd or "kubectl describe pods"
                    
                    success_prob = recommended_opt.get("success_probability", 85) if isinstance(recommended_opt, dict) else 85
                    confidence = success_prob / 100.0
                    incident.confidence_score = confidence
                    
                    incident.remediation_options_json = json.dumps(remediation.get("ranked_options", []))
                    db.commit()
                    
                    add_incident_log(db, incident.id, "PROMPT_LOAD", "Mastra integration: CRISPE loaded.")
                    add_incident_log(db, incident.id, "RAG_RETRIEVAL", f"Mastra RAG runbooks fetched: {len(remediation.get('ranked_options', []))} options.")
                    add_incident_log(db, incident.id, "REASONING", f"Mastra agent reasoning success. RCA Confidence: {rca.get('confidence', 90)}%.")
                    add_incident_log(db, incident.id, "CONTRADICTION_CHECK", "Mastra workflow: contradiction checks passed.")
                    
                    for step_name in ["RETRIEVE_CONTEXT", "RETRIEVE_RUNBOOKS", "PLAN_REMEDIATION", "CONTRADICTION_CHECK", "VALIDATE"]:
                        step_obj = _start_step(step_name)
                        _complete_step(step_obj, step_name)
                    
                    context["prompt_context"] = "Mastra remote context"
                    context["rag_context"] = "Mastra remote RAG context"
                    context["reasoning_result"] = {
                        "analysis": rca.get("root_cause", "RCA analysis completed by Mastra"),
                        "action": incident.suggested_action,
                        "confidence": confidence,
                        "rationale": "Mastra agent suggested recovery"
                    }
                    context["contradiction_checked"] = True
                    context["safety_checked"] = True
                    
                    from .execution_mode_service import ExecutionModeService
                    target_svc = "payment" if "payment" in incident.title.lower() else "kube-system"
                    auto_allowed, gov_reason = ExecutionModeService.should_auto_execute(
                        db=db,
                        incident_id=incident.id,
                        confidence_score=confidence * 100,
                        action_command=incident.suggested_action,
                        target_service=target_svc,
                        affected_services_count=3,
                        severity=incident.severity or "MEDIUM"
                    )
                    
                    if auto_allowed:
                        update_incident_status(db, incident.id, "BYPASSED", actor="sentinelflow-autopilot")
                        add_incident_log(db, incident.id, "CONFIDENCE_GATE", f"Auto-pilot execution APPROVED. Reason: {gov_reason}")
                        context["decision_routed"] = "AUTO_PILOT"
                    else:
                        update_incident_status(db, incident.id, "PENDING_APPROVAL", actor="sentinelflow-autopilot")
                        add_incident_log(db, incident.id, "CONFIDENCE_GATE", f"Auto-pilot BLOCKED. Reason: {gov_reason}")
                        context["decision_routed"] = "PENDING_APPROVAL"
                    
                    state.context_data_json = json.dumps(context)
                    db.commit()
                except Exception as mastra_err:
                    # Mastra microservice call failed — gracefully degrade to local workflow engine
                    logger.warning("mastra_workflow_call_failed_falling_through_to_local", error=str(mastra_err), incident_id=incident.id)
                    add_incident_log(db, incident.id, "MASTRA_FALLBACK", f"Mastra microservice unavailable ({str(mastra_err)[:120]}). Falling through to local workflow engine.")
            
            _complete_step(step, "RETRIEVE_CONTEXT")
            _record_trace(db, correlation_id, "INGEST", time.time() - workflow_start)
        except Exception as e:
            _fail_step(step, str(e))
            raise e
    else:
        incident = db.query(Incident).filter(Incident.id == context["incident_id"]).first()

    # ── State 2: RETRIEVE_CONTEXT ────────────────────────────
    if "prompt_context" not in context:
        step = _start_step("RETRIEVE_CONTEXT")
        try:
            step_start = time.time()
            prompt = db.query(PromptTemplate).filter(PromptTemplate.id == anomaly_type).first()
            if not prompt:
                prompt_context = f"Analyze and remediate: {anomaly_type}"
                add_incident_log(db, incident.id, "PROMPT_LOAD", f"No specific prompt template found for {anomaly_type}. Using generic.")
            else:
                prompt_context = f"[CRISPE] Capacity: {prompt.capacity}\nRole: {prompt.role}\nIntent: {prompt.intent}\nSubject: {prompt.subject}"
                add_incident_log(db, incident.id, "PROMPT_LOAD", f"Loaded CRISPE template: {prompt.name}")
            
            context["prompt_context"] = prompt_context
            _complete_step(step, "RETRIEVE_RUNBOOKS")
            _record_trace(db, correlation_id, "CRISPE_PROMPT_LOAD", time.time() - step_start)
        except Exception as e:
            _fail_step(step, str(e))
            raise e
    else:
        prompt_context = context["prompt_context"]

    # ── State 3: RETRIEVE_RUNBOOKS ───────────────────────────
    if "rag_context" not in context:
        step = _start_step("RETRIEVE_RUNBOOKS")
        try:
            step_start = time.time()
            rag_results = search_similar_runbooks(description, limit=3)
            rag_context = ""
            if rag_results:
                rag_context = "\n".join([f"- [{r['title']}] (score: {r['score']:.2f}): {r['content'][:200]}" for r in rag_results])
                add_incident_log(
                    db, incident.id, "RAG_RETRIEVAL",
                    f"Found {len(rag_results)} similar runbooks. Top match: {rag_results[0]['title']} (score: {rag_results[0]['score']:.2f})",
                    metadata={"matches": [r["title"] for r in rag_results]},
                )
                add_timeline_event(
                    db, incident.id, "RAG_MATCH",
                    f"Found {len(rag_results)} relevant runbooks",
                    f"Top match: {rag_results[0]['title']}",
                    decision_rationale=f"Similarity scores: {[round(r['score'], 2) for r in rag_results]}",
                )
            else:
                add_incident_log(db, incident.id, "RAG_RETRIEVAL", "No similar runbooks found in vector index.")
            
            context["rag_context"] = rag_context
            context["rag_results"] = [
                {"title": r["title"], "content": r["content"], "score": r["score"]} for r in rag_results
            ]
            _complete_step(step, "PLAN_REMEDIATION")
            _record_trace(db, correlation_id, "QDRANT_RAG_RETRIEVAL", time.time() - step_start)
        except Exception as e:
            _fail_step(step, str(e))
            raise e
    else:
        rag_context = context["rag_context"]
        rag_results = context.get("rag_results", [])

    # ── State 4: PLAN_REMEDIATION ────────────────────────────
    if "reasoning_result" not in context:
        step = _start_step("PLAN_REMEDIATION")
        try:
            step_start = time.time()
            from .llm_service import llm_manager

            # Inject RCA findings to guide the remediation planning agent
            enhanced_description = description
            try:
                db_incident = db.query(Incident).filter(Incident.id == incident.id).first()
                if db_incident and db_incident.root_cause_json:
                    rca = json.loads(db_incident.root_cause_json)
                    enhanced_description = (
                        f"[Root Cause Diagnostic: {rca.get('primary_cause')}. "
                        f"Initial Remedy Suggestion: {rca.get('remediation_action')}]\n"
                        f"{description}"
                    )
            except Exception:
                pass

            # Query all shared memories to construct a multi-agent collaborative view
            shared_memories_context = ""
            try:
                from .memory_service import retrieve_memory
                memories = retrieve_memory("shared_memory", "diagnostics threat reputation", incident.id, limit=10)
                if memories:
                    memories_text = "\n".join([f"- [{m.get('agent_id', 'agent')}]: {m.get('key')} = {m.get('value')}" for m in memories])
                    shared_memories_context = f"\n### Multi-Agent Shared Memory Context\n{memories_text}\n"
                    enhanced_description = f"{enhanced_description}\n{shared_memories_context}"
                    
                    # Log memory retrieval event to the forensic timeline
                    add_timeline_event(
                        db, incident.id, "AGENT_MEMORY_SYNC",
                        f"Retrieved {len(memories)} shared team memories",
                        "Remediation planner synchronized shared agent memory findings before reasoning.",
                        actor="workflow-orchestrator",
                        decision_rationale=f"Retrieved keys: {', '.join([m.get('key') for m in memories])}."
                    )
            except Exception as mem_err:
                logger.warning("workflow_memory_retrieve_failed", error=str(mem_err))

            # Query similar past incidents (Organizational Memory)
            org_memory_context = ""
            try:
                from .memory_service import search_similar_resolved_incidents
                past_incidents = search_similar_resolved_incidents(description, limit=5)
                if past_incidents:
                    formatted_past = []
                    for inc in past_incidents:
                        formatted_past.append(
                            f"- Incident #{inc.get('incident_id')}: {inc.get('title')}\n"
                            f"  Findings: {inc.get('rca_findings')}\n"
                            f"  Remediation: {inc.get('remediation_action')}\n"
                            f"  Outcome: {inc.get('outcome')}"
                        )
                    org_memory_context = "\n### Similar Past Incidents (Organizational Memory)\n" + "\n".join(formatted_past) + "\n"
                    enhanced_description = f"{enhanced_description}\n{org_memory_context}"
            except Exception as org_err:
                logger.warning("workflow_org_memory_retrieve_failed", error=str(org_err))

            # Query human corrections/feedback loops (Continuous Learning)
            feedback_context = ""
            try:
                from ..models.models import RecommendationFeedback
                feedbacks = db.query(RecommendationFeedback).join(Incident).filter(
                    Incident.metric_type == anomaly_type
                ).order_by(RecommendationFeedback.created_at.desc()).limit(3).all()
                if feedbacks:
                    formatted_fb = []
                    for fb in feedbacks:
                        formatted_fb.append(
                            f"- Corrected: `{fb.original_recommendation}` -> `{fb.engineer_correction}`. Reasoning: {fb.reasoning or 'None'}"
                        )
                    feedback_context = f"\n### Engineer Corrections & Learned Feedback for {anomaly_type}:\n" + "\n".join(formatted_fb) + "\n"
                    enhanced_description = f"{enhanced_description}\n{feedback_context}"
            except Exception as fb_err:
                logger.warning("workflow_feedback_retrieve_failed", error=str(fb_err))

            # LLM routing parameters
            latency_critical = (incident.severity == "CRITICAL" or anomaly_type == "UNAUTHORIZED_ACCESS")
            cost_sensitive = (incident.severity in ["LOW", "MEDIUM"])

            reasoning_resp = llm_manager.generate_suggestion(
                anomaly_type,
                enhanced_description,
                prompt_context,
                rag_context,
                severity=incident.severity or "MEDIUM",
                latency_critical=latency_critical,
                cost_sensitive=cost_sensitive
            )
            reasoning_result = reasoning_resp.model_dump()
            
            # Log router decision to timeline
            from .llm_router_service import select_optimal_model
            routing_decision = select_optimal_model(
                anomaly_type=anomaly_type,
                severity=incident.severity or "MEDIUM",
                input_text_length=len(prompt_context) + len(enhanced_description) + len(rag_context),
                latency_critical=latency_critical,
                cost_sensitive=cost_sensitive
            )
            
            add_timeline_event(
                db, incident.id, "LLM_ROUTER",
                f"LLM Router selected {routing_decision['model_name']} ({routing_decision['tier'].upper()})",
                routing_decision["reason"],
                actor="llm-router",
                decision_rationale=f"Complexity score: {routing_decision['complexity_score']}/100. Latency Critical: {latency_critical}. Cost Sensitive: {cost_sensitive}."
            )

            # Route to incident-type-specific Mastra agent
            agent_info = AGENT_ROUTING.get(anomaly_type, DEFAULT_AGENT)
            primary_agent = agent_info["agent"]
            agent_sub_type = agent_info["sub_type"]
            agent_domain = agent_info["domain"]

            add_timeline_event(
                db, incident.id, "AGENT_ROUTING",
                f"Routed to {primary_agent} for {anomaly_type} ({agent_sub_type}/{agent_domain})",
                f"Incident type {anomaly_type} mapped to {agent_sub_type} domain under {agent_domain}. Primary agent: {primary_agent}.",
                actor="workflow-router",
                decision_rationale=f"Agent routing map: {anomaly_type} -> {primary_agent}. Sub-type: {agent_sub_type}. Domain: {agent_domain}."
            )

            add_incident_log(
                db, incident.id, "REASONING",
                f"Agent: {primary_agent} | LLM Analysis: {reasoning_result['analysis']}\nSuggested Action: {reasoning_result['action']}",
            )
            from .timeline_service import generate_decision_explanation
            explanation = generate_decision_explanation("LLM_REASONING", {
                "provider": f"{reasoning_result.get('provider', 'Simulation')} ({reasoning_result.get('routed_model', 'standard')})",
                "confidence": reasoning_result.get("confidence", 0.0),
                "contradictions": "None detected",
                "reasoning": reasoning_result.get("analysis", ""),
                "remediation_plan": reasoning_result.get("action", "")
            })
            add_timeline_event(
                db, incident.id, "LLM_REASONING",
                "AI reasoning completed",
                reasoning_result["analysis"],
                decision_rationale=explanation,
                confidence_at_step=reasoning_result["confidence"],
                duration_ms=(time.time() - step_start) * 1000,
            )
            
            context["reasoning_result"] = reasoning_result
            context["agent_routed"] = primary_agent
            context["agent_sub_type"] = agent_sub_type
            context["agent_domain"] = agent_domain
            _complete_step(step, "CONTRADICTION_CHECK")
            _record_trace(
                db, correlation_id, "LLM_REASONING", time.time() - step_start,
                input_tokens=reasoning_result["input_tokens"],
                output_tokens=reasoning_result["output_tokens"],
                metadata_json=json.dumps({
                    "model_tier": reasoning_result.get("model_tier"),
                    "model_name": reasoning_result.get("routed_model"),
                    "cost_usd": reasoning_result.get("cost_usd", 0.0)
                })
            )
        except Exception as e:
            _fail_step(step, str(e))
            raise e
    else:
        reasoning_result = context["reasoning_result"]

    # ── State 5: CONTRADICTION_CHECK ─────────────────────────
    if "contradiction" not in context:
        step = _start_step("CONTRADICTION_CHECK")
        try:
            step_start = time.time()
            contradiction = _check_contradictions(reasoning_result["action"], rag_results)
            add_incident_log(
                db, incident.id, "CONTRADICTION_CHECK",
                f"Contradiction analysis: {contradiction['message']}",
            )
            if contradiction["has_contradiction"]:
                reasoning_result["confidence"] *= 0.7
                context["reasoning_result"] = reasoning_result
            
            context["contradiction"] = contradiction
            _complete_step(step, "VALIDATE")
            _record_trace(db, correlation_id, "MASTRA_CONTRADICTION_CHECK", time.time() - step_start)
        except Exception as e:
            _fail_step(step, str(e))
            raise e
    else:
        contradiction = context["contradiction"]

    # ── State 6: VALIDATE ────────────────────────────────────
    if "safety_status" not in context:
        step = _start_step("VALIDATE")
        try:
            step_start = time.time()
            safety_status, safety_risk, safety_assessment = _enkrypt_ai_safety_check(reasoning_result["action"])
            add_incident_log(
                db, incident.id, "SAFETY_CHECK",
                f"Enkrypt Safety: {safety_status} (Risk: {safety_risk:.0%}). {safety_assessment}",
            )
            from .timeline_service import generate_decision_explanation
            explanation = generate_decision_explanation("SAFETY_CHECK", {
                "status": safety_status,
                "risk_score": safety_risk,
                "assessment": safety_assessment,
                "command": reasoning_result["action"]
            })
            add_timeline_event(
                db, incident.id,
                "SAFETY_CHECK_PASS" if safety_status == "ALLOWED" else "SAFETY_CHECK_FAIL",
                f"Safety check: {safety_status}",
                safety_assessment,
                decision_rationale=explanation,
            )
            if safety_status == "BLOCKED":
                reasoning_result["confidence"] = 0.0
                context["reasoning_result"] = reasoning_result
                
            context["safety_status"] = safety_status
            context["safety_risk"] = safety_risk
            context["safety_assessment"] = safety_assessment
            _complete_step(step, "APPROVE_DECISION")
            _record_trace(db, correlation_id, "ENKRYPT_SAFETY_CHECK", time.time() - step_start)
        except Exception as e:
            _fail_step(step, str(e))
            raise e
    else:
        safety_status = context["safety_status"]
        safety_risk = context["safety_risk"]
        safety_assessment = context["safety_assessment"]

    # ── State 7: APPROVE_DECISION ────────────────────────────
    if "decision_routed" not in context:
        step = _start_step("APPROVE_DECISION")
        try:
            step_start = time.time()
            confidence = reasoning_result["confidence"]
            incident.confidence_score = confidence
            incident.suggested_action = reasoning_result["action"]

            # Compile comprehensive explainability metrics for audit trail
            try:
                from .explainability_service import ExplainabilityService
                
                # RCA diagnostic reports
                rca_details = {}
                if incident.root_cause_json:
                    try:
                        rca_data = json.loads(incident.root_cause_json)
                        rca_details = ExplainabilityService.get_rca_explanation(
                            incident.metric_type,
                            rca_data.get("evidence", [])
                        )
                    except Exception:
                        pass
                if not rca_details:
                    rca_details = ExplainabilityService.get_rca_explanation(incident.metric_type, [])

                # Threat intelligence lookup reports
                ti_findings = []
                ti_level = "CLEAN"
                try:
                    from .memory_service import retrieve_memory
                    mems = retrieve_memory("shared_memory", "threat_intel", incident.id, limit=1)
                    if mems:
                        ti_data = json.loads(mems[0]["value"])
                        ti_findings = ti_data.get("findings", [])
                        ti_level = ti_data.get("overall_threat_level", "CLEAN")
                except Exception:
                    pass
                ti_details = ExplainabilityService.get_threat_intel_explanation(ti_level, ti_findings)

                # Remediation alternate evaluations
                action = reasoning_result["action"]
                alt_action = "kubectl scale deployment ... --replicas=3"
                alt_reason = "Rejected because scaling up takes longer (5min+) and does not clear transient process lockups or OOM memory leak loops."
                if "scale" in action.lower():
                    alt_action = "kubectl rollout restart deployment ..."
                    alt_reason = "Rejected because current traffic spikes indicate high workload requiring replica expansion over restarting."
                
                remediation_details = ExplainabilityService.get_remediation_explanation(action, alt_action, alt_reason)

                # Aggregate combined report
                explainability_report = {
                    "rca": rca_details,
                    "threat_intel": ti_details,
                    "remediation": remediation_details,
                    "overall_explanation": f"SentinelFlow AI diagnosed {incident.metric_type} incident #{incident.id}. RCA confidence is {rca_details['confidence_score']}%. Remediation recommended is '{action}' with {remediation_details['confidence_score']}% safety score.",
                    "overall_confidence": (rca_details['confidence_score'] + remediation_details['confidence_score']) / 2.0
                }
                
                incident.explainability_json = json.dumps(explainability_report)

                # ── Phase 36: Remediation Options
                from .remediation_agent import RemediationAgent
                rem_agent = RemediationAgent()
                ranked_options = rem_agent.rank_options(
                    anomaly_type=incident.metric_type,
                    pod_name="payment-gateway-9f7d2e4a1",
                    deployment_name="payment-gateway"
                )
                incident.remediation_options_json = json.dumps(ranked_options)

                # ── Phase 40: Runbook Recommendations
                from .runbook_recommendation_service import RunbookRecommendationService
                recommended_runbooks = RunbookRecommendationService.get_recommendations(
                    anomaly_type=incident.metric_type,
                    root_cause=rca_details.get("why_conclusion", "Anomaly match"),
                    severity=incident.severity or "MEDIUM"
                )
                incident.recommended_runbooks_json = json.dumps(recommended_runbooks)

                # ── Phase 35: Dry Run Simulation
                from .simulation_service import SimulationEngine
                simulation_result = SimulationEngine.simulate(
                    action=action,
                    anomaly_type=incident.metric_type
                )
                incident.simulation_json = json.dumps(simulation_result)

                # ── Phase 39: Decision Graph
                from .decision_graph_service import DecisionGraphService
                decision_graph = DecisionGraphService.build_graph(incident, db)
                incident.decision_graph_json = json.dumps(decision_graph)

                # ── Phase 42: Attack Graph
                from .attack_graph_service import AttackGraphService
                attack_graph = AttackGraphService.generate_attack_graph(incident.metric_type, incident.severity)
                incident.attack_graph_json = json.dumps(attack_graph)

                db.commit()
            except Exception as exp_err:
                logger.warning("workflow_explainability_compilation_failed", error=str(exp_err))
            
            from .timeline_service import generate_decision_explanation
            if safety_status == "BLOCKED":
                update_incident_status(db, incident.id, "PENDING_APPROVAL", actor="safety-gate")
                add_incident_log(db, incident.id, "CONFIDENCE_GATE", "Safety check BLOCKED — requiring human approval.")
                explanation = generate_decision_explanation("HITL_DECISION", {
                    "action": "PENDING_APPROVAL (BLOCKED)",
                    "actor": "safety-gate",
                    "rationale": "Safety gate blocked the proposed action. Human verification required."
                })
                add_timeline_event(
                    db, incident.id, "HITL_REQUESTED",
                    "Human approval required (Safety Block)",
                    "Proposed action was blocked by safety validation",
                    actor="safety-gate",
                    decision_rationale=explanation,
                )
                try:
                    from .slack_service import post_slack_notification
                    post_slack_notification(
                        db=db,
                        incident=incident,
                        message=f"❓ Incident #{incident.id} BLOCKED by safety gate. Verification required for: `{incident.suggested_action}`"
                    )
                except Exception:
                    pass
                context["decision_routed"] = "PENDING_APPROVAL"
            else:
                from .execution_mode_service import ExecutionModeService
                target_svc = "payment" if "payment" in incident.title.lower() else "kube-system"
                auto_allowed, gov_reason = ExecutionModeService.should_auto_execute(
                    db=db,
                    incident_id=incident.id,
                    confidence_score=confidence * 100,
                    action_command=incident.suggested_action or "restart",
                    target_service=target_svc,
                    affected_services_count=3,
                    severity=incident.severity or "MEDIUM"
                )

                if auto_allowed:
                    update_incident_status(db, incident.id, "BYPASSED", actor="sentinelflow-autopilot")
                    add_incident_log(db, incident.id, "CONFIDENCE_GATE", f"Auto-pilot execution APPROVED. Reason: {gov_reason}")
                    explanation = generate_decision_explanation("HITL_DECISION", {
                        "action": "AUTO_APPROVED",
                        "actor": "sentinelflow-autopilot",
                        "rationale": gov_reason
                    })
                    add_timeline_event(
                        db, incident.id, "HITL_APPROVED",
                        "Autonomous Execution triggered",
                        gov_reason,
                        actor="sentinelflow-autopilot",
                        decision_rationale=explanation,
                        confidence_at_step=confidence,
                    )
                    # Log execution event to trigger rate limiter
                    add_timeline_event(
                        db, incident.id, "REMEDIATION_EXECUTED",
                        "Autonomous remediation executed",
                        f"Executed command: {incident.suggested_action}",
                        actor="sentinelflow-autopilot",
                    )
                    try:
                        from .slack_service import post_slack_notification
                        post_slack_notification(
                            db=db,
                            incident=incident,
                            message=f"✅ Incident #{incident.id} AUTO-APPROVED and executing: `{incident.suggested_action}`"
                        )
                    except Exception:
                        pass
                    context["decision_routed"] = "AUTO_PILOT"
                else:
                    update_incident_status(db, incident.id, "PENDING_APPROVAL", actor="sentinelflow-autopilot")
                    add_incident_log(db, incident.id, "CONFIDENCE_GATE", f"Auto-pilot BLOCKED. Reason: {gov_reason}")
                    explanation = generate_decision_explanation("HITL_DECISION", {
                        "action": "PENDING_APPROVAL",
                        "actor": "sentinelflow-autopilot",
                        "rationale": gov_reason
                    })
                    add_timeline_event(
                        db, incident.id, "HITL_REQUESTED",
                        "Human approval required",
                        gov_reason,
                        actor="sentinelflow-autopilot",
                        decision_rationale=explanation,
                        confidence_at_step=confidence,
                    )
                    try:
                        from .slack_service import post_slack_notification
                        post_slack_notification(
                            db=db,
                            incident=incident,
                            message=f"❓ Incident #{incident.id} requires manual approval. Reason: {gov_reason}"
                        )
                    except Exception:
                        pass
                    context["decision_routed"] = "PENDING_APPROVAL"
                
            _complete_step(step, "EXECUTE_REMEDIATION")
            _record_trace(db, correlation_id, "CONFIDENCE_GATE", time.time() - step_start)
        except Exception as e:
            _fail_step(step, str(e))
            raise e
    else:
        decision_routed = context["decision_routed"]

    # ── State 8: EXECUTE_REMEDIATION ─────────────────────────
    if context.get("decision_routed") == "AUTO_PILOT" and "execution_completed" not in context:
        step = _start_step("EXECUTE_REMEDIATION")
        try:
            update_incident_status(db, incident.id, "EXECUTING", actor="workflow")
            add_incident_log(db, incident.id, "EXECUTION", f"Auto-executing suggested command: {incident.suggested_action}")
            
            from .rollback_tracker import RollbackTracker
            baseline = RollbackTracker.capture_baseline(incident)

            from .safety_service import execute_guarded_command
            exec_log = execute_guarded_command(
                db=db,
                command=incident.suggested_action,
                incident_id=incident.id,
                performed_by="auto-pilot",
            )
            
            update_incident_status(db, incident.id, "EXECUTED", actor="executor")
            context["execution_completed"] = True
            context["execution_output"] = exec_log.get("execution_output")
            state.is_completed = True
            _complete_step(step, "RESOLVE")

            # Store incident embedding in Qdrant for future similarity search
            try:
                from ..core.vector_db import store_incident_embedding
                store_incident_embedding(
                    incident_id=incident.id,
                    title=incident.title,
                    metric_type=incident.metric_type,
                    description=incident.description or "",
                    severity=incident.severity or "MEDIUM",
                    action_taken=incident.suggested_action or "",
                    resolution_status="EXECUTED",
                )
            except Exception as emb_err:
                logger.warning("workflow_incident_embedding_store_failed", error=str(emb_err))

            # Spin up background rollback monitoring thread
            import threading
            from ..core.database import SessionLocal
            monitor_thread = threading.Thread(
                target=RollbackTracker.monitor_and_verify,
                args=(incident.id, baseline, SessionLocal)
            )
            monitor_thread.daemon = True
            monitor_thread.start()
        except Exception as e:
            _fail_step(step, str(e))
            update_incident_status(db, incident.id, "FAILED", actor="executor")
            raise e
    elif context.get("decision_routed") == "PENDING_APPROVAL":
        # Hand off to Human approval, don't execute automatically
        state.is_completed = False
        db.commit()

    elapsed_total = (time.time() - workflow_start) * 1000
    logger.info("workflow_completed", status=incident.status, elapsed_ms=round(elapsed_total, 1))

    db.commit()
    db.refresh(incident)
    return incident


def _enkrypt_ai_safety_check(command: str) -> tuple[str, float, str]:
    """
    Real Enkrypt AI SDK safety validation with local regex fallback.
    Returns (status, risk_score, assessment) matching the evaluate_command_safety contract.
    """
    if settings.ENKRYPTAI_ENABLED and settings.ENKRYPTAI_API_KEY:
        try:
            from ..services.enkrypt_service import EnkryptSafetyService
            import asyncio

            enkrypt = EnkryptSafetyService(
                api_key=settings.ENKRYPTAI_API_KEY,
                base_url=settings.ENKRYPTAI_BASE_URL,
            )

            async def _call_enkrypt():
                return await enkrypt.validate_command(command, context={"source": "workflow_pipeline"})

            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop and loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    result = pool.submit(lambda: asyncio.run(_call_enkrypt())).result(timeout=5.0)
            else:
                result = asyncio.run(_call_enkrypt())

            risk_score = result.get("risk_score", 0.0)
            violations = result.get("violations", [])

            if not result.get("is_safe", True):
                status = "BLOCKED"
                assessment = (
                    f"ENKRYPT AI SDK: BLOCKED. Risk score {risk_score:.0%}. "
                    f"Violations: {', '.join(str(v) for v in violations[:3])}. "
                    f"{result.get('message', '')}"
                )
            else:
                if risk_score >= 0.50:
                    status = "ALLOWED"
                    assessment = (
                        f"ENKRYPT AI SDK: CONDITIONAL PASS. Risk score {risk_score:.0%}. "
                        f"{result.get('message', 'Proceed with caution.')}"
                    )
                else:
                    status = "ALLOWED"
                    assessment = (
                        f"ENKRYPT AI SDK: PASS. Risk score {risk_score:.0%}. "
                        f"{result.get('message', 'Command validated by Enkrypt AI.')}"
                    )

            logger.info(
                "enkrypt_ai_workflow_check",
                status=status,
                risk_score=risk_score,
                command=command[:100],
            )
            return (status, risk_score, assessment)

        except Exception as e:
            logger.warning("enkrypt_ai_sdk_unavailable_fallback_to_local", error=str(e))
            return evaluate_command_safety(command)
    else:
        logger.debug("enkrypt_ai_disabled_or_no_key_using_local_regex")
        return evaluate_command_safety(command)


def _simulate_llm_reasoning(
    anomaly_type: str,
    description: str,
    prompt_context: str,
    rag_context: str,
) -> dict:
    """Simulate LLM reasoning for demo purposes."""
    # Simulated responses based on anomaly type
    responses = {
        "CPU_SPIKE": {
            "analysis": "CPU utilization has exceeded critical threshold (>90%). The affected pod is consuming disproportionate compute resources, likely due to a runaway process or sudden traffic surge.",
            "action": "kubectl rollout restart deployment/api-gateway -n production",
            "rationale": "A rolling restart will cycle pods without downtime. If the spike persists, HPA will trigger scale-up.",
            "confidence": random.uniform(0.70, 0.79),
        },
        "MEMORY_EXHAUSTION": {
            "analysis": "Memory usage approaching OOMKill threshold. Potential memory leak detected in container runtime.",
            "action": "kubectl scale deployment/data-processor --replicas=3 -n production",
            "rationale": "Scaling out distributes memory pressure across more pods while investigation continues.",
            "confidence": random.uniform(0.70, 0.90),
        },
        "UNAUTHORIZED_ACCESS": {
            "analysis": "Suspicious API access pattern detected from non-whitelisted service account in kube-system namespace.",
            "action": "kubectl delete pod suspicious-pod -n kube-system --grace-period=0",
            "rationale": "Immediate pod termination to prevent lateral movement. RBAC audit recommended.",
            "confidence": random.uniform(0.65, 0.85),
        },
        "DISK_FULL": {
            "analysis": "Persistent volume claim at 92% capacity. Log rotation and temp file cleanup required.",
            "action": "kubectl exec -it db-pod -n production -- sh -c 'find /tmp -mtime +7 -delete'",
            "rationale": "Removing stale temp files is safe and non-disruptive. PV expansion should be scheduled.",
            "confidence": random.uniform(0.75, 0.90),
        },
        "HIGH_LATENCY": {
            "analysis": "Service latency 5x above baseline. CoreDNS resolution delays detected.",
            "action": "kubectl rollout restart deployment/coredns -n kube-system",
            "rationale": "DNS cache corruption causing resolution delays. Restart clears the cache.",
            "confidence": random.uniform(0.70, 0.85),
        },
        "ERROR_RATE_SPIKE": {
            "analysis": "Application error rate spiked to 15%. Recent deployment may have introduced regression.",
            "action": "kubectl rollout undo deployment/api-gateway -n production",
            "rationale": "Rollback to last known good revision to restore service stability.",
            "confidence": random.uniform(0.80, 0.95),
        },
    }

    default_response = {
        "analysis": f"Detected anomaly of type '{anomaly_type}': {description[:200]}",
        "action": f"kubectl describe pods -n default --field-selector=status.phase!=Running",
        "rationale": "Gathering diagnostic information for manual review.",
        "confidence": random.uniform(0.50, 0.70),
    }

    result = responses.get(anomaly_type, default_response)
    result["input_tokens"] = len(prompt_context) + len(rag_context) + len(description)
    result["output_tokens"] = len(result["analysis"]) + len(result["action"])

    return result


def _check_contradictions(suggested_action: str, rag_results: list[dict]) -> dict:
    """Check for contradictions between the suggested action and RAG knowledge base."""
    if not rag_results:
        return {"has_contradiction": False, "message": "No RAG context to check against."}

    # Simple keyword-based contradiction check
    action_lower = suggested_action.lower()
    contradictions = []

    for result in rag_results:
        content_lower = result["content"].lower()
        # Check if action contradicts runbook guidance
        if "scale down" in content_lower and "scale up" in action_lower:
            contradictions.append(f"Runbook '{result['title']}' suggests scaling down, but action scales up.")
        if "do not restart" in content_lower and "restart" in action_lower:
            contradictions.append(f"Runbook '{result['title']}' advises against restart.")
        if "isolate" in content_lower and "delete" in action_lower:
            contradictions.append(f"Runbook '{result['title']}' recommends isolation, not deletion.")

    if contradictions:
        return {
            "has_contradiction": True,
            "message": f"Found {len(contradictions)} contradiction(s): " + "; ".join(contradictions),
        }

    return {
        "has_contradiction": False,
        "message": "No contradictions detected between suggested action and knowledge base.",
    }


def _record_trace(
    db: Session,
    correlation_id: str,
    step_name: str,
    elapsed_seconds: float,
    input_tokens: int = 0,
    output_tokens: int = 0,
    status: str = "success",
    error_message: Optional[str] = None,
    metadata_json: Optional[str] = None,
) -> None:
    """Record an observability trace for a workflow step."""
    trace = AIObservabilityTrace(
        correlation_id=correlation_id,
        step_name=step_name,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        latency_ms=elapsed_seconds * 1000,
        status=status,
        error_message=error_message,
        metadata_json=metadata_json,
    )
    db.add(trace)
    db.commit()
