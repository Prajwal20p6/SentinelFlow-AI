# 💻 SentinelFlow AI — Local Development & Debugging Guide

This guide describes how to run and debug the entire SentinelFlow AI multi-service stack locally on a development machine.

---

## 📐 Local Architecture & Port Maps

When running locally, the stack is distributed as follows:

```
                  +-------------------------+
                  |  Next.js App (Port 3000) |
                  +-------------------------+
                    /                      \
                   / HTTP                   \ WebSockets
                  v                          v
      +-------------------------+      +-------------------------+
      |  FastAPI App (Port 8000) | <--> |  Redis Stream Emulator |
      +-------------------------+      +-------------------------+
        /           |            \
       /            |             \
      v             v              v
+---------+   +------------+   +-----------+
| SQLite  |   | Mastra Node|   | Embedded  |
| File DB |   | (Port 3001)|   | Qdrant DB |
+---------+   +------------+   +-----------+
```

* **Frontend Console:** Next.js Client on `http://localhost:3000`.
* **Backend core API:** FastAPI Gateway on `http://localhost:8000`. (Uses SQLite local database file `backend/sentinelflow.db` automatically).
* **AI Orchestrator:** Mastra service on `http://localhost:3001`. (Fires agent execution runs).
* **Vector database:** Local embedded Qdrant (in-process) stored in `backend/data/qdrant/`.
* **Broker & Streams:** Redis stream listener (defaults to in-memory fallback queues if Redis port 6379 is offline).

---

## ⚡ Prerequisites

Install the following dependencies on your system:
* **Python:** Version 3.12+
* **Node.js:** Version 20+
* **Package Manager:** npm version 10+
* **Git:** Version 2.40+

---

## 🚀 Step-by-Step Local Setup

### Step 1: Clone the Repository
```bash
git clone https://github.com/Prajwal20p6/SentinelFlow-AI.git
cd SentinelFlow-AI
```

### Step 2: Configure & Start Python Backend
1. Navigate to the backend folder:
   ```bash
   cd backend
   ```
2. Create and source a Python virtual environment:
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```
3. Install package dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy the environment template:
   ```bash
   cp .env.example .env
   ```
5. Initialize the database schema and seed default users:
   ```bash
   python run.py --init-db
   ```
6. Start the development server:
   ```bash
   python -m uvicorn app.main:app --reload --port 8000
   ```
   *Backend Swagger docs will be exposed at `http://localhost:8000/docs`.*

---

### Step 3: Configure & Start Mastra AI Service
1. In a new terminal window, navigate to the Mastra directory:
   ```bash
   cd mastra-service
   ```
2. Install npm dependencies:
   ```bash
   npm install
   ```
3. Copy the environment variables template:
   ```bash
   cp .env.example .env
   ```
4. Start the service:
   ```bash
   npm run dev
   ```
   *Mastra Express API will run on `http://localhost:3001`.*

---

### Step 4: Configure & Start Frontend Console
1. In a third terminal window, navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Run in local development mode:
   ```bash
   npm run dev
   ```
   *The Next.js client is now live on `http://localhost:3000`.*

---

## 🔐 Debugging Login & User Management

### Do I need to create a new user to log in?
**No.** The server seeds default users automatically into your local SQLite file database on the first boot. 

### Seeded Demo Accounts
Use these preconfigured user accounts to log in:

| Email Address | Password | Role / Access level |
|---|---|---|
| `admin@sentinelflow.ai` | `admin123` | Administrator (Full access) |
| `engineer@sentinelflow.ai` | `eng123` | SRE Engineer (Can execute actions) |
| `judge@sentinelflow.ai` | `judgepass123!` | Hackathon Judge Console |

### Resetting database state
If you wish to clear all logs, mock incidents, and restore default seeded users, run the database initializer flag again:
```bash
cd backend
venv\Scripts\activate
python run.py --init-db
```

---

## 🛠️ Debugging Mastra Service Issues

If Mastra workflows fail or return timeout errors, check the following points:

### 1. Port Collision
Ensure no other service is binding to port `3001` or `8000`. Mastra configuration expects backend on `8000` and node service on `3001`.

### 2. Dotenv Configuration
We have updated `mastra-service/src/index.ts` to load environment variables using `import "dotenv/config";`. If keys are not loading, check that `mastra-service/.env` contains your correct `MASTRA_OPENAI_API_KEY`.

### 3. Namespace Bridges
Our startup script bridges custom variables (e.g. `MASTRA_OPENAI_API_KEY` -> `OPENAI_API_KEY`) to prevent SDK resolution issues. Make sure your keys are valid.

---

## 🧪 Operational Test Commands

Use these endpoints to manually check and trigger incidents in development mode:

### 1. Backend Health Check
```bash
curl http://localhost:8000/health
```
*Expected response:* `{"status":"ok", ...}`

### 2. Mastra Service Health Check
```bash
curl http://localhost:3001/mastra/health
```
*Expected response:* `{"status":"healthy", "service":"mastra-workflow-service"}`

### 3. Anomaly Telemetry Injection
```bash
curl -X POST http://localhost:8000/api/v1/telemetry/ingest \
  -H "Content-Type: application/json" \
  -d "{\"metric_name\":\"cpu_usage\",\"value\":98.5,\"service\":\"payment-api\"}"
```
*Expected response:* Status `200 OK` showing incident successfully added to queue.
