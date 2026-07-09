# SentinelFlow AI — System Architecture & Data Flow

SentinelFlow AI maps real-time telemetry inputs to auto-healing cloud actions using multi-stage AI workflows and safety envelopes.

---

## 1. Multi-Tiered Architecture

The system consists of three main operational tiers:

```
+-------------------------------------------------------------+
|                     Next.js React Client                    |
|  - Live topology nodes mapping                              |
|  - Real-time WebSockets connection channels                 |
|  - Interactive command console                              |
+-------------------------------------------------------------+
                              |
                     HTTPS / WebSockets
                              v
+-------------------------------------------------------------+
|                      FastAPI Services                       |
|  - Telemetry Normalizers (JSON/Prometheus/K8s events)       |
|  - Mastra Workflow Orchestration Machine (8 States)         |
|  - Enkrypt AI Guardrails Policy Engine                      |
|  - Dynamic LLM failover layer (OpenAI/Anthropic/Gemini)      |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|                    Infrastructure & Caching                 |
|  - SQLite / PostgreSQL: Session logs, incidents records    |
|  - Redis: Pub/sub events propagation and cache buffers      |
|  - Qdrant: RAG Runbook vector embeddings memory             |
+-------------------------------------------------------------+
```

---

## 2. The 8-State Mastra Self-Healing Lifecycle

When an anomaly triggers, the Mastra workflow transitions through eight states:

1. **State 1: DETECT_ANOMALY**
   Receives telemetry, scrubs PII, checks prompt injection vectors. Creates an incident record.
2. **State 2: RAG_RETRIEVAL**
   Queries Qdrant runbook memories for matching commands. Cascades to FAISS/Chroma fallbacks if Qdrant is offline.
3. **State 3: LLM_REASONING**
   Feeds context to OpenAI, Anthropic, or Gemini to formulate action plans.
4. **State 4: CONTRADICTION_CHECK**
   Compares recommended commands against retrieved runbooks. Scales down confidence if inconsistencies are found.
5. **State 5: VALIDATE**
   Evaluates commands via the **Enkrypt AI Safety Envelope** denylist. Blocks command execution if dangerous threat matches are detected.
6. **State 6: APPROVE_DECISION**
   Applies confidence threshold gates. Auto-approves if confidence $\ge$ 80% (autopilot); routes to PENDING_APPROVAL and alerts Slack webhooks if confidence is below.
7. **State 7: EXECUTE_REMEDIATION**
   Executes commands via K8s, AWS, or GCP clients in dry-run or live mode. Write audit logs.
8. **State 8: VERIFY_EXECUTION**
   Asserts system returns to healthy state. Closes incident ticket.

---

## 3. Cryptographic Ledgers & S3 Archiving

To prevent tampering by malicious actors:
1. Every incident state transition, safety check, and cloud action is written to the `audit_trails` table.
2. Each log entry calculates a SHA-256 block hash incorporating the hash of the previous log entry, forming a cryptographically chained ledger.
3. System verification runs daily, serializing verified log chains and archiving them to AWS S3 backup storage buckets.
