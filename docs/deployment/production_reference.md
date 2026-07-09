# SentinelFlow AI — Production Deployment Reference Architecture

This document provides architectural references for taking SentinelFlow AI from a hackathon demo setup to a secure, highly-available, production-grade enterprise cybersecurity infrastructure. 

> [!NOTE]
> These architectures represent documentation guidelines and recommendations only; they are not active in the local development/demo setup.

---

## 1. Relational Database Scaling (PostgreSQL)

For production loads, replace the SQLite developer instance with a high-availability PostgreSQL cluster:

```mermaid
graph LR
    App1[API Instance 1] --> Primary[Primary PostgreSQL (Read/Write)]
    App2[API Instance 2] --> Primary
    App1 -.-> Replica1[PostgreSQL Read Replica 1]
    App2 -.-> Replica2[PostgreSQL Read Replica 2]
    Primary --> |Asynchronous Replication| Replica1
    Primary --> |Asynchronous Replication| Replica2
```

### Specifications
- **Connection Pooling**: Deploy `PgBouncer` sidecars next to FastAPI instances to minimize database connection overhead.
- **Failover**: Use `Patroni` with Consul or Etcd for automated leader election and failover.
- **Backups**: Configure automated point-in-time recovery (PITR) to secure locations (e.g., AWS S3 via WAL-G).

---

## 2. Distributed Vector Database (Qdrant)

Instead of the embedded local storage client, deploy a distributed, replicated Qdrant cluster:

- **Cluster Setup**: Qdrant deployed as a StatefulSet on Kubernetes with a minimum of 3 nodes.
- **Replication Factor**: Set replication factor to `2` or `3` to allow node failure without data loss.
- **Index Optimization**:
  - Configure HNSW indexes with `m=16` and `ef_construct=100` for speed/memory balance.
  - Implement dynamic quantization (scalar quantization `int8`) to reduce vector memory footprint by up to 4x.

---

## 3. High-Throughput Streaming (Redis Cluster)

Production telemetry ingestion rates require a clustered Redis configuration:

- **Topology**: 3 Master nodes and 3 Replica nodes (one replica per master) distributed across availability zones.
- **Partitioning**: Ingest metrics into shards using hash tags (e.g., `{node-01}:telemetry_stream`) to preserve ordering on individual streams while scaling write throughput.
- **Persistence**: Enable AOF (Append Only File) with `everysec` policy combined with daily RDB snapshots to guarantee durability.

---

## 4. Kubernetes Integration & Auto-Scaling

Deploy SentinelFlow AI itself as a Kubernetes deployment:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sentinelflow-backend
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: backend
        image: sentinelflow-backend:latest
        resources:
          limits:
            cpu: "2"
            memory: 2Gi
          requests:
            cpu: "500m"
            memory: 512Mi
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: sentinelflow-backend-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: sentinelflow-backend
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 75
```

---

## 5. Global Observability & Tracing

Ensure global visibility by shipping system telemetry to dedicated telemetry servers:

- **Distributed Tracing**: Configure the OpenTelemetry SDK to export trace spans to a shared collector daemon, pushing to a central Jaeger or Tempo backend.
- **System Metrics**: Expose Prometheus endpoints `/metrics` from all backend nodes, scraped every 15 seconds, and visualised via Grafana dashboards tracking:
  - API request rates, latency (P95/P99), and error percentages (RED method).
  - LLM token expenditure, safety guard evaluation speed, and queue depths.
  - Verification failures on the SHA-256 audit block ledger.

---

## 6. Advanced ML Anomaly Detection

Upgrade the heuristic detection pipeline to a fully containerised ML inference engine:

- **Model Training**: Train an unsupervised autoencoder or isolation forest offline on historical telemetry profiles.
- **Inference Pipeline**: Serve the model via Triton Inference Server or FastAPI model server sidecars.
- **Feature Store**: Use Feast or Redis to retrieve historical rolling window statistics in real time during telemetry evaluation.
