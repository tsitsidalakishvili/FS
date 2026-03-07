# Stage 3 — SolutionArchitect

## Target architecture (Increment 1)
- Frontend: production web client (separate from Streamlit)
- Backend: FastAPI modular service (`/api/v1`)
- DBMS: Neo4j (system of record)
- Optional supporting services: cache/queue for resilience and idempotency

## Domain/API boundaries
- Domains: People, Tasks, Events, Registration, DeepLink resolver
- Contract-first API design with strict schemas and versioning
- Backend is sole writer to Neo4j

## NFRs
- Security: authenticated internal routes, least-privilege access
- Reliability: health checks, readiness/liveness, rollback path
- Performance: bounded p95 targets and indexed queries
- Observability: structured logs, correlation IDs, metrics

## Migration approach
- Strangler pattern: migrate selected routes first, preserve deep links
- Phased cutover with parity checks and rollback switches

## Gate result
- SolutionArchitect Gate: PASS
- Artifact delivered: YES
