# Production Runbook

## Scope

Services covered:

- `crm` (Streamlit UI)
- `deliberation-api` (FastAPI)
- `neo4j`
- `redis`
- `prometheus` + `alertmanager` (optional monitoring profile)

Primary deployment artifact: `docker-compose.yml`.

---

## 1) Deployment procedure

1. Pull latest code and verify CI green (`test`, `build`, `deploy-readiness` jobs).
2. Provide runtime env via secret manager or host-level env export.
3. Deploy core stack:
   ```bash
   docker compose up -d --build
   ```
4. Deploy monitoring stack (optional but recommended):
   ```bash
   docker compose --profile monitoring up -d
   ```
5. Validate health:
   - API liveness: `GET /healthz`
   - API readiness: `GET /readyz`
   - API metrics: `GET /metrics`
   - CRM liveness: `GET /_stcore/health`

---

## 2) Health checks and SLO guardrails

### Health checks

- Container health checks are configured in Dockerfiles and compose services.
- Readiness endpoint `/readyz` returns `503` when required dependencies are unavailable.

### Suggested SLO thresholds

- API availability: `>= 99.9%`
- API p95 latency: `< 1.5s`
- API 5xx ratio: `< 5%` over 10m windows

### Prometheus alerts (shipped)

- `DeliberationApiDown`
- `DeliberationApiHigh5xxRate`
- `DeliberationApiHighP95Latency`

---

## 3) Logging and tracing

- API emits structured request logs (JSON) including:
  - `request_id`
  - `method`
  - `path`
  - `status_code`
  - `duration_ms`
- API returns `X-Request-ID` header for request correlation.
- Sentry captures errors and optional traces:
  - `SENTRY_DSN` or service-specific DSNs
  - set `SENTRY_ENVIRONMENT`, `APP_RELEASE`, trace sample rates

---

## 4) Metrics and observability dashboards

- Scrape API metrics at `/metrics`.
- Track:
  - `deliberation_http_requests_total`
  - `deliberation_http_request_latency_seconds`
- Build dashboards for:
  - request throughput by route/method
  - p95/p99 latency
  - 4xx/5xx rate
  - dependency readiness state (`/readyz` checks)

---

## 5) Incident response flow

1. **Acknowledge alert** (Prometheus/Alertmanager and/or Sentry).
2. **Check blast radius**:
   - Is issue isolated to API, CRM, DB, or Redis?
   - Are errors hard failures (`5xx`) or degradations (`readiness`/latency)?
3. **Inspect first signals**:
   - `docker compose ps`
   - `docker compose logs --tail=200 deliberation-api crm neo4j redis`
   - `curl -sf http://<api-host>:8010/readyz`
4. **Mitigate**:
   - restart unhealthy component
   - scale/allocate resources
   - disable optional features (e.g., Redis cache) if root cause is dependency instability
5. **Recover and verify**:
   - alerts resolved
   - latency/error ratio normal
   - business flows validated

---

## 6) Rollback procedure

Use image-tagged deployments in production (recommended `APP_RELEASE=<git-sha>`).

### Compose rollback (image tag based)

1. Set previous known-good tags in deployment env/config.
2. Redeploy:
   ```bash
   docker compose pull
   docker compose up -d
   ```
3. Verify:
   - `readyz` returns healthy
   - critical smoke tests pass
   - no active high-severity alerts

### Emergency rollback checklist

- [ ] Last known good release tag identified
- [ ] Rollback applied to both `crm` and `deliberation-api`
- [ ] Data migrations verified for backward compatibility
- [ ] On-call notified and incident timeline updated

---

## 7) Security and secrets checks

- Ensure `.env` is never committed.
- Keep DSNs, tokens, passwords in secret manager only.
- Rotate credentials immediately if exposed.
- Run periodic secret scanning in CI/SCM settings.

---

## 8) Post-incident actions

- Publish RCA with timeline, root cause, and prevention actions.
- Add/adjust alert thresholds if noisy or missing.
- Add regression tests and deploy-readiness checks for the failure mode.
