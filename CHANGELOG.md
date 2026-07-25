# Changelog

All notable changes to SentinelFlow AI will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.4.0] - 2026-07-25

### Added
- **Phase 4: PostgreSQL Persistence for Playbook Execution Tracking**
  - Added `PlaybookExecution` SQLAlchemy ORM model in `backend/app/models/models.py` (`execution_id` UUID PK, `incident_id` FK with `ondelete="CASCADE"`, indexed).
  - Migrated `PlaybookExecutionService` from in-memory dictionary to PostgreSQL database persistence.
  - Added Alembic migration script `481649a6726e_add_playbook_execution_persistence.py`.
  - Added backend process restart survival unit test `test_playbook_execution_persists_across_service_reinstantiation` verifying historical continuity across server restarts.

### Changed
- **Phase 3: Frontend State Management Refactor with Zustand**
  - Refactored `frontend/src/app/page.tsx` state management by extracting local `useState` hooks into 6 domain-scoped Zustand stores:
    1. `authStore.ts` (Authentication & session state)
    2. `incidentStore.ts` (Incident list, detail, and topology state)
    3. `postmortemStore.ts` (Postmortem report, simulation, and PDF export state)
    4. `playbookStore.ts` (Playbook execution tracking state)
    5. `mastraStore.ts` (Mastra agent execution monitor state)
    6. `liveStore.ts` (WebSocket real-time updates, metrics history, and replay engine state)
  - Verified `next build` static page generation and type checking pass cleanly.

- **Phase 2: Centralized Secrets Management**
  - Implemented `SecretProvider` abstraction (`backend/app/core/secrets.py`) supporting `EnvSecretProvider` (local development) and `AWSSecretProvider` (AWS Secrets Manager with `boto3`, caching, and fallback).
  - Updated all core configuration and services to load credentials via dynamic provider lookups.
  - Built `getSecret()` utility in `mastra-service/src/config/secrets.ts`.

- **Phase 1: Test Coverage Formalization & Dependency Mocking**
  - Formalized pytest CI coverage gate (`--cov-fail-under=68`) in `.github/workflows/test.yml` and `pyproject.toml`.
  - Isolated external dependencies (Qdrant, Enkrypt AI, OpenAI/Anthropic/Gemini LLMs, Mastra, Redis) using mocked fixtures.
  - Achieved 100% test pass rate across 149 unit tests with 72% overall code coverage.

- **Phase 5: Repository & Documentation Hygiene**
  - Consolidated historical completion reports into `docs/history/`.
  - Updated `README.md`, `QUICKSTART.md`, and `LOCAL_DEVELOPMENT_GUIDE.md` with verified code credentials (`judge@sentinelflow.ai` / `JudgeDemo123!`).

---

## [1.0.0] - 2026-07-01

### Added
- Initial production release of SentinelFlow AI.
- Autonomous Incident Response & Post-Mortem Orchestration Platform.
- Multi-agent AI reasoning via Mastra microservice.
- Vector-based semantic runbook retrieval using Qdrant.
- AI command safety guardrails via Enkrypt AI integration.
- Next.js cyber-themed interactive SRE incident response console.
