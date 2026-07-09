# 🛡️ SentinelFlow AI

> **Autonomous SecOps Incident Response & Post-Mortem Orchestration**  
> *Under the Hood: Mastra Agent Workflows, Enkrypt AI Guardrails, and Tamper-Evident Audit Trails for Cloud & Kubernetes Infrastructures.*

[![Hackathon](https://img.shields.io/badge/Hackathon-HiDevs%20%C3%97%20Mastra%202026-blueviolet?style=for-the-badge)](https://github.com/Prajwal20p6/SentinelFlow-AI)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104%2B-009688?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-15-black?style=for-the-badge&logo=nextdotjs)](https://nextjs.org)
[![Mastra](https://img.shields.io/badge/Orchestrator-Mastra-FF5722?style=for-the-badge)](https://mastra.ai)
[![Safety](https://img.shields.io/badge/Guardrails-Enkrypt%20AI-00ff88?style=for-the-badge)](https://enkrypt.ai)

---

## 🚀 Live Demo

### **Deploy in 1-Click**
Click the link below to deploy the entire SentinelFlow AI ecosystem (FastAPI, Next.js, PostgreSQL, Redis, and Qdrant) directly on your Railway project dashboard:

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new/template?template=https://github.com/Prajwal20p6/SentinelFlow-AI)

* **Production URL:** `https://sentinelflow-production.up.railway.app/`
* **Backend API URL:** `https://sentinelflow-production.up.railway.app/api/v1`
* **Health Check URL:** `https://sentinelflow-production.up.railway.app/health`

### 🔑 Demo Credentials
* **Email:** `admin@sentinelflow.ai`
* **Password:** `admin123`
* **MFA Verification Code:** `123456` *(If MFA is enabled, backup codes can be verified offline)*
* *Note: In the demo control panel, click "INJECT CREDENTIALS" to auto-authenticate.*

---

## 💡 What is SentinelFlow AI?

SentinelFlow AI is a production-ready, self-healing **Autonomous Incident Response & Post-Mortem Generation Platform**. 

Built for modern distributed Kubernetes and cloud-native systems, SentinelFlow AI ingests telemetry anomalies, invokes a collaborative team of specialized AI agents to analyze threats, orchestrates containment playbooks, and executes rollouts safely under **Enkrypt AI policy envelopes** and cryptographic **Human-in-the-Loop (HITL) approvals**.

### The Problem We Solve
* 🚨 **Alert Fatigue:** SOC teams are overwhelmed by thousands of raw logs and telemetry metrics.
* 🐢 **High Resolution MTTR:** Manual analysis and correlation across systems takes hours, leaving clusters vulnerable.
* 📉 **Safety Risks in Auto-Remediation:** Executing raw commands in production risks service outages or database destruction.
* 📄 **Manual Audits:** Drafting compliance reports and root-cause analyses wastes precious engineering time.

### Why it is Innovative & Deserves to Win
1. **Mastra Agent workflows:** An 8-state resilient incident response pipeline that checkpoints context in SQL for full resume support on server restarts.
2. **Dual-Vector RAG Memory Cascades:** Fallback lookup pipelines (Qdrant → FAISS → ChromaDB) when network nodes timeout.
3. **Enkrypt AI Safety Envelope:** Pre-flight prompt-injection scanning, automatic PII scrubbing, and regex command blocking.
4. **Tamper-Evident Ledger:** Chronological audit trails verified using blockchain-inspired SHA-256 hash chains.
5. **Autopilot Rollbacks:** Records container baselines prior to remediation; triggers auto-rollbacks if latency spikes or error rates climb.

---

## 🛠️ Technical Architecture

```
                                  +-----------------------+
                                  |   Next.js 15 Client   |
                                  +-----------------------+
                                              |
                                              | (REST / WebSockets)
                                              v
                                  +-----------------------+
                                  |    FastAPI Gateway    |
                                  +-----------------------+
                                    /         |         \
                                   /          |          \
                    +-------------+    +-------------+    +-------------+
                    | SQLite/Post |    | Qdrant/Chro |    | Redis Cache |
                    |  (SQLite/    |    |  ma Vector  |    |  & PubSub   |
                    |  PostgreSQL) |    |  database)  |    |  database)  |
                    +-------------+    +-------------+    +-------------+
```

### Key Components
* **`backend/`**: FastAPI python app running the services layer, Mastra engines, and integrations.
* **`frontend/`**: Responsive Next.js 15 / React 19 cyberpunk dashboard with telemetry sparklines, cluster topology nodes, and interactive consoles.
* **`docs/`**: Production PRDs, API schemas, and troubleshooting runbooks.

---

## ⚡ Quick Start (Local Setup)

### Prerequisites
* Python 3.11+
* Node.js 18+
* Git

### 1. Set Up the Backend
```bash
# Clone the repository
git clone https://github.com/Prajwal20p6/SentinelFlow-AI.git
cd SentinelFlow-AI/backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run migrations and seed data
python run.py --init-db

# Launch server
python run.py
```
*Backend runs on `http://127.0.0.1:8000` with Swagger docs available at `/docs`.*

### 2. Set Up the Frontend
```bash
cd ../frontend

# Install dependencies
npm install

# Run in development mode
npm run dev
```
*Frontend dashboard opens on `http://localhost:3000`.*

---

## 🛡️ Functional Walkthrough for Judges

1. **Simulate a Threat:** Log in and navigate to the **Demo Control Panel** in the bottom sidebar. Click **Trigger CPU_SPIKE** or **PHISHING_ATTACK**.
2. **Observe Mastra State Machine:** Watch the **Autonomous Ingestion Path** transition sequentially from `DETECT_ANOMALY` -> `RAG_RETRIEVAL` -> `SAFETY_CHECK` in real-time.
3. **Verify Safety Gate:** Run a destructive command like `rm -rf /` or `kubectl scale --replicas=0` in the Guarded CLI. Watch the Enkrypt AI envelope block the execution and log it to the audit ledger.
4. **Interactive Playbooks:** Open the **Playbook Tracker** tab. Select an incident, click **Start Execution**, and watch the 8-step recovery playbook execute with real-time logs, metrics, and cancel triggers.
5. **Inspect Live Metrics:** Click **Live Metrics** in the sidebar to review the per-service utilization grid and interactive Recharts graphs.

---

## 📈 System Integration & Diagnostics

To run the automated Python test suite:
```bash
cd backend
venv\Scripts\pytest tests/unit/test_metrics_and_playbooks.py
```

To compile the frontend and verify TypeScript types:
```bash
cd frontend
npm run build
```

---

## 📜 MITRE ATT&CK Mapping Matrix

SentinelFlow AI correlates raw telemetry events to standardized adversary techniques:

| Threat Event | Metric Ingest | MITRE Technique | Mitigation Action |
| --- | --- | --- | --- |
| Account Takeover | `UNAUTHORIZED_ACCESS` | `T1078 (Valid Accounts)` | Revoke Session & Lock API Token |
| Compute Hijack | `CPU_SPIKE` | `T1059 (Command Execution)` | Scale Deployment Replicas |
| Data Exfiltration | `DATA_BREACH` | `T1048 (Alternative Protocol)`| Block Network Ports & Isolate Pod |
| Storage Exhaustion | `DISK_FULL` | `T1485 (Data Destruction)` | Evict Pod & Expand PVC Volume |

---

## 👥 Contributors

* **Prajwal S** — Lead AI SRE & System Architect (https://github.com/Prajwal20p6)
* Mastra AI Agent Developer team (2026)
