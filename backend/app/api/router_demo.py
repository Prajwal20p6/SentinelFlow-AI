"""
SentinelFlow AI — Demo Mode & Scenario API Router
Exposes routes to trigger simulated failure scenarios and clear test database logs.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Dict, Any

from ..core.database import get_db
from ..middleware.auth import require_role
from ..models.models import User, Incident
from ..services.workflow_service import run_incident_workflow
from ..services.simulator_service import generate_anomaly_metrics

router = APIRouter(prefix="/demo", tags=["Demo Mode"])

# ── Demo Failure Scenario Definitions ────────────────────────
SCENARIOS = {
    "CPU_SPIKE": {
        "anomaly_type": "CPU_SPIKE",
        "description": "High CPU utilization detected on node-02/api-gateway pod. Scale deployment to mitigate.",
        "severity": "CRITICAL",
        "node_name": "node-02",
        "pod_name": "api-gateway-7d8f6c5b9"
    },
    "DISK_FULL": {
        "anomaly_type": "DISK_FULL",
        "description": "Storage space exceeded 95% on infrastructure node-03. Clear persistent volume cache.",
        "severity": "WARNING",
        "node_name": "node-03",
        "pod_name": "postgres-primary-5f2c8b7d4"
    },
    "UNAUTHORIZED_ACCESS": {
        "anomaly_type": "UNAUTHORIZED_ACCESS",
        "description": "Repeated failed SSH login attempts detected from unrecognized host IP 198.51.100.42.",
        "severity": "CRITICAL",
        "node_name": "node-01",
        "pod_name": "auth-service-4a2e1b3c8"
    },
    "PHISHING_ATTACK": {
        "anomaly_type": "PHISHING_ATTACK",
        "description": "Simulated Office 365 phishing breach. PowerShell running, unusual logins from 103.45.67.12, database exfiltration. Recommends: disable user, revoke session tokens.",
        "severity": "CRITICAL",
        "node_name": "node-01",
        "pod_name": "identity-provider-9f2c"
    },
    "DDOS_ATTACK": {
        "anomaly_type": "DDOS_ATTACK",
        "description": "Traffic volume surge of 15,000 req/sec from botnet IPs 185.120.45.99. Scale resources and block firewall ports.",
        "severity": "CRITICAL",
        "node_name": "node-02",
        "pod_name": "ingress-gateway-abc1"
    },
    "DATA_BREACH": {
        "anomaly_type": "DATA_BREACH",
        "description": "Impossible travel login detected, database bulk download attempt from IP 99.88.77.66. Apply network policy block and isolate container.",
        "severity": "CRITICAL",
        "node_name": "node-03",
        "pod_name": "database-primary-z5r2"
    }
}


@router.post("/trigger")
def trigger_scenario(
    body: Dict[str, str],
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("engineer")),
):
    """
    Trigger a specific failing scenario synchronously.
    Available Scenarios: CPU_SPIKE, DISK_FULL, UNAUTHORIZED_ACCESS.
    """
    scenario_key = body.get("scenario", "CPU_SPIKE").upper()
    if scenario_key not in SCENARIOS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid scenario: '{scenario_key}'. Select one of: {list(SCENARIOS.keys())}"
        )

    sc_config = SCENARIOS[scenario_key]
    
    try:
        # Run workflow execution synchronous path
        incident = run_incident_workflow(
            db=db,
            anomaly_type=sc_config["anomaly_type"],
            description=sc_config["description"],
            severity=sc_config["severity"],
            node_name=sc_config["node_name"],
            pod_name=sc_config["pod_name"]
        )
        
        incident_id = incident.id
        
        return {
            "status": "success",
            "scenario": scenario_key,
            "incident_id": incident_id,
            "status_routed": incident.status if incident else "DETECTED",
            "suggested_action": incident.suggested_action if incident else None,
            "message": f"Demo failure scenario '{scenario_key}' triggered successfully."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to trigger scenario: {e}")


@router.post("/cleanup")
def cleanup_demo_data(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """
    Purge simulated incidents, workflow states, and execution histories from DB.
    Restricted to Admin.
    """
    try:
        db.execute(text("DELETE FROM remediation_executions"))
        db.execute(text("DELETE FROM incident_comments"))
        db.execute(text("DELETE FROM incident_logs"))
        db.execute(text("DELETE FROM timeline_events"))
        db.execute(text("DELETE FROM mastra_workflow_steps"))
        db.execute(text("DELETE FROM mastra_workflow_states"))
        db.execute(text("DELETE FROM ai_observability_traces"))
        db.execute(text("DELETE FROM audit_trails"))
        db.execute(text("DELETE FROM incidents"))
        db.commit()
        
        return {
            "status": "success",
            "message": "Demo database records successfully purged."
        }
    except Exception as cleanup_err:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to purge demo database: {cleanup_err}"
        )
