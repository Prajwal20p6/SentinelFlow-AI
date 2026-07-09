# SentinelFlow AI — System Architecture

This guide describes the modular components and self-healing lifecycle mapping of SentinelFlow AI.

---

## 1. System Topology Overview

The application utilizes a decoupled backend (FastAPI) and frontend (Next.js React dashboard) architecture communicating via REST APIs and WebSockets.

```mermaid
graph TD
    subgraph "External Sources"
        Prometheus[Prometheus Metrics] --> |Post Ingest| TelemetryAPI[Telemetry Ingestion Endpoint]
        K8sEvents[Kubernetes v1.Events] --> |Post Ingest| TelemetryAPI
    end

    subgraph "FastAPI Backend"
        TelemetryAPI --> AnomalyEngine[Anomaly Detection Engine]
        AnomalyEngine --> |Trigger Anomaly| WorkflowEngine[Mastra Workflow Orchestrator]
        
        subgraph "8-State Mastra Workflow"
            WorkflowEngine --> State1[1. Detect Anomaly]
            State1 --> State2[2. RAG Retrieval]
            State2 --> State3[3. LLM Reasoning]
            State3 --> State4[4. Contradiction Check]
            State4 --> State5[5. Security Check]
            State5 --> State6[6. Gating Check]
            State6 --> State7[7. Auto-remediate/HITL]
            State7 --> State8[8. Verify & Close]
        end

        State2 --> |Query Runbooks| Qdrant[Qdrant Local Vector DB]
        State3 --> |Cascading LLM Request| LLM[LLM Failover Layer OpenAI/Anthropic/Simulation]
        State5 --> |Rule Check| SafetyEnvelope[Enkrypt Safety Envelope]
        State7 --> |Execute Command| CloudManager[Cloud Remediation Manager]
        
        CloudManager --> |Execute Action| K8s[Kubernetes Cluster Client]
        CloudManager --> |Send Interactive Message| Slack[Slack Interactive Webhooks]
        
        State1 --> |Save State| PostgreSQL[(PostgreSQL / SQLite Database)]
        State1 --> |Emit Broadcast| WSManager[WebSocket Connection Pool]
    end

    subgraph "Next.js Frontend Client"
        WSManager --> |Real-time Updates| ReactApp[React Cyberpunk Dashboard]
        ReactApp --> |Manual Commands Execution| CloudManager
    end
```

---

## 2. Key Architecture Blocks

1. **API Gateway Middleware**:
   - Rate-limiting checking buckets per client IP.
   - OWASP prompt and query injection filters.
   - Standardized error-handling envelopes.
2. **Mastra-Inspired State Machine**:
   - Durably tracks transaction checkpoints in the database.
   - Evaluates LLM reasoning confidence gates (automatic execution if confidence $\ge$ 80%; human-in-the-loop escalation if below).
3. **Enkrypt AI Safety Envelope**:
   - Validates suggested actions against local regex and block policies.
   - Automatically falls back to manual validation if commands match threat signatures.
4. **Cloud Remediations Router**:
   - Standardizes execution logs in SQL database.
   - Provides inverse command generators for rollback triggers (e.g. scale up has rollback scale down).
5. **WebSocket Session Pool**:
   - Manages horizontal scaling via Redis pub/sub.
   - Buffers offline messages up to 1 hour to prevent client packet loss.
