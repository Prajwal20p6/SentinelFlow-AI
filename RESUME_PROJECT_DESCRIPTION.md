# SentinelFlow AI — Resume Project Description

## Resume Bullet Points

- Designed and built a multi-agent AI incident-response platform (FastAPI + Next.js + Mastra) with an enforced AI-transparency guarantee, verifying that simulated/fallback model output is never presented as real — tracing the flag from backend response through WebSocket delivery to a rendered UI indicator.
- Refactored a 6,000+ line monolithic React component into 6 domain-scoped Zustand stores and a Next.js App Router structure (12 route pages, shared auth-gated layout), reducing the original file to 155 lines while preserving all functionality, verified through repeated build/test/type-check passes with zero regressions.
- Implemented a defense-in-depth security layer — TOTP-based MFA with encrypted secret storage, AES-256 column encryption, and a hash-chained tamper-evident audit ledger with an actual chain-verification function — and drove test coverage on the previously weakest safety-critical modules from 31–48% to 93–100%.

## Detailed Resume Description

SentinelFlow AI is an autonomous SecOps platform that ingests infrastructure telemetry, orchestrates a four-agent AI workflow (root cause analysis, threat intelligence enrichment, prioritization, and remediation planning) to diagnose incidents, and executes or recommends remediation actions gated by a confidence-score threshold and human-in-the-loop approval. The system's vector-search layer implements a 4-tier cascading fallback (Qdrant → ChromaDB → FAISS → in-memory) with circuit-breaker protection to preserve availability under partial infrastructure failure. A central engineering focus was AI output transparency: the platform explicitly flags any simulated or fallback AI response so it can never be mistaken for a genuine model decision, verified through the full data path from backend to UI rather than assumed from code presence alone. The frontend was incrementally refactored from a single large component into a properly decomposed Next.js App Router application with domain-scoped state management, with every refactoring step independently verified against real build, type-check, and test output before proceeding to the next.

## Technologies Used

**Backend:** Python, FastAPI, SQLAlchemy, Alembic, PostgreSQL/SQLite, Redis, Qdrant, ChromaDB, FAISS
**Frontend:** TypeScript, Next.js (App Router), React, Zustand, Tailwind CSS
**AI/Orchestration:** Mastra (Node.js/TypeScript), Anthropic/OpenAI/Google provider routing with an explicit simulation-fallback mode
**Testing:** pytest, pytest-cov, Jest, React Testing Library, Playwright
**Security:** JWT, TOTP (MFA), AES-256 encryption, hash-chained audit logging
**Deployment/CI:** Docker, Railway, GitHub Actions

## Measurable Engineering Achievements (independently verified)

- Reduced the primary frontend entry file from 6,058 lines to 155 lines through incremental state-and-component extraction, verified by direct line-count reproduction against the committed source at each step
- Raised test coverage on three safety-critical backend modules: `idempotency_middleware.py` 33% → 93%, `enkrypt_service.py` 48% → 100%, `observability_service.py` 31% → 100%, independently measured via `pytest --cov`
- Verified, via independent code execution (not report review), that a real PDF document generator produces valid binary output starting with the correct `%PDF-1.4` magic header
- Verified, via a standalone reproduction, that a test-suite network-isolation guard correctly blocks real external network calls while allowing local/loopback traffic through
