"""
SentinelFlow AI — Phase 57: Real-Time Cluster Metrics Dashboard Service
Aggregates cluster-wide and service-specific metrics for live dashboard updates.
Provides time-series snapshots with incident and remediation annotations.
"""

from __future__ import annotations

import random
import time
from collections import deque
from datetime import datetime, timezone
from typing import Any, Deque, Dict, List, Optional

from ..core.observability import logger

# ── Rolling window of metric snapshots (last 30 samples per series) ─────────
_MAX_HISTORY = 30
_metric_series: Deque[Dict[str, Any]] = deque(maxlen=_MAX_HISTORY)
_annotation_log: Deque[Dict[str, Any]] = deque(maxlen=100)

# ── Service names tracked per-service ───────────────────────────────────────
_TRACKED_SERVICES = [
    "api-gateway",
    "auth-service",
    "payment-gateway",
    "data-processor",
    "notification-svc",
    "ml-inference",
    "redis-cache",
    "postgres",
]


class MetricsDashboardService:
    """
    Aggregates cluster-wide and per-service metrics into live dashboard snapshots.
    Integrates with WebSocket broadcast loop (5-second intervals) and annotates
    incident and remediation events on the time-series.
    """

    # ── Public API ───────────────────────────────────────────────────────────

    @classmethod
    def capture_snapshot(cls) -> Dict[str, Any]:
        """
        Generate and store a new cluster metric snapshot.
        Called every 5 seconds by the background broadcast task in main.py.
        Returns the snapshot dict (also saved to the rolling history).
        """
        snapshot = cls._build_snapshot()
        _metric_series.append(snapshot)
        logger.debug("metrics_snapshot_captured", timestamp=snapshot["timestamp"])
        return snapshot

    @classmethod
    def get_live_metrics(cls) -> Dict[str, Any]:
        """
        Return the full payload delivered to the frontend:
          - cluster_summary: aggregate CPU / Memory / Latency / Error-rate
          - service_metrics: per-service breakdown
          - time_series: last N snapshots for sparklines
          - annotations: recent incident and remediation events
        """
        history = list(_metric_series)

        if not history:
            # Return an empty-but-valid structure before first snapshot
            snapshot = cls.capture_snapshot()
            history = [snapshot]

        latest = history[-1]

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "cluster_summary": latest.get("cluster_summary", {}),
            "service_metrics": latest.get("service_metrics", []),
            "time_series": [
                {
                    "timestamp": h["timestamp"],
                    "cpu": h["cluster_summary"]["avg_cpu"],
                    "memory": h["cluster_summary"]["avg_memory"],
                    "latency": h["cluster_summary"]["avg_latency_ms"],
                    "error_rate": h["cluster_summary"]["avg_error_rate"],
                    "incident_count": h["cluster_summary"].get("active_incidents", 0),
                }
                for h in history
            ],
            "annotations": list(_annotation_log)[-20:],  # last 20 annotations
            "history_size": len(history),
        }

    @classmethod
    def add_annotation(
        cls,
        event_type: str,
        label: str,
        severity: str = "INFO",
        incident_id: Optional[int] = None,
    ) -> None:
        """
        Record an incident or remediation annotation onto the time-series.
        Called by workflow_service and remediation paths when key events occur.
        """
        annotation = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,   # e.g. "INCIDENT_DETECTED", "REMEDIATION_STARTED"
            "label": label,
            "severity": severity,       # INFO / WARNING / CRITICAL / SUCCESS
            "incident_id": incident_id,
        }
        _annotation_log.append(annotation)
        logger.info(
            "metrics_annotation_added",
            event_type=event_type,
            label=label,
            incident_id=incident_id,
        )

    @classmethod
    def get_service_detail(cls, service_name: str) -> Optional[Dict[str, Any]]:
        """Return per-service metrics from the latest snapshot."""
        history = list(_metric_series)
        if not history:
            return None
        latest = history[-1]
        for svc in latest.get("service_metrics", []):
            if svc["name"] == service_name:
                return svc
        return None

    # ── Private Helpers ──────────────────────────────────────────────────────

    @classmethod
    def _build_snapshot(cls) -> Dict[str, Any]:
        """Build a single metric snapshot with realistic simulated data."""
        ts = datetime.now(timezone.utc).isoformat()

        service_metrics: List[Dict[str, Any]] = []
        cpu_values, mem_values, lat_values, err_values = [], [], [], []

        for svc in _TRACKED_SERVICES:
            cpu = round(random.gauss(38, 15), 1)
            cpu = max(5.0, min(99.9, cpu))

            memory = round(random.gauss(47, 12), 1)
            memory = max(10.0, min(99.9, memory))

            latency = round(abs(random.gauss(55, 25)), 1)
            error_rate = round(random.uniform(0, 3.5), 2)

            # Occasionally spike a service for realism
            if random.random() < 0.04:
                cpu = round(random.uniform(85, 99), 1)
                latency = round(random.uniform(300, 800), 1)
                error_rate = round(random.uniform(5, 20), 2)

            svc_status = (
                "DEGRADED"
                if (cpu > 85 or memory > 90 or error_rate > 10)
                else "HEALTHY"
            )

            service_metrics.append(
                {
                    "name": svc,
                    "cpu_usage": cpu,
                    "memory_usage": memory,
                    "latency_ms": latency,
                    "error_rate": error_rate,
                    "requests_per_sec": round(random.uniform(10, 250), 1),
                    "status": svc_status,
                    "timestamp": ts,
                }
            )

            cpu_values.append(cpu)
            mem_values.append(memory)
            lat_values.append(latency)
            err_values.append(error_rate)

        avg_cpu = round(sum(cpu_values) / len(cpu_values), 1) if cpu_values else 0.0
        avg_mem = round(sum(mem_values) / len(mem_values), 1) if mem_values else 0.0
        avg_lat = round(sum(lat_values) / len(lat_values), 1) if lat_values else 0.0
        avg_err = round(sum(err_values) / len(err_values), 2) if err_values else 0.0

        # Determine cluster health score (0-100, higher = healthier)
        health_score = 100 - (avg_cpu * 0.3 + avg_mem * 0.3 + min(avg_lat / 10, 20) + min(avg_err * 2, 20))
        health_score = max(0, round(health_score, 1))

        # Count degraded services
        degraded_count = sum(1 for s in service_metrics if s["status"] == "DEGRADED")

        return {
            "timestamp": ts,
            "cluster_summary": {
                "avg_cpu": avg_cpu,
                "avg_memory": avg_mem,
                "avg_latency_ms": avg_lat,
                "avg_error_rate": avg_err,
                "health_score": health_score,
                "degraded_services": degraded_count,
                "total_services": len(_TRACKED_SERVICES),
                "active_incidents": degraded_count,  # proxy; real count from DB
                "status": "DEGRADED" if degraded_count > 0 else "HEALTHY",
            },
            "service_metrics": service_metrics,
        }
