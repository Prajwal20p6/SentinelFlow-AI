# SentinelFlow AI — Interview Guide

## Project Architecture Explanation (30-second version)

"SentinelFlow AI is three services working together: a FastAPI backend that owns persistence and business logic, a Next.js frontend, and a Node.js Mastra service that runs a four-agent AI workflow. When an incident comes in, the backend hands it to Mastra, which runs Root Cause Analysis, Threat Intelligence, Prioritization, and Remediation agents in sequence. If the confidence score is high enough, it can auto-remediate; otherwise it pauses for a human to approve. The whole flow streams to the frontend in real time over WebSocket into a set of Zustand stores, and every remediation action is logged into a hash-chained, tamper-evident audit trail."

## Architecture Explanation (longer version, if asked to go deeper)

Three independently deployable services, each with its own Dockerfile and health check:
1. **Backend (FastAPI/Python):** owns the database (PostgreSQL/SQLite via SQLAlchemy + Alembic migrations), Redis-backed rate limiting and pub/sub, the vector-search layer (Qdrant with cascading fallback), authentication (JWT + TOTP MFA), and the REST API the frontend consumes.
2. **Frontend (Next.js/TypeScript):** App Router structure with a shared auth-gated layout, 6 domain-scoped Zustand stores, and components organized by feature (auth, incidents, mastra, playbooks, postmortem, dashboard).
3. **Mastra service (Node.js/TypeScript):** runs the four-agent workflow, calling out to LLM providers (with an explicit, flagged simulation fallback when a real call isn't available), and reports results back to the backend.

Data flows: an incident trigger hits the backend → the backend calls the Mastra service → Mastra's workflow runs the four agents in sequence, consulting the vector store for relevant runbooks along the way → results and progress stream back through the backend's WebSocket layer → the frontend's Zustand stores update in real time → the UI re-renders, including a visible badge if any step's output was simulated rather than a real model call.

## Major Technical Decisions

**Why a multi-agent workflow instead of one large prompt?** Specialization: each agent has a narrower, more reliable job (find the cause vs. assess threat vs. decide priority vs. plan remediation), which makes failures easier to isolate and reason about than a single prompt trying to do all four at once.

**Why a 4-tier vector-store fallback instead of a single Qdrant dependency?** Availability. A vector-store outage shouldn't take down runbook retrieval entirely — cascading through ChromaDB, then FAISS, then an in-memory store means degraded results are always better than a hard failure.

**Why Zustand over Redux or Context for frontend state?** Lower boilerplate for a project this size, and state naturally divides into independent domains (auth, incidents, postmortem, playbooks, mastra execution, live metrics) that don't need a single global reducer.

**Why fail fast on missing Redis in production instead of silently falling back to in-memory rate limiting?** A silent fallback in production means rate limits quietly become per-worker instead of shared — which is a security-relevant behavior change that should never happen invisibly. Failing loudly at boot in production (while still allowing the in-memory fallback in local dev) makes the failure mode observable instead of a subtle production bug.

## Biggest Engineering Challenges

1. **Making AI transparency actually enforced, not just documented.** It's easy to write a comment saying "fallback output is clearly labeled" and much harder to prove it's true end-to-end. This required tracing the flag from the workflow's mock-response generators, through the backend's response shape, through the WebSocket event payload, into the frontend's Zustand store, and finally confirming the UI component actually reads and renders it — any one broken link in that chain would have meant the guarantee was false despite looking true in isolated code review.

2. **Refactoring a 6,000+ line component without breaking anything.** The temptation with a file that size is a big-bang rewrite. The actual approach was incremental: extract one domain's state into a store, verify build/type-check/test pass, commit, repeat — and only once state extraction was solid, do the same incrementally for JSX/component extraction, and only after that, migrate to proper App Router sub-routes. Each step had its own verification gate before the next began.

3. **Test isolation for a vector database.** Qdrant's embedded/local mode creates a lock file on disk. Early on, this caused real test hangs when a stale lock from a previous run collided with a new test session. The actual root cause turned out to be a module-level singleton — the Qdrant client was being instantiated at import time, before any test fixture could override its storage path — and the real fix was making that instantiation lazy.

## Bugs Found During the Audit Process — and How They Were Fixed

- **AI simulation output was not flagged.** The Mastra workflow's fallback path (triggered when a live LLM call failed) returned template-generated output with a fabricated confidence score, indistinguishable from a real model decision anywhere in the response. Fixed by adding `is_simulated`/`simulation_reason` to every fallback path and rendering a visible badge in the UI whenever it's true.
- **A "PDF" export wasn't actually a PDF.** An early implementation returned plain text with a `Content-Type: application/pdf` header — it would fail to open in any real PDF viewer. Fixed with a genuine `reportlab`-based binary PDF generator, verified by checking the output starts with the real `%PDF-1.4` magic header.
- **An E2E test could pass even when the feature it tested failed.** The test sent the wrong request key and silently defaulted to a hardcoded incident ID if the real one was missing from the response, meaning a broken backend could still produce a "passing" test. Fixed by correcting the request payload and replacing the silent fallback with an explicit assertion.
- **A stale test assertion no longer matched the real code.** A test asserted a model name contained the substring "fast," but the actual routing service had since been updated to return real provider model names like `gpt-4o-mini`. Fixed by updating the assertion to check against the real, current model-name mapping.
- **Jest and Playwright collided in CI.** Once a Playwright E2E test was added, Jest's default file-matching picked it up and tried to run it as a Jest test, which fails because Playwright's runtime needs its own CLI context. Fixed with a `testPathIgnorePatterns` exclusion in the Jest config.
- **A Qdrant client was instantiated eagerly at module import time.** This meant a test fixture's attempt to redirect vector storage to an isolated temp directory had no effect — the client had already been created against the real path before the fixture ran. Fixed by converting to lazy singleton getters behind proxy objects, verified with a repeated stress test that confirmed the real project directory was never touched during test runs.

## How to Explain the Mastra Workflow

"When an incident triggers, the backend calls into the Mastra service, which runs a defined workflow: first a Root Cause Analysis agent looks at the telemetry and forms a hypothesis, then a Threat Intelligence agent checks whether this looks like a security event, then a Prioritization agent scores urgency, and finally a Remediation agent proposes an action — pulling relevant context from the vector store along the way. Each agent's output feeds into a confidence score; if it's high enough, the system can execute the remediation automatically, and if not, it pauses and waits for a human to approve. Every step of this streams to the frontend in real time so you can watch the reasoning happen, not just see a final result."

## How to Explain the Simulation-Transparency Feature

"During development, I found that if a real LLM call failed — rate limit, timeout, whatever — the system would quietly substitute template-generated output with a made-up confidence score, and there was nothing anywhere telling you that had happened. For a system whose whole point is showing AI decision-making, that's a real integrity problem: a demo or even a production incident could show 'confident AI decision' when it was actually a canned fallback. I fixed it by adding an explicit flag to every fallback path, threading it through the API response and the WebSocket event, and rendering a visible badge in the UI whenever it's active — verified by actually tracing that path end to end, not just adding the flag and assuming it would show up correctly."

## How to Explain the Vector Database Fallback Architecture

"Runbook and context retrieval depends on a vector database — Qdrant — but a single point of failure there would mean an outage takes down the AI's ability to consult past incidents entirely. So there's a cascading fallback: if Qdrant is unavailable, it falls back to ChromaDB, then FAISS, then a simple in-memory store as a last resort, with a circuit breaker tracking failures so it doesn't keep retrying a dead service on every request. The tradeoff is that lower tiers have less capability — the in-memory store obviously doesn't persist or scale — but degraded functionality beats a hard failure for something that's supporting, not blocking, the core workflow."

## How to Explain the Security Architecture

"Authentication is JWT-based with TOTP multi-factor auth, and the MFA secret itself is stored AES-256 encrypted at the database column level, not in plaintext. Every automated remediation action gets written into a hash-chained audit ledger — each entry includes the hash of the previous entry, so if anyone tampered with history, the chain would break and a verification pass would catch it. Rate limiting is enforced through Redis, and in production the system fails fast at boot if Redis isn't reachable rather than silently degrading to a per-worker in-memory limiter, because that kind of silent degradation is exactly the sort of thing that becomes a real vulnerability nobody notices until it's exploited."

## Likely Interview Questions with Strong Answers

**"How do you know your tests are actually testing anything real?"**
"During this project's audit process, I specifically found a test that could pass even when the feature it covered was broken — it sent the wrong field name to an endpoint and silently fell back to a hardcoded ID instead of failing when the real response was malformed. That's exactly the failure mode you're describing, and finding and fixing it is part of why I'm confident in the rest of the suite — I went looking for that specific kind of false-positive risk, not just whether tests were green."

**"What would you do differently with more time?"**
"Two things concretely: migrate the remaining frontend orchestration logic further into the App Router structure rather than keeping any central switchboard file, and get live infrastructure verification — a real Railway deployment, real LLM provider keys under load — since everything to date has been verified against local/simulation mode. Those are the two categories of work still open."

**"How do you handle a failing external dependency?"** Point to the vector-store cascading fallback and the Redis fail-fast decision as two different, deliberately different answers to the same underlying question — sometimes graceful degradation is right (vector search), sometimes failing loudly is right (rate limiting), and the distinction is whether silent degradation would hide a security-relevant change in behavior.

**"Tell me about a time you found a bug that wasn't yours."** See `STAR_STORIES.md` — several of these are drawn directly from bugs found during the verification process on code written by a different contributor/tool.
