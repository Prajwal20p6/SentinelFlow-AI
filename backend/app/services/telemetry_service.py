"""
SentinelFlow AI — Telemetry Ingestion & Anomaly Detection Service
Handles metric ingestion, schema validation, anomaly heuristics, and ML-based detection.
"""

import time
import json
import re
import numpy as np
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session

from ..core.security import generate_correlation_id
from ..core.redis_streams import stream_bus
from ..models.models import MetricSample, AIObservabilityTrace


# ── Anomaly Detection Thresholds ─────────────────────────────
ANOMALY_THRESHOLDS = {
    "cpu_critical": 90.0,
    "cpu_warning": 75.0,
    "memory_critical": 90.0,
    "memory_warning": 80.0,
    "disk_critical": 90.0,
    "latency_critical": 5000.0,  # ms
    "error_rate_critical": 10.0,  # %
}

# Rolling window for statistical anomaly detection
_metric_history: list[dict] = []
MAX_HISTORY = 500


def ingest_telemetry(
    db: Session,
    node_name: str,
    pod_name: Optional[str],
    namespace: str,
    cpu_usage: float,
    memory_usage: float,
    disk_usage: float = 0.0,
    network_rx_bytes: float = 0.0,
    network_tx_bytes: float = 0.0,
    requests_per_sec: float = 0.0,
    latency_ms: float = 0.0,
    error_rate: float = 0.0,
) -> tuple[str, list[str]]:
    """
    Ingest a telemetry event:
    1. Persist to database
    2. Publish to Redis Streams
    3. Run anomaly detection
    4. Record observability trace
    Returns (correlation_id, list of anomaly types detected).
    """
    start = time.time()
    correlation_id = generate_correlation_id()

    # ── 1. Persist metric sample ─────────────────────────────
    sample = MetricSample(
        node_name=node_name,
        pod_name=pod_name or "unknown",
        namespace=namespace,
        cpu_usage=cpu_usage,
        memory_usage=memory_usage,
        disk_usage=disk_usage,
        network_rx_bytes=network_rx_bytes,
        network_tx_bytes=network_tx_bytes,
        requests_per_sec=requests_per_sec,
        latency_ms=latency_ms,
        error_rate=error_rate,
    )
    db.add(sample)
    db.commit()

    # ── 2. Publish to stream ─────────────────────────────────
    stream_bus.publish("telemetry:raw", {
        "correlation_id": correlation_id,
        "node": node_name,
        "pod": pod_name or "unknown",
        "namespace": namespace,
        "cpu": cpu_usage,
        "memory": memory_usage,
        "disk": disk_usage,
        "latency": latency_ms,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    # ── 3. Anomaly detection ─────────────────────────────────
    anomalies = _detect_anomalies(cpu_usage, memory_usage, disk_usage, latency_ms, error_rate)

    # ── 4. Statistical anomaly (Z-score) ────────────────────
    stat_anomalies = _statistical_anomaly_check(cpu_usage, memory_usage, latency_ms)
    anomalies.extend(stat_anomalies)

    # ── 5. Record trace ──────────────────────────────────────
    elapsed = (time.time() - start) * 1000
    trace = AIObservabilityTrace(
        correlation_id=correlation_id,
        step_name="INGEST",
        input_tokens=len(json.dumps({"cpu": cpu_usage, "mem": memory_usage})),
        output_tokens=len(json.dumps(anomalies)),
        latency_ms=elapsed,
        status="success",
    )
    db.add(trace)

    if anomalies:
        anomaly_trace = AIObservabilityTrace(
            correlation_id=correlation_id,
            step_name="ANOMALY_DETECTION",
            latency_ms=elapsed,
            status="success",
            metadata_json=json.dumps({"anomalies": anomalies}),
        )
        db.add(anomaly_trace)

    db.commit()

    return correlation_id, anomalies


def _detect_anomalies(
    cpu: float, memory: float, disk: float, latency: float, error_rate: float
) -> list[str]:
    """Rule-based anomaly detection using configurable thresholds."""
    anomalies = []

    if cpu >= ANOMALY_THRESHOLDS["cpu_critical"]:
        anomalies.append("CPU_SPIKE")
    elif cpu >= ANOMALY_THRESHOLDS["cpu_warning"]:
        anomalies.append("CPU_WARNING")

    if memory >= ANOMALY_THRESHOLDS["memory_critical"]:
        anomalies.append("MEMORY_EXHAUSTION")
    elif memory >= ANOMALY_THRESHOLDS["memory_warning"]:
        anomalies.append("MEMORY_WARNING")

    if disk >= ANOMALY_THRESHOLDS["disk_critical"]:
        anomalies.append("DISK_FULL")

    if latency >= ANOMALY_THRESHOLDS["latency_critical"]:
        anomalies.append("HIGH_LATENCY")

    if error_rate >= ANOMALY_THRESHOLDS["error_rate_critical"]:
        anomalies.append("ERROR_RATE_SPIKE")

    return anomalies


def _statistical_anomaly_check(cpu: float, memory: float, latency: float) -> list[str]:
    """Z-score based anomaly detection using rolling window."""
    global _metric_history

    _metric_history.append({"cpu": cpu, "memory": memory, "latency": latency})
    if len(_metric_history) > MAX_HISTORY:
        _metric_history = _metric_history[-MAX_HISTORY:]

    if len(_metric_history) < 30:
        return []  # Need minimum data for statistics

    anomalies = []
    for metric_name in ["cpu", "memory", "latency"]:
        values = [m[metric_name] for m in _metric_history]
        mean = np.mean(values)
        std = np.std(values)

        if std > 0:
            z_score = (values[-1] - mean) / std
            if abs(z_score) > 3.0:  # 3-sigma rule
                anomalies.append(f"STATISTICAL_{metric_name.upper()}_ANOMALY")

    return anomalies


def get_recent_metrics(db: Session, limit: int = 50) -> list[MetricSample]:
    """Get the most recent metric samples."""
    return (
        db.query(MetricSample)
        .order_by(MetricSample.timestamp.desc())
        .limit(limit)
        .all()
    )


def parse_prometheus_metrics(raw_text: str) -> dict:
    """
    Parse Prometheus text exposition format into a normalized metric dictionary.
    """
    metrics = {
        "node_name": "unknown-node",
        "pod_name": None,
        "namespace": "default",
        "cpu_usage": 0.0,
        "memory_usage": 0.0,
        "disk_usage": 0.0,
        "network_rx_bytes": 0.0,
        "network_tx_bytes": 0.0,
        "requests_per_sec": 0.0,
        "latency_ms": 0.0,
        "error_rate": 0.0,
    }
    
    # Try to extract node name from labels
    node_match = re.search(r'node="([^"]+)"', raw_text)
    if node_match:
        metrics["node_name"] = node_match.group(1)
        
    pod_match = re.search(r'pod="([^"]+)"', raw_text)
    if pod_match:
        metrics["pod_name"] = pod_match.group(1)

    namespace_match = re.search(r'namespace="([^"]+)"', raw_text)
    if namespace_match:
        metrics["namespace"] = namespace_match.group(1)

    # Parse key metric lines
    for line in raw_text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        
        parts = line.split()
        if len(parts) < 2:
            continue
            
        metric_name_with_labels = parts[0]
        try:
            value = float(parts[-1])
        except ValueError:
            continue
            
        if "node_cpu_utilization" in metric_name_with_labels:
            metrics["cpu_usage"] = value
        elif "node_memory_utilization" in metric_name_with_labels:
            metrics["memory_usage"] = value
        elif "node_disk_utilization" in metric_name_with_labels:
            metrics["disk_usage"] = value
        elif "http_request_duration_ms" in metric_name_with_labels:
            metrics["latency_ms"] = value
        elif "http_requests_errors" in metric_name_with_labels:
            metrics["error_rate"] = value
            
    return metrics


def parse_kubernetes_event(event_json: dict) -> dict:
    """
    Parse a Kubernetes v1.Event resource into normalized metrics.
    """
    metadata = event_json.get("metadata", {})
    involved_object = event_json.get("involvedObject", {})
    reason = event_json.get("reason", "")
    message = event_json.get("message", "")
    
    metrics = {
        "node_name": involved_object.get("nodeName") or "k8s-node",
        "pod_name": involved_object.get("name") if involved_object.get("kind") == "Pod" else None,
        "namespace": involved_object.get("namespace", "default"),
        "cpu_usage": 0.0,
        "memory_usage": 0.0,
        "disk_usage": 0.0,
        "network_rx_bytes": 0.0,
        "network_tx_bytes": 0.0,
        "requests_per_sec": 0.0,
        "latency_ms": 0.0,
        "error_rate": 0.0,
    }
    
    if reason == "OOMKilled" or "OOMKilled" in message:
        metrics["memory_usage"] = 99.9  # Triggers MEMORY_EXHAUSTION
    elif reason in ("FailedScheduling", "Evicted"):
        metrics["disk_usage"] = 95.0    # Triggers DISK_FULL
    elif reason == "BackOff" or "Back-off restarting" in message:
        metrics["error_rate"] = 100.0   # Triggers ERROR_RATE_SPIKE
        
    return metrics
