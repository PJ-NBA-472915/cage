# Containerised Distributed Task System Specification

**Status:** Draft  
**Version:** v0.1 (2025-08-21)  
**Authors/Owners:** Jaak  
**Audience:** Engineering (backend, devops), Product, Operators  
**Decision Forum:** Engineering lead + product owner

## 1. Abstract

A containerised, distributed task system with a central Coordinator and multiple Agent workers. The system uses Redis for task queueing, Postgres for persistent state, and adds observability (Prometheus, Loki, Grafana) for monitoring. This enables reliable parallel execution, improved fault tolerance, and easier scaling compared to current ad-hoc scripts.

## 2. Motivation & Goals

### Why now
- Current workflow is manual and brittle; scaling requires human orchestration.

### Goals (MUST)
- Handle ≥ 1k tasks/minute reliably.
- Provide end-to-end visibility via metrics/logs.
- Ensure no task loss on Coordinator/Agent restarts.

### Non-Goals (WON'T)
- Cross-region deployment in v1.
- Advanced scheduling (priority queues, fairness).

## 3. Stakeholders & Users

- **Operators (internal devs):** Run the system locally & on Fly.io.
- **Agents (containers):** Pull and execute tasks.
- **External API clients:** Submit tasks via Coordinator API.

### Use cases
- Operator runs `docker compose up` → full local stack comes up.
- API client submits job → Coordinator enqueues → Agent executes → result logged in Postgres.

## 4. Proposal (High Level)

Introduce a Coordinator service exposing REST/gRPC endpoints, backed by Redis Streams for task queueing and Postgres for persistence. Agents poll Redis, execute tasks, and report results. Observability stack (Prometheus, Loki, Grafana) provides visibility.

**Success criteria:** A new engineer can spin up the system locally and process 1000 tasks reliably with metrics visible in Grafana.

## 5. Requirements

### Functional (MUST)
- Coordinator MUST expose `POST /v1/tasks` to accept jobs.
- Agent MUST acknowledge tasks within 1s.
- Coordinator MUST persist task lifecycle in Postgres.
- API MUST return task status when queried.

### Non-Functional
- **Performance:** P95 enqueue latency < 200 ms.
- **Reliability:** No task loss; retries on agent crash.
- **Security:** Auth token required for task submission.
- **Observability:** Metrics on QPS, latency, queue depth. Logs with correlation IDs.
- **Maintainability:** Configurable via env vars; feature flag for "observability_enabled."

## 6. Design & Architecture

### Context
- **Coordinator:** REST API, connects to Redis + Postgres.
- **Agent:** Worker that pulls from Redis.
- **Observability:** Prometheus scrapes metrics, Loki ingests logs, Grafana visualises.

### Sequence (happy path)
1. Client → Coordinator (`POST /v1/tasks`).
2. Coordinator validates + writes to Postgres.
3. Coordinator enqueues job into Redis.
4. Agent pulls job, executes, pushes result → Postgres.
5. Metrics/logs emitted → Prometheus/Loki.

### Data model

#### `tasks` table
```sql
id BIGSERIAL PK,
status VARCHAR,
payload JSONB,
created_at TIMESTAMP,
updated_at TIMESTAMP
```

### API contract

```
POST /v1/tasks
Authorization: Bearer <token>
Body: { "type": "resize_image", "params": { ... } }
→ 201 Created { "id": 123, "status": "queued" }
```

## 7. Examples (Before/After)

**Before:** Dev manually runs a script on laptop; no logging; failure requires rerun.

**After:** Dev submits job via API; can query `/v1/tasks/{id}` for status; Grafana shows metrics.

## 8. Trade-offs & Alternatives Considered

- **Redis vs RabbitMQ:** Redis chosen for simplicity, native Streams support. RabbitMQ could offer richer semantics but adds ops overhead.
- **Coordinator as monolith vs microservices:** Monolith for v1 (fewer moving parts). Future split possible.
- **Postgres vs DynamoDB:** Postgres chosen for local-first dev and Supabase cloud path.

## 9. Risks, Threats & Failure Modes

- **Redis crash:** Risk of task loss → mitigated with persistence enabled (AOF).
- **Agent overload:** Tasks pile up → mitigated with queue depth metrics + autoscaling.
- **Log flood:** High QPS may overwhelm Loki → mitigate with sampling.

## 10. Testing & Validation Plan

- **Unit tests:** API validation, DB writes.
- **Integration tests:** Coordinator ↔ Redis ↔ Agent flow.
- **Load test:** 1k tasks/min with 10 agents.
- **Chaos test:** Kill agent mid-task → ensure retry succeeds.

## 11. Rollout Plan

- Local dev with `docker compose up`.
- Deploy to Fly.io with Redis + Postgres managed services.
- Staged rollout: 1 agent → 3 agents → 10 agents.
- **Rollback:** redeploy Coordinator from previous image, flush Redis stream.

## 12. Cost & Feasibility

- **Complexity:** Medium. Existing libraries reduce effort.
- **Infra cost (est):** $50–100/mo Fly.io (Coordinator, Redis, Grafana) + Supabase Postgres.
- **Effort:** ~3 engineer-weeks for MVP.

### Timeline
- **Week 1:** API + Postgres schema
- **Week 2:** Redis + Agent workers
- **Week 3:** Observability + rollout

## 13. Open Questions

- Should tasks be FIFO or allow priority queues?
- Do we need gRPC in v1 or REST only?
- Should Grafana dashboards be versioned in repo?

## 14. Decision Record

- **Outcome:** Pending review.
- **Rationale:** TBD.
- **Follow-ups:** Create GitHub issues for MVP milestones.

## 15. References

1. [RFC 2119](https://tools.ietf.org/html/rfc2119) – Key words for requirement levels.
2. [Redis Streams documentation](https://redis.io/docs/data-types/streams/).
3. [Supabase Postgres service docs](https://supabase.com/docs/guides/database).
4. [Fly.io Redis service](https://fly.io/docs/redis/).
5. [Fly.io example of isolated environments](https://fly.io/docs/blueprints/per-user-dev-environments/)
