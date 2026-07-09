"""
SentinelFlow AI — Demo Simulator Service
Generates realistic telemetry data, periodic anomalies, and test incidents.
"""

import time
import random
import threading
from datetime import datetime, timezone

from ..core.database import SessionLocal
from ..core.redis_streams import stream_bus
from ..core.observability import logger


# ── Simulated Pod Topology ──────────────────────────────────
SIMULATED_PODS = [
    {"name": "api-gateway-7d8f6c5b9", "namespace": "production", "node": "node-01", "service": "api-gateway"},
    {"name": "auth-service-4a2e1b3c8", "namespace": "production", "node": "node-01", "service": "auth-service"},
    {"name": "payment-gateway-9f7d2e4a1", "namespace": "production", "node": "node-02", "service": "payment-gateway"},
    {"name": "data-processor-6c3b8a1e5", "namespace": "production", "node": "node-02", "service": "data-processor"},
    {"name": "notification-svc-2d9e7f4c3", "namespace": "production", "node": "node-03", "service": "notification-svc"},
    {"name": "ml-inference-8b4a5c2d7", "namespace": "ml-workloads", "node": "node-03", "service": "ml-inference"},
    {"name": "redis-cache-1e6d3f9a2", "namespace": "infrastructure", "node": "node-01", "service": "redis-cache"},
    {"name": "postgres-primary-5f2c8b7d4", "namespace": "infrastructure", "node": "node-02", "service": "postgres"},
    {"name": "monitoring-agent-3a9e1d6c5", "namespace": "kube-system", "node": "node-01", "service": "monitoring"},
    {"name": "log-collector-7c4b2f8a3", "namespace": "kube-system", "node": "node-03", "service": "log-collector"},
]

SIMULATED_NODES = [
    {"name": "node-01", "role": "control-plane", "status": "Ready", "cpu_capacity": 8, "memory_gb": 32},
    {"name": "node-02", "role": "worker", "status": "Ready", "cpu_capacity": 16, "memory_gb": 64},
    {"name": "node-03", "role": "worker", "status": "Ready", "cpu_capacity": 16, "memory_gb": 64},
]


def get_cluster_topology() -> dict:
    """Return simulated cluster topology for the dashboard."""
    nodes = []
    for n in SIMULATED_NODES:
        node_pods = [p for p in SIMULATED_PODS if p["node"] == n["name"]]
        nodes.append({
            **n,
            "pod_count": len(node_pods),
            "cpu_usage": round(random.uniform(20, 70), 1),
            "memory_usage": round(random.uniform(30, 75), 1),
        })

    pods = []
    for p in SIMULATED_PODS:
        pods.append({
            "name": p["name"],
            "namespace": p["namespace"],
            "status": random.choice(["Running"] * 9 + ["CrashLoopBackOff"]),
            "node": p["node"],
            "service": p["service"],
            "cpu_usage": round(random.uniform(5, 65), 1),
            "memory_usage": round(random.uniform(10, 70), 1),
            "restart_count": random.randint(0, 3),
            "containers": [{"name": p["service"], "ready": True, "image": f"sentinelflow/{p['service']}:latest"}],
            "labels": {"app": p["service"], "tier": p["namespace"]},
        })

    services = [
        {"name": "api-gateway", "type": "ClusterIP", "port": 8080, "endpoints": 3},
        {"name": "auth-service", "type": "ClusterIP", "port": 8081, "endpoints": 2},
        {"name": "payment-gateway", "type": "LoadBalancer", "port": 443, "endpoints": 2},
        {"name": "data-processor", "type": "ClusterIP", "port": 8082, "endpoints": 1},
        {"name": "notification-svc", "type": "ClusterIP", "port": 8083, "endpoints": 1},
    ]

    return {"nodes": nodes, "pods": pods, "services": services}


def generate_normal_metrics() -> dict:
    """Generate normal (non-anomalous) telemetry data."""
    pod = random.choice(SIMULATED_PODS)
    return {
        "node_name": pod["node"],
        "pod_name": pod["name"],
        "namespace": pod["namespace"],
        "cpu_usage": round(random.gauss(35, 12), 1),
        "memory_usage": round(random.gauss(45, 10), 1),
        "disk_usage": round(random.uniform(20, 60), 1),
        "network_rx_bytes": round(random.uniform(1000, 50000), 0),
        "network_tx_bytes": round(random.uniform(500, 30000), 0),
        "requests_per_sec": round(random.uniform(10, 200), 1),
        "latency_ms": round(random.gauss(50, 20), 1),
        "error_rate": round(random.uniform(0, 2), 2),
    }


def generate_anomaly_metrics(anomaly_type: str) -> dict:
    """Generate telemetry data that will trigger a specific anomaly."""
    base = generate_normal_metrics()

    if anomaly_type == "CPU_SPIKE":
        base["cpu_usage"] = round(random.uniform(91, 99), 1)
    elif anomaly_type == "MEMORY_EXHAUSTION":
        base["memory_usage"] = round(random.uniform(91, 98), 1)
    elif anomaly_type == "DISK_FULL":
        base["disk_usage"] = round(random.uniform(91, 99), 1)
    elif anomaly_type == "HIGH_LATENCY":
        base["latency_ms"] = round(random.uniform(5500, 15000), 1)
    elif anomaly_type == "ERROR_RATE_SPIKE":
        base["error_rate"] = round(random.uniform(12, 30), 2)

    return base


def _simulator_loop():
    """Background thread that periodically generates telemetry and anomalies."""
    anomaly_cycle = 0

    while True:
        try:
            metrics = generate_normal_metrics()

            # Publish to stream for consumers
            stream_bus.publish("telemetry:simulated", {
                "type": "NORMAL",
                **{k: str(v) for k, v in metrics.items()},
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

            # Every ~30 cycles, inject an anomaly
            anomaly_cycle += 1
            if anomaly_cycle >= 30:
                anomaly_cycle = 0
                anomaly_type = random.choice([
                    "CPU_SPIKE", "MEMORY_EXHAUSTION", "UNAUTHORIZED_ACCESS",
                    "HIGH_LATENCY", "ERROR_RATE_SPIKE",
                ])
                anomaly_metrics = generate_anomaly_metrics(anomaly_type)

                stream_bus.publish("telemetry:anomaly", {
                    "type": anomaly_type,
                    **{k: str(v) for k, v in anomaly_metrics.items()},
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

                logger.info("simulator_anomaly_injected", anomaly_type=anomaly_type)

                # Trigger workflow in a separate session
                try:
                    db = SessionLocal()
                    from .workflow_service import run_incident_workflow
                    run_incident_workflow(
                        db=db,
                        anomaly_type=anomaly_type,
                        description=f"Simulated {anomaly_type} event: {anomaly_metrics}",
                        severity="CRITICAL" if anomaly_type in ("CPU_SPIKE", "UNAUTHORIZED_ACCESS") else "WARNING",
                        node_name=anomaly_metrics.get("node_name", "node-01"),
                        pod_name=anomaly_metrics.get("pod_name"),
                    )
                    db.close()
                except Exception as e:
                    logger.warning("simulator_workflow_error", error=str(e))

        except Exception as e:
            logger.error("simulator_error", error=str(e))

        time.sleep(5)  # Generate metrics every 5 seconds


def start_simulator_thread():
    """Start the background simulator daemon thread."""
    thread = threading.Thread(target=_simulator_loop, daemon=True, name="sentinelflow-simulator")
    thread.start()
    logger.info("simulator_started")
