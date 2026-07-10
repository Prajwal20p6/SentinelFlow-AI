# 🧑‍⚖️ SentinelFlow AI — Hackathon Judge Demo Guide

Welcome to the **SentinelFlow AI** interactive demo walkthrough! This guide outlines how to access the live application, authenticate using the pre-seeded judge demo credentials, trigger simulated infrastructure incidents, and observe autonomous security actions.

---

## 🔗 Live Application Access URLs

* **Frontend Dashboard URL:** `https://sentinelflow-production.up.railway.app`
* **Backend Gateway API URL:** `https://sentinelflow-production.up.railway.app/api/v1`
* **Interactive Swagger UI Docs:** `https://sentinelflow-production.up.railway.app/docs`

---

## 🔑 Judge Demo Credentials

To access the reactive operational dashboard without setup, log in using:

* **Email Address:** `judge@sentinelflow.ai`
* **Access Password:** `judgepass123!`
* **MFA Passcode:** `123456` *(In the login console, you can also click the "INJECT CREDENTIALS" helper button to auto-authenticate)*

---

## 🚀 Step-by-Step Demo Flow

Follow these steps to experience the full incident lifecycle:

### Step 1: Access the Dashboard
1. Open the [Frontend Dashboard](https://sentinelflow-production.up.railway.app) in your web browser.
2. Enter the Judge credentials from the section above and complete the login sequence.
3. Observe the cyberpunk-themed **Cyber Security Operations Dashboard** displaying active clusters, telemetry indicators, and incident queues.

### Step 2: Trigger a Simulated Metric Spike
1. In the bottom-left sidebar, open the **Demo Control Panel** drawer.
2. Click the button labeled: **Trigger CPU_SPIKE (Payment API Pod)**.
3. In the background, this simulates a sudden 95% CPU consumption anomaly on a production Kubernetes container pod.

### Step 3: Observe Mastra AI Orchestration
1. Instantly, a new high-severity incident will be added to the queue via WebSocket updates.
2. Click on the incident card in the **Active Queue** to open the **Investigation Console**.
3. Watch the workflow timeline cycle through the Mastra Agent states:
   * **`RCA Agent`** analyzes pod log traces to pinpoint CPU spike roots.
   * **`Threat Intel Agent`** performs IOC registry checks for compute hijacking patterns.
   * **`Prioritization Agent`** assesses security alerts and maps response SLAs.
   * **`Remediation Agent`** designs safety-gated CLI actions.

### Step 4: Inspect Qdrant Runbook Retrieval
1. Inside the incident detail view, scroll down to the **Suggested Runbooks** section.
2. Observe the mitigation steps found by **Qdrant Vector Database** using semantic similarity mapping against historical security playbook libraries.

### Step 5: Test Enkrypt AI Safety Validation
1. Under **Remediation CLI Console**, you will see the recommended terminal command.
2. Try executing a safe command (e.g. `kubectl scale deployment payment-api --replicas=3`). Observe that the **Enkrypt AI SDK** validates it as safe and allows execution.
3. Try typing a dangerous or destructive action (e.g. `rm -rf /` or `kubectl delete namespace default`). Observe that the **Enkrypt AI prompt/command guardrail** blocks the action and outputs a `403 Forbidden` response details report.

---

## 📐 System Architecture

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

---

## 🛠️ Technology Stack
* **Gateway Core:** Python 3.12, FastAPI, SQLAlchemy, Alembic, Prometheus Client
* **Agent Engine:** Mastra SDK, Node.js, Express, TSX
* **Vector Search:** Qdrant Cloud Cluster database
* **Client Interface:** React 19, Next.js 15, Recharts charts, TailwindCSS
* **Security Layer:** Enkrypt AI SDK

---

## 💡 Troubleshooting
* **WebSockets Offline:** If updates slow down, click the **Reconnect WS** toggle in the top status bar.
* **Database Reset:** If you wish to clear past logs, navigate to the **Demo Control Panel** and select **Reset Database State**.
