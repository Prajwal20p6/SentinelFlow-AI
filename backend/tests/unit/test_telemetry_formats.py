import pytest
from app.services.telemetry_service import parse_prometheus_metrics, parse_kubernetes_event

def test_parse_prometheus_metrics():
    prom_data = """
    # HELP node_cpu_utilization CPU utilization percentage
    # TYPE node_cpu_utilization gauge
    node_cpu_utilization{node="prom-node-01"} 92.5
    node_memory_utilization{node="prom-node-01"} 81.0
    node_disk_utilization{node="prom-node-01"} 50.0
    http_request_duration_ms{node="prom-node-01"} 450.5
    http_requests_errors{node="prom-node-01"} 12.5
    """
    metrics = parse_prometheus_metrics(prom_data)
    assert metrics["node_name"] == "prom-node-01"
    assert metrics["cpu_usage"] == 92.5
    assert metrics["memory_usage"] == 81.0
    assert metrics["disk_usage"] == 50.0
    assert metrics["latency_ms"] == 450.5
    assert metrics["error_rate"] == 12.5

def test_parse_kubernetes_event_oom():
    k8s_event = {
        "metadata": {"name": "oom-event"},
        "involvedObject": {
            "kind": "Pod",
            "name": "oom-pod-01",
            "namespace": "production",
            "nodeName": "k8s-node-large"
        },
        "reason": "OOMKilled",
        "message": "Container limit reached: OOMKilled"
    }
    metrics = parse_kubernetes_event(k8s_event)
    assert metrics["node_name"] == "k8s-node-large"
    assert metrics["pod_name"] == "oom-pod-01"
    assert metrics["namespace"] == "production"
    assert metrics["memory_usage"] == 99.9  # Simulated memory exhaustion

def test_parse_kubernetes_event_backoff():
    k8s_event = {
        "metadata": {"name": "backoff-event"},
        "involvedObject": {
            "kind": "Pod",
            "name": "backoff-pod",
            "namespace": "default",
            "nodeName": "node-2"
        },
        "reason": "BackOff",
        "message": "Back-off restarting container"
    }
    metrics = parse_kubernetes_event(k8s_event)
    assert metrics["node_name"] == "node-2"
    assert metrics["pod_name"] == "backoff-pod"
    assert metrics["error_rate"] == 100.0  # Simulated error spike
