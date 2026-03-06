# Backend Service Architecture (API/Service Engineer)

## Scope
- Define backend service boundaries for CRM + Deliberation.
- Propose minimal backend changes.
- Keep architecture simple: **reuse the existing FastAPI deliberation service** and avoid introducing new services unless load/latency forces it.

---

## 1) Service Boundaries

### Current state (from codebase)
- `crm/` (Streamlit app): UI and CRM workflows.
- `deliberation/api` (FastAPI): conversations, comments, votes, analysis/reporting.
- Shared data platform: Neo4j (separate DB config available via `DELIBERATION_*` env vars).

### Recommended target boundaries
1. **CRM UI Service Boundary (Streamlit)**
   - Owns page rendering, user session state, and UI-level validation.
   - Must treat deliberation as a remote API domain (already true via `crm/clients/deliberation.py`).
   - Should not write/read deliberation graph entities directly.

2. **Deliberation API Boundary (FastAPI)**
   - Owns all deliberation domain logic:
     - Conversation lifecycle/settings
     - Comment intake + moderation state transitions
     - Voting ingestion/idempotency
     - Consensus/polarization/clustering/report generation
   - Owns deliberation graph schema and constraints.

3. **Data Boundary (Neo4j)**
   - Keep deliberation data isolated logically:
     - Prefer dedicated Neo4j database for deliberation (`DELIBERATION_NEO4J_DATABASE`).
     - Maintain unique constraints already initialized in `init_constraints()`.
   - CRM data model remains separate from deliberation nodes/relationships.

4. **No new microservice (default)**
   - Keep a single deliberation FastAPI process for now.
   - If analysis workload grows, first step should be async jobs **inside the same service boundary** (same repo/runtime), not a new standalone analytics service.

---

## 2) API Surface

### Existing endpoints to keep
- `POST /conversations`
- `PATCH /conversations/{conversation_id}`
- `GET /conversations`
- `GET /conversations/{conversation_id}`
- `POST /conversations/{conversation_id}/seed-comments:bulk`
- `POST /conversations/{conversation_id}/comments`
- `GET /conversations/{conversation_id}/comments?status=...`
- `PATCH /comments/{comment_id}`
- `POST /vote`
- `POST /conversations/{conversation_id}/analyze`
- `GET /conversations/{conversation_id}/report`

### Minimal endpoint additions (recommended)
1. `GET /healthz`
   - Liveness only (process up).
   - Used by container orchestrator liveness checks.

2. `GET /readyz`
   - Readiness includes lightweight Neo4j check (`RETURN 1`).
   - Prevents traffic to unhealthy instances.

3. `GET /conversations/{conversation_id}/stats` (optional but useful)
   - Returns cheap aggregates already queried in multiple places:
     - `comments_total`, `participants_total`, `approved_comments`, `pending_comments`, `votes_total`.
   - Avoids repeated heavy report calls for dashboard counters.

### Contract hardening (no new endpoints required)
- Add explicit response model for `/vote` and seed bulk route.
- Add pagination params on comments list:
  - `limit`, `offset`, `sort` (default by `createdAt`).
- Maintain compatibility by defaulting new params.

---

## 3) Backend Change Plan (Minimal, High-Impact)

### A. Application structure (inside existing FastAPI service)
- Split `routes.py` into domain routers:
  - `routes/conversations.py`
  - `routes/comments.py`
  - `routes/votes.py`
  - `routes/reports.py`
  - `routes/health.py`
- Add service layer modules (pure logic) and repository/query modules (Neo4j IO).
- Benefit: easier testing and safer future changes without changing deployment topology.

### B. Analysis execution model
- Keep synchronous analysis for now (`POST /.../analyze`).
- Add guardrails:
  - configurable max participants/comments for sync path.
  - timeout and graceful 503 with retry guidance when load spikes.
- If needed later, add in-process background task queue before adding any new service.

### C. Data and integrity improvements
- Preserve immutable vote event metadata (e.g., `votedAt` already set).
- Add/update indexes for frequent filters (`Comment.status`, `Comment.createdAt`).
- Keep participant hashing strategy (`ANON_SALT`) and ensure non-default value in production.

---

## 4) Deployment Notes

1. **Topology**
   - Deploy Streamlit and Deliberation API as separate containers/services.
   - Deliberation API is stateless; Neo4j is stateful dependency.

2. **Runtime config**
   - Required: `DELIBERATION_API_URL` in CRM runtime.
   - Deliberation API DB env should point to dedicated DB where possible:
     - `DELIBERATION_NEO4J_URI`
     - `DELIBERATION_NEO4J_USER`
     - `DELIBERATION_NEO4J_PASSWORD`
     - `DELIBERATION_NEO4J_DATABASE`
   - Set `ANON_SALT` per environment.

3. **Scaling**
   - Scale deliberation API horizontally for read/write endpoints.
   - Keep analysis endpoint protected by timeout/concurrency limits.
   - If analysis becomes dominant, move compute to async worker mode within same codebase first.

4. **Release safety**
   - Backward-compatible API changes only.
   - Add smoke checks:
     - `GET /healthz`
     - create conversation
     - post comment + vote
     - fetch report

---

## 5) Observability Notes

### Metrics (must-have)
- HTTP request count/latency/error rate by route and status.
- Neo4j query latency + error count.
- Analysis runtime histogram and failures.
- Queue depth/time-to-complete (if background analysis is enabled later).

### Logging
- Structured JSON logs with:
  - `timestamp`, `level`, `service`, `route`, `method`, `status_code`, `latency_ms`, `request_id`.
- Include `conversation_id` for domain actions where available.
- Redact participant raw IDs and secrets.

### Tracing
- Add OpenTelemetry instrumentation for:
  - inbound FastAPI requests
  - outbound Neo4j operations
- Propagate `X-Request-Id` (generate if absent).

### Suggested SLOs/alerts (initial)
- API availability: 99.9% monthly for core endpoints.
- p95 latency:
  - read/write endpoints < 400 ms
  - report/analyze endpoint < 5 s (current sync mode).
- Alerts:
  - 5xx rate > 2% over 5 min
  - readiness failures > 3 consecutive checks
  - analysis timeout error spikes.

---

## 6) Recommended Implementation Order
1. Add `/healthz` + `/readyz`.
2. Add request ID middleware + structured logging.
3. Add comments pagination and `/stats` endpoint (optional).
4. Refactor `routes.py` into domain routers/services/repositories without behavior changes.
5. Add observability instrumentation (metrics/tracing) and dashboards.

This sequence keeps risk low while improving operability and preserving the current single-service architecture.
