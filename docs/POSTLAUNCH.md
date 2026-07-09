# SentinelFlow AI — Post-Launch Verification & Operations Plan

This plan outlines baseline metrics, post-deployment testing, and operational monitoring targets for SentinelFlow AI.

---

## 1. Post-Deployment Verification Checklist

Verify the following items immediately after cluster rollouts:

1. **API Gateway Connectivity**: Ensure endpoints return valid JWT challenges.
2. **WebSocket connection pool**: Confirm React dashboards hook into `/ws` and register active connection counts.
3. **Database migrations check**: Run `alembic current` to ensure the schema matches the production version.
4. **Vector Database RAG connectivity**: Test semantic search cascades via `GET /api/v1/agent/search-runbooks?query=healthcheck`.

---

## 2. Baseline Performance & SLA Metrics

Maintain performance within the following bounds under production loads:

- **API HTTP Latency (P95)**: $< 200\text{ms}$ on read endpoints, $< 100\text{ms}$ on database queries.
- **WebSocket delivery latency**: $< 50\text{ms}$ from backend emit to client dashboard repaint.
- **PII Scrubbing speed**: $< 5\text{ms}$ for standard description inputs.
- **RTO (Recovery Time Objective)**: $< 1\text{ hour}$ for database recovery.
- **RPO (Recovery Point Objective)**: $< 5\text{ minutes}$ for database restoration point.

---

## 3. Alerts Escalation Matrices

Alert notifications are routed through the configured Slack webhook:

- **CRITICAL Alert**: DB connection drop or safety envelope failure -> Page the On-Call DevOps Team immediately.
- **WARNING Alert**: Latency exceeds $1\text{ second}$ -> File a ticket in the engineering backlog.
- **INFO Alert**: Automated self-healing workflow completion -> Log to local structlogs.
