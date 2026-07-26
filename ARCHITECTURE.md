# SentinelFlow AI — System Architecture & Data Flow

SentinelFlow AI maps real-time telemetry inputs to auto-healing cloud actions using multi-stage AI agent workflows, Enkrypt AI safety guardrail policy envelopes, and tamper-evident audit ledgers.

---

## 1. System Component Architecture

```mermaid
graph TD
    Client["Next.js 16 Web Dashboard<br/>(React 19, Zustand, TailwindCSS)"]
    API["FastAPI Gateway Service<br/>(Python 3.12, Uvicorn)"]
    Mastra["Mastra Agent Microservice<br/>(Node.js 20, TypeScript, Express)"]
    DB[("PostgreSQL / SQLite WAL<br/>(SQLAlchemy, Alembic)")]
    Redis[("Redis Pub/Sub & Cache<br/>(Event Streaming)")]
    VectorDB[("Qdrant Vector DB<br/>(384-dim Embeddings)")]
    Chroma[("ChromaDB Fallback")]
    FAISS[("FAISS Fallback")]
    InMemory[("In-Memory Store Fallback")]
    Enkrypt["Enkrypt AI Guardrails<br/>(LLM Policy Envelope)"]

    Client -->|HTTPS REST API| API
    Client -->|WebSocket Live Stream| API
    API -->|HTTP REST| Mastra
    API -->|SQLAlchemy ORM| DB
    API -->|Pub/Sub & Caching| Redis
    API -->|Circuit Breaker| VectorDB
    VectorDB -.->|Fallback 1| Chroma
    Chroma -.->|Fallback 2| FAISS
    FAISS -.->|Fallback 3| InMemory
    API -->|Command Validation| Enkrypt
```

---

## 2. Flagship Autonomous Incident Response Sequence

```mermaid
sequenceDiagram
    autonumber
    actor Telemetry as Prometheus / K8s Telemetry
    participant Gateway as FastAPI Backend Gateway
    participant Enkrypt as Enkrypt AI Guardrails
    participant Qdrant as Qdrant Vector Store
    participant Mastra as Mastra Agent Service
    actor Operator as Human SRE Operator
    participant Audit as Cryptographic Audit Ledger

    Telemetry->>Gateway: POST /api/v1/telemetry/ingest (Metrics / Anomaly Event)
    Gateway->>Gateway: Fingerprint & Create Incident Record
    Gateway->>Enkrypt: Validate Prompt & Context (Prompt Injection Check)
    Enkrypt-->>Gateway: Validation Result (Allowed / Sanitized)
    Gateway->>Qdrant: Search Similar Runbooks (Vector Similarity Search)
    Qdrant-->>Gateway: Matching Runbooks & SOP Chunks
    Gateway->>Mastra: POST /mastra/workflows/incident-response
    Mastra->>Mastra: Execute RCA, Threat Intel, Prioritization, & Remediation Agents
    Mastra-->>Gateway: Agent Workflow Results & Confidence Score (e.g. 71.24%)
    
    alt Confidence >= 85% (Autopilot Mode)
        Gateway->>Gateway: Auto-Execute Remediation Action
    else Confidence < 85% (Human-in-the-Loop Gate)
        Gateway->>Gateway: Set Status PENDING_APPROVAL
        Gateway->>Operator: WebSocket Notification (Pending Human Action)
        Operator->>Gateway: POST /api/v1/incidents/{id}/approve
        Gateway->>Gateway: Execute Remediation Action & Update Status EXECUTED
    end

    Gateway->>Audit: Record Action & SHA-256 Cryptographic Hash Chain
    Gateway->>Gateway: Generate Postmortem Report & PDF Export Stream
```

---

## 3. Centralized Secrets & Configuration Architecture

Secrets and environment configurations are managed via a centralized provider pattern (`SecretProvider` in `app.core.secrets`):

- **`EnvSecretProvider`**: Resolves configuration keys from local process environment and `.env` files.
- **`AWSSecretProvider`**: Fetch and cache secrets dynamically from AWS Secrets Manager in production deployments.
- **Encrypted Database Columns**: Sensitive credentials (such as MFA TOTP secrets) are stored using `EncryptedText` SQLAlchemy column types with AES-256 encryption at rest.

---

## 4. Known Limitations & Architectural Trade-offs

1. **Single-Node Qdrant File Lock**: When operating in local embedded file mode (`QDRANT_MODE=local`, `./data/qdrant`), Qdrant locks its directory exclusively to a single process. In multi-worker backend setups, run Qdrant in server/container mode (`QDRANT_MODE=server`).
2. **Mastra Simulation Fallback Flagging**: If upstream LLMs or API keys time out, Mastra workflow steps return fallback responses explicitly flagged with `is_simulated: true` and visible UI warning badges to ensure zero silent mock masquerading.
3. **Database Persistence Fallback**: Defaults to SQLite with WAL mode (`sentinelflow.db`) when external PostgreSQL is unavailable.
4. **Autopilot Governance Gate**: Autopilot remediation enforces an 85% confidence score threshold; actions below 85% transition to `PENDING_APPROVAL` requiring human SRE operator review in the UI.
