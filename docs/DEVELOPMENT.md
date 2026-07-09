# SentinelFlow AI — Development Guide

This guide describes how to set up the development environment, extend features, and run testing suites.

---

## 1. Setup Local Development Workspace

Ensure Python 3.11+ and Node.js 20+ are installed.

### Backend Setup
1. Create virtual env and install requirements:
   ```bash
   cd backend
   python -m venv venv
   # Windows:
   venv\Scripts\activate
   # Unix:
   source venv/bin/activate
   
   pip install -r requirements.txt
   ```
2. Initialize and seed local database configurations:
   ```bash
   python ../scripts/python/setup_databases.py
   ```
3. Run FastAPI backend server:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

### Next.js Frontend Setup
1. Install node dependencies:
   ```bash
   cd frontend
   npm install
   ```
2. Start Next.js development server:
   ```bash
   npm run dev
   ```
   Open dashboard at `http://localhost:3000`.

---

## 2. Test Execution Guidelines

Testing is integrated across unit, integration, performance, and E2E suites.

### Running Backend Pytests
Always execute tests inside the `backend/` directory with active virtual environments:
```bash
# Run all tests
pytest

# Verbose execution with stdout logging
pytest -vv -s
```

### Running Frontend Jest Tests
Execute React component verification tests:
```bash
cd frontend
npm run test
```

---

## 3. Extending the Safety Envelope Policies

To modify command validation patterns or append restricted commands:
1. Open [policies.yaml](file:///e:/SENTINELFLOW%20AI/backend/app/core/policies.yaml).
2. Append a new regex match entry to the threat signatures list:
   ```yaml
   - pattern: "(^|\\s)rm\\s+-rf\\s+.*"
     message: "Immediate block: File deletion traversal threat detected."
     severity: "high"
   ```
3. The policies engine automatically hot-reloads the configuration without restarting the FastAPI process.
