"""
SentinelFlow AI — Operations, Health & Metrics Router
Exposes Prometheus metric scraper and K8s readiness/liveness probes.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from sqlalchemy import text
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from ..core.database import get_db
from ..core.observability import METRIC_REGISTRY
from ..core.config import get_settings

router = APIRouter(tags=["Operations & Metrics"])
settings = get_settings()

@router.get("/health")
def liveness_probe():
    """Liveness probe. Checks if the service process is up."""
    return {"status": "healthy", "service": settings.PROJECT_NAME}

@router.get("/ready")
def readiness_probe(db: Session = Depends(get_db)):
    """Readiness probe. Validates PostgreSQL database and Qdrant connections."""
    # 1. Database check
    try:
        db.execute(text("SELECT 1"))
    except Exception as db_err:
        raise HTTPException(status_code=503, detail=f"Database check failed: {db_err}")
        
    # 2. Vector DB check
    try:
        from ..core.vector_db import qdrant_client
        if qdrant_client is None:
            raise ValueError("Vector database client not initialized.")
    except Exception as vec_err:
        raise HTTPException(status_code=503, detail=f"Vector Store check failed: {vec_err}")
        
    return {
        "status": "ready",
        "dependencies": {
            "database": "OK",
            "vector_store": "OK"
        }
    }

@router.get("/metrics")
def prometheus_metrics():
    """Prometheus endpoints. Emits structured metric logs for scraping."""
    latest_metrics = generate_latest(METRIC_REGISTRY)
    return Response(content=latest_metrics, media_type=CONTENT_TYPE_LATEST)


# ── Governance Config Endpoints ──────────────────────────────
from ..schemas.schemas import ExecutionConfigResponse, ExecutionConfigUpdateRequest
from ..services.execution_mode_service import ExecutionModeService
from ..middleware.auth import require_role
from ..models.models import User

@router.get("/execution-config", response_model=ExecutionConfigResponse)
def get_execution_configuration(
    db: Session = Depends(get_db)
):
    """Retrieve global autonomous execution config and safety thresholds."""
    return ExecutionModeService.get_config(db)


@router.post("/execution-config", response_model=ExecutionConfigResponse)
def update_execution_configuration(
    body: ExecutionConfigUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin"))
):
    """Update global autonomous execution config and safety thresholds (Admin only)."""
    return ExecutionModeService.update_config(
        db=db,
        mode=body.mode,
        rate_limit_per_minute=body.rate_limit_per_minute,
        min_confidence_score=body.min_confidence_score,
        max_blast_radius=body.max_blast_radius,
        restricted_services=body.restricted_services,
        low_risk_actions=body.low_risk_actions
    )


@router.get("/circuit-breakers")
def get_ops_circuit_breakers():
    """Retrieve current state and failure statistics of all protected dependency circuit breakers."""
    from ..services.circuit_breaker_service import CircuitBreakerService
    return CircuitBreakerService.get_all_status()


@router.get("/policies")
def list_ops_policies(db: Session = Depends(get_db)):
    """List all configured autopilot automation policies."""
    from ..models.models import Policy
    return db.query(Policy).all()


@router.post("/policies/{policy_id}/toggle")
def toggle_ops_policy(policy_id: int, db: Session = Depends(get_db)):
    """Toggle a policy enable/disable switch."""
    from ..models.models import Policy
    policy = db.query(Policy).filter(Policy.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    policy.enabled = not policy.enabled
    db.commit()
    db.refresh(policy)
    return {"id": policy.id, "enabled": policy.enabled, "name": policy.name}


@router.post("/policies/dry-run")
def dry_run_policy_eval(incident_id: int, db: Session = Depends(get_db)):
    """Perform a dry-run evaluation of all policies against an incident."""
    from ..models.models import Incident
    from ..services.policy_engine import PolicyEngine
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    allowed, reason, actions = PolicyEngine.evaluate_incident(db, incident)
    return {"allowed": allowed, "reason": reason, "actions": actions}


@router.get("/quotas")
def get_ops_resource_quotas(db: Session = Depends(get_db)):
    """Retrieve database, storage, redis, and LLM budget quota usage metrics."""
    from ..services.quota_service import ResourceQuotaService
    return ResourceQuotaService.get_quota_status(db)


# ── Phase 57: Live Cluster Metrics Dashboard ─────────────────────────────────

@router.get("/live-metrics")
def get_live_cluster_metrics():
    """
    Return the latest cluster-wide and per-service real-time metrics snapshot.
    Includes CPU, Memory, Latency, Error-rate, health score, time-series
    history (last 30 samples), and incident/remediation annotations.
    """
    from ..services.metrics_dashboard_service import MetricsDashboardService
    return MetricsDashboardService.get_live_metrics()


@router.get("/live-metrics/services/{service_name}")
def get_service_metrics(service_name: str):
    """Return per-service metrics from the latest snapshot."""
    from ..services.metrics_dashboard_service import MetricsDashboardService
    detail = MetricsDashboardService.get_service_detail(service_name)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"Service '{service_name}' not found in latest snapshot.")
    return detail


@router.post("/live-metrics/annotations")
def add_metrics_annotation(
    event_type: str,
    label: str,
    severity: str = "INFO",
    incident_id: Optional[int] = None,
):
    """Manually add an annotation to the cluster metrics time-series."""
    from ..services.metrics_dashboard_service import MetricsDashboardService
    MetricsDashboardService.add_annotation(event_type, label, severity, incident_id)
    return {"status": "annotation_added", "event_type": event_type, "label": label}


# ── Phase 58: Playbook Execution Tracking ────────────────────────────────────

@router.get("/playbook-executions")
def list_playbook_executions():
    """List all tracked playbook executions (newest first)."""
    from ..services.playbook_execution_service import PlaybookExecutionService
    return PlaybookExecutionService.get_all_executions()


@router.get("/playbook-executions/incident/{incident_id}")
def list_incident_playbook_executions(incident_id: int):
    """List all playbook executions for a specific incident."""
    from ..services.playbook_execution_service import PlaybookExecutionService
    return PlaybookExecutionService.get_executions_for_incident(incident_id)


@router.get("/playbook-executions/{execution_id}")
def get_playbook_execution(execution_id: str):
    """Retrieve a single playbook execution by its UUID."""
    from ..services.playbook_execution_service import PlaybookExecutionService
    record = PlaybookExecutionService.get_execution(execution_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Playbook execution not found.")
    return record


@router.post("/playbook-executions")
def start_playbook_execution(
    incident_id: int,
    playbook_name: str,
    db: Session = Depends(get_db),
):
    """
    Start a new playbook execution tracking session for an incident.
    Returns the execution record including UUID and step list.
    """
    from ..services.playbook_execution_service import PlaybookExecutionService
    from ..services.metrics_dashboard_service import MetricsDashboardService

    record = PlaybookExecutionService.start_execution(
        incident_id=incident_id,
        playbook_name=playbook_name,
        actor="sre-operator",
    )

    # Annotate the cluster metrics timeline
    MetricsDashboardService.add_annotation(
        event_type="PLAYBOOK_STARTED",
        label=f"Playbook '{playbook_name}' started for incident #{incident_id}",
        severity="INFO",
        incident_id=incident_id,
    )

    return record


@router.post("/playbook-executions/{execution_id}/advance")
def advance_playbook_step(
    execution_id: str,
    success: bool = True,
    log_message: Optional[str] = None,
):
    """
    Advance a playbook execution to the next step.
    Pass success=False to mark the current step as FAILED and abort.
    """
    from ..services.playbook_execution_service import PlaybookExecutionService
    record = PlaybookExecutionService.advance_step(execution_id, success, log_message)
    if record is None:
        raise HTTPException(status_code=404, detail="Playbook execution not found.")
    return record


@router.post("/playbook-executions/{execution_id}/log")
def append_playbook_log(execution_id: str, message: str):
    """Append a log line to the current step of a running execution."""
    from ..services.playbook_execution_service import PlaybookExecutionService
    record = PlaybookExecutionService.append_log(execution_id, message)
    if record is None:
        raise HTTPException(status_code=404, detail="Playbook execution not found.")
    return record


@router.post("/playbook-executions/{execution_id}/cancel")
def cancel_playbook_execution(execution_id: str):
    """Cancel a running playbook execution."""
    from ..services.playbook_execution_service import PlaybookExecutionService
    from ..services.metrics_dashboard_service import MetricsDashboardService

    record = PlaybookExecutionService.cancel_execution(execution_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Playbook execution not found.")

    MetricsDashboardService.add_annotation(
        event_type="PLAYBOOK_CANCELLED",
        label=f"Playbook '{record['playbook_name']}' cancelled for incident #{record['incident_id']}",
        severity="WARNING",
        incident_id=record["incident_id"],
    )
    return record
