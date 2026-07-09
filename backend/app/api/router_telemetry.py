"""
SentinelFlow AI — Telemetry Ingestion API Router
Handles metric ingestion, anomaly detection triggers, and metric history.
"""

import json
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.observability import logger
from ..middleware.auth import get_current_user
from ..models.models import User
from ..schemas.schemas import TelemetryEvent, TelemetryIngestResponse
from ..services.telemetry_service import (
    ingest_telemetry,
    get_recent_metrics,
    parse_prometheus_metrics,
    parse_kubernetes_event,
)
from ..services.workflow_service import run_incident_workflow

router = APIRouter(prefix="/telemetry", tags=["Telemetry"])


@router.post("/ingest", response_model=TelemetryIngestResponse, status_code=202)
async def ingest(
    request: Request,
    format: str = "json",
    db: Session = Depends(get_db)
):
    """
    Ingest a telemetry event. Runs anomaly detection and triggers
    the incident workflow for detected anomalies. Supports multi-format payload parsing.
    Open endpoint for high-throughput ingestion (no auth required).
    """
    # ── Read body bytes ──────────────────────────────────────
    body_bytes = await request.body()
    
    # ── Normalize metric data based on format ────────────────
    normalized = {}
    if format == "json":
        try:
            body_json = json.loads(body_bytes)
            # Validate standard TelemetryEvent fields
            event = TelemetryEvent(**body_json)
            normalized = event.model_dump()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid JSON TelemetryEvent: {e}")
            
    elif format == "prometheus":
        try:
            raw_text = body_bytes.decode("utf-8")
            normalized = parse_prometheus_metrics(raw_text)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid Prometheus exposition data: {e}")
            
    elif format == "kubernetes_event":
        try:
            body_json = json.loads(body_bytes)
            normalized = parse_kubernetes_event(body_json)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid Kubernetes v1.Event: {e}")
            
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {format}")

    # ── Process Ingestion ────────────────────────────────────
    correlation_id, anomalies = ingest_telemetry(
        db=db,
        node_name=normalized.get("node_name", "k8s-node"),
        pod_name=normalized.get("pod_name"),
        namespace=normalized.get("namespace", "default"),
        cpu_usage=normalized.get("cpu_usage", 0.0),
        memory_usage=normalized.get("memory_usage", 0.0),
        disk_usage=normalized.get("disk_usage", 0.0),
        network_rx_bytes=normalized.get("network_rx_bytes", 0.0),
        network_tx_bytes=normalized.get("network_tx_bytes", 0.0),
        requests_per_sec=normalized.get("requests_per_sec", 0.0),
        latency_ms=normalized.get("latency_ms", 0.0),
        error_rate=normalized.get("error_rate", 0.0),
    )

    # Trigger workflow for each detected anomaly with fingerprint deduplication
    from ..services.alert_fingerprinting_service import AlertFingerprintingService
    from ..models.models import IncidentLog
    from ..services.websocket_service import broadcast_incident_update

    for anomaly_type in anomalies:
        try:
            severity = "CRITICAL" if anomaly_type in ("CPU_SPIKE", "UNAUTHORIZED_ACCESS", "MEMORY_EXHAUSTION") else "WARNING"
            desc_text = (
                f"Telemetry anomaly detected: {anomaly_type}. "
                f"CPU: {normalized.get('cpu_usage') or 0.0}%, Memory: {normalized.get('memory_usage') or 0.0}%, "
                f"Latency: {normalized.get('latency_ms') or 0.0}ms, Error Rate: {normalized.get('error_rate') or 0.0}%"
            )
            svc_name = normalized.get("pod_name") or normalized.get("node_name") or "k8s-node"

            incident_id, is_new, fp_record = AlertFingerprintingService.process_incoming_alert(
                db=db,
                source="K8s Telemetry Monitor",
                alert_type=anomaly_type,
                service=svc_name,
                message=desc_text
            )

            if is_new:
                incident = run_incident_workflow(
                    db=db,
                    anomaly_type=anomaly_type,
                    description=desc_text,
                    severity=severity,
                    node_name=normalized.get("node_name", "k8s-node"),
                    pod_name=normalized.get("pod_name"),
                    correlation_id=correlation_id,
                )
                fp_record.incident_id = incident.id
                db.commit()
            else:
                # Grouped: log activity to incident history
                if incident_id:
                    log_entry = IncidentLog(
                        incident_id=incident_id,
                        stage="DEDUPLICATION",
                        message=f"Grouped identical/similar telemetry alert: {anomaly_type}. Total grouped: {fp_record.alert_count}.",
                    )
                    db.add(log_entry)
                    db.commit()

                    # Trigger WS update to update alert count on UI
                    broadcast_incident_update(
                        incident_id=incident_id,
                        status="ANALYZING",
                        severity=severity,
                        service=svc_name
                    )
        except Exception as e:
            logger.warning("telemetry_workflow_error", error=str(e))

    return TelemetryIngestResponse(
        status="accepted",
        correlation_id=correlation_id,
        anomalies_detected=anomalies,
        message=f"Ingested. {len(anomalies)} anomaly(ies) detected." if anomalies else "Ingested. No anomalies.",
    )


@router.get("/metrics")
def get_metrics(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get recent metric samples."""
    samples = get_recent_metrics(db, limit)
    return {
        "metrics": [
            {
                "id": s.id,
                "node_name": s.node_name,
                "pod_name": s.pod_name,
                "namespace": s.namespace,
                "cpu_usage": s.cpu_usage,
                "memory_usage": s.memory_usage,
                "disk_usage": s.disk_usage,
                "latency_ms": s.latency_ms,
                "error_rate": s.error_rate,
                "timestamp": s.timestamp.isoformat() if s.timestamp else None,
            }
            for s in samples
        ],
        "count": len(samples),
    }
