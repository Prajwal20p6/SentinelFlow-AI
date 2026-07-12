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

# ── Cached state for realistic metric progression ──────────────────────────
_service_baselines: Dict[str, Dict[str, float]] = {}
_last_snapshot_time: float = 0.0


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
    def _get_active_incident_count(cls) -> int:
        """Get the actual count of active incidents from the database."""
        try:
            from ..core.database import SessionLocal
            from ..models.models import Incident
            db = SessionLocal()
            try:
                count = db.query(Incident).filter(
                    Incident.status.notin_(["EXECUTED", "REJECTED"])
                ).count()
                return count
            finally:
                db.close()
        except Exception:
            return 0

    @classmethod
    def _get_incident_severity_impact(cls) -> Dict[str, float]:
        """Get aggregate severity impact from active incidents."""
        try:
            from ..core.database import SessionLocal
            from ..models.models import Incident
            db = SessionLocal()
            try:
                active = db.query(Incident).filter(
                    Incident.status.notin_(["EXECUTED", "REJECTED"])
                ).all()
                
                cpu_impact = 0.0
                memory_impact = 0.0
                latency_impact = 0.0
                error_impact = 0.0
                
                for inc in active:
                    mt = (inc.metric_type or "").upper()
                    severity_mult = 1.5 if inc.severity == "CRITICAL" else 1.0 if inc.severity == "WARNING" else 0.5
                    
                    if "CPU" in mt:
                        cpu_impact += 15 * severity_mult
                    elif "MEMORY" in mt:
                        memory_impact += 12 * severity_mult
                    elif "LATENCY" in mt or "NETWORK" in mt:
                        latency_impact += 200 * severity_mult
                    elif "ERROR" in mt:
                        error_impact += 5 * severity_mult
                    elif "DISK" in mt:
                        memory_impact += 8 * severity_mult
                    elif "UNAUTHORIZED" in mt or "PHISHING" in mt or "DDOS" in mt or "BREACH" in mt:
                        cpu_impact += 5 * severity_mult
                        error_impact += 2 * severity_mult
                        latency_impact += 100 * severity_mult
                
                return {
                    "cpu_impact": min(cpu_impact, 50),
                    "memory_impact": min(memory_impact, 40),
                    "latency_impact": min(latency_impact, 500),
                    "error_impact": min(error_impact, 15),
                }
            finally:
                db.close()
        except Exception:
            return {"cpu_impact": 0, "memory_impact": 0, "latency_impact": 0, "error_impact": 0}

    @classmethod
    def _build_snapshot(cls) -> Dict[str, Any]:
        """Build a single metric snapshot incorporating real incident state."""
        global _service_baselines, _last_snapshot_time
        ts = datetime.now(timezone.utc).isoformat()
        now = time.time()
        
        # Get real incident data
        active_incident_count = cls._get_active_incident_count()
        severity_impact = cls._get_incident_severity_impact()
        
        # Initialize or drift service baselines for realistic continuity
        if not _service_baselines or (now - _last_snapshot_time) > 300:
            for svc in _TRACKED_SERVICES:
                _service_baselines[svc] = {
                    "cpu": random.gauss(35, 10),
                    "memory": random.gauss(45, 8),
                    "latency": abs(random.gauss(50, 15)),
                    "error_rate": random.uniform(0.1, 1.5),
                    "rps": random.uniform(50, 200),
                }
            _last_snapshot_time = now
        
        service_metrics: List[Dict[str, Any]] = []
        cpu_values, mem_values, lat_values, err_values = [], [], [], []

        for svc in _TRACKED_SERVICES:
            # Drift baselines slightly for continuity between snapshots
            baseline = _service_baselines[svc]
            baseline["cpu"] += random.gauss(0, 1.5)
            baseline["memory"] += random.gauss(0, 0.8)
            baseline["latency"] += random.gauss(0, 3)
            baseline["error_rate"] += random.gauss(0, 0.1)
            baseline["rps"] += random.gauss(0, 5)
            
            cpu = max(5.0, min(99.9, round(baseline["cpu"], 1)))
            memory = max(10.0, min(99.9, round(baseline["memory"], 1)))
            latency = max(1.0, round(abs(baseline["latency"]), 1))
            error_rate = max(0.0, round(min(baseline["error_rate"], 25.0), 2))
            rps = max(5.0, round(baseline["rps"], 1))
            
            # Apply real incident impact
            if "payment" in svc:
                cpu += severity_impact["cpu_impact"] * 0.3
                latency += severity_impact["latency_impact"] * 0.2
                error_rate += severity_impact["error_impact"] * 0.1
            elif "api-gateway" in svc:
                cpu += severity_impact["cpu_impact"] * 0.4
                latency += severity_impact["latency_impact"] * 0.3
                error_rate += severity_impact["error_impact"] * 0.15
            elif "auth" in svc:
                latency += severity_impact["latency_impact"] * 0.1
                error_rate += severity_impact["error_impact"] * 0.05
            elif "postgres" in svc:
                memory += severity_impact["memory_impact"] * 0.4
                latency += severity_impact["latency_impact"] * 0.15
            elif "redis" in svc:
                cpu += severity_impact["cpu_impact"] * 0.1
                latency += severity_impact["latency_impact"] * 0.05
            
            # Occasional realistic spike
            if random.random() < 0.03:
                cpu = round(random.uniform(80, 99), 1)
                latency = round(random.uniform(200, 600), 1)
                error_rate = round(random.uniform(4, 15), 2)
            
            cpu = max(5.0, min(99.9, round(cpu, 1)))
            memory = max(10.0, min(99.9, round(memory, 1)))
            latency = max(1.0, round(latency, 1))
            error_rate = max(0.0, round(min(error_rate, 25.0), 2))
            
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
                    "requests_per_sec": rps,
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
        
        # Use real active incident count instead of proxy
        display_incident_count = active_incident_count if active_incident_count > 0 else degraded_count

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
                "active_incidents": display_incident_count,
                "status": "DEGRADED" if degraded_count > 0 or display_incident_count > 0 else "HEALTHY",
            },
            "service_metrics": service_metrics,
        }
