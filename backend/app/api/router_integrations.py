"""
SentinelFlow AI — Integrations API Router
Slack webhooks, notification management, external service connectors.
"""

import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from ..core.database import get_db
from ..middleware.auth import get_current_user
from ..models.models import User, NotificationLog, Incident
from ..schemas.schemas import SlackWebhookPayload, NotificationLogResponse
from ..services.incident_service import update_incident_status

router = APIRouter(prefix="/integrations", tags=["Integrations"])


@router.post("/slack/webhook")
def slack_webhook_receiver(
    payload: SlackWebhookPayload,
    db: Session = Depends(get_db),
):
    """
    Receive Slack interactive webhook callbacks.
    Handles approval/rejection actions from Slack buttons.
    """
    # Log the notification
    log = NotificationLog(
        incident_id=payload.incident_id,
        channel="slack",
        recipient=payload.channel or "#sentinelflow-alerts",
        message=payload.text or f"Slack action: {payload.action}",
        status="delivered",
        response_action=payload.action,
    )
    db.add(log)
    db.commit()

    result = {"status": "received", "action": payload.action}

    # Process approval/rejection actions
    if payload.action and payload.incident_id:
        try:
            if payload.action == "approve":
                incident = update_incident_status(
                    db, payload.incident_id, "APPROVED",
                    actor="slack-bot",
                    reason="Approved via Slack interactive button",
                )
                # Auto-execute
                incident = update_incident_status(db, payload.incident_id, "EXECUTING", actor="workflow")
                
                # Execute the suggested command via safety gate
                if incident.suggested_action:
                    from ..services.safety_service import execute_guarded_command
                    execute_guarded_command(
                        db=db,
                        command=incident.suggested_action,
                        incident_id=incident.id,
                        performed_by="slack-bot",
                    )
                    
                incident = update_incident_status(db, payload.incident_id, "EXECUTED", actor="executor")
                result["message"] = f"Incident #{payload.incident_id} approved and executed."
            elif payload.action == "reject":
                incident = update_incident_status(
                    db, payload.incident_id, "REJECTED",
                    actor="slack-bot",
                    reason="Rejected via Slack interactive button",
                )
                result["message"] = f"Incident #{payload.incident_id} rejected."
        except ValueError as e:
            result["error"] = str(e)

    return result


@router.get("/notifications")
def get_notifications(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get notification history."""
    logs = (
        db.query(NotificationLog)
        .order_by(NotificationLog.timestamp.desc())
        .limit(limit)
        .all()
    )
    return {
        "notifications": [NotificationLogResponse.model_validate(n) for n in logs],
        "count": len(logs),
    }


def send_slack_notification(
    db: Session,
    incident_id: int,
    message: str,
    channel: str = "#sentinelflow-alerts",
) -> None:
    """Send a Slack notification (simulated for hackathon)."""
    import requests as req_lib
    from ..core.config import get_settings

    settings = get_settings()

    payload = {
        "text": message,
        "channel": channel,
        "incident_id": incident_id,
    }

    try:
        response = req_lib.post(
            settings.SLACK_WEBHOOK_URL,
            json=payload,
            timeout=5,
        )
        status = "delivered" if response.status_code == 200 else "failed"
    except Exception:
        status = "failed"

    log = NotificationLog(
        incident_id=incident_id,
        channel="slack",
        recipient=channel,
        message=message,
        status=status,
    )
    db.add(log)
    db.commit()


# ── Threat Intelligence Ingestion API & Webhooks ──────────────

import time
from collections import defaultdict
from fastapi import Header, Body
from typing import Dict, Any
from ..schemas.schemas import NormalizedAlert
from ..services.incident_service import create_incident

ALERT_RATE_LIMITS = defaultdict(list)


def verify_threat_intel_key(x_api_key: str = Header(..., description="Threat Intel Ingestion API key")) -> str:
    """Validate integration-specific API key for ingestion endpoints."""
    from ..core.config import get_settings
    settings = get_settings()
    if x_api_key != settings.THREAT_INTEL_API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid threat intelligence API key.")
    return x_api_key


@router.post("/alerts", status_code=201)
def ingest_normalized_alert(
    payload: NormalizedAlert,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_threat_intel_key)
) -> Dict[str, Any]:
    """
    Ingest normalized security alert from external platforms (Splunk, Microsoft Sentinel).
    Extracts, caches, and enriches threat intelligence indicators.
    """
    # 1. Source-based Rate Limiting (60 requests per minute per unique source)
    now = time.time()
    source_bucket = ALERT_RATE_LIMITS[payload.source]
    source_bucket[:] = [t for t in source_bucket if now - t < 60]
    if len(source_bucket) >= 60:
        raise HTTPException(status_code=429, detail=f"Rate limit exceeded for alert source: {payload.source}")
    source_bucket.append(now)

    # 2. Map normalized fields to Incident database model
    alert_iocs_str = ", ".join([f"{ioc.type}:{ioc.value}" for ioc in payload.iocs])
    raw_info = json.dumps(payload.raw_data or {})
    description = (
        f"Ingested alert from {payload.source}.\n"
        f"Alert Type: {payload.alert_type}\n"
        f"Indicators: {alert_iocs_str}\n"
        f"Raw context: {raw_info}"
    )

    incident = create_incident(
        db=db,
        source=payload.source,
        metric_type=payload.alert_type,
        severity=payload.severity.upper(),
        title=f"Security Alert from {payload.source}: {payload.alert_type}",
        description=description
    )

    # 3. Automatically execute Threat Intelligence auto-enrichment pipeline
    try:
        from ..services.threat_intel_service import auto_enrich_incident_threats
        enrich_result = auto_enrich_incident_threats(db, incident.id)
    except Exception as e:
        enrich_result = {"error": str(e)}

    db.refresh(incident)

    return {
        "status": "ingested",
        "incident_id": incident.id,
        "correlation_id": incident.correlation_id,
        "threat_enrichment": enrich_result
    }


@router.post("/webhooks/splunk", status_code=201)
def splunk_webhook_receiver(
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_threat_intel_key)
) -> Dict[str, Any]:
    """
    Splunk webhook mapper. Transposes Splunk alerts to normalized ingestion schemas.
    """
    # Map splunk keys: sid, search_name, result
    result = payload.get("result", {})
    alert_type = payload.get("search_name", "Splunk Alert")
    severity = result.get("severity", "WARNING").upper()
    message = result.get("message", "No message details provided.")
    src_ip = result.get("src_ip")
    
    iocs = []
    if src_ip:
        iocs.append({"type": "ip", "value": src_ip})

    normalized = NormalizedAlert(
        source="Splunk",
        alert_type=alert_type,
        severity=severity,
        iocs=iocs,
        raw_data={"splunk_payload": payload}
    )

    return ingest_normalized_alert(normalized, db=db, api_key=api_key)


@router.post("/webhooks/sentinel", status_code=201)
def sentinel_webhook_receiver(
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_threat_intel_key)
) -> Dict[str, Any]:
    """
    Microsoft Sentinel webhook mapper. Transposes Sentinel alert schema to normalized schema.
    """
    properties = payload.get("properties", {})
    alert_type = properties.get("title", "Sentinel Security Alert")
    severity = properties.get("severity", "WARNING").upper()
    description = properties.get("description", "No description provided.")
    
    # Extract IOCs dynamically from description
    from ..services.threat_intel_service import extract_iocs_from_text
    extracted = extract_iocs_from_text(description)
    iocs = [{"type": x["type"], "value": x["value"]} for x in extracted]

    normalized = NormalizedAlert(
        source="Microsoft Sentinel",
        alert_type=alert_type,
        severity=severity,
        iocs=iocs,
        raw_data={"sentinel_payload": payload}
    )

    return ingest_normalized_alert(normalized, db=db, api_key=api_key)

