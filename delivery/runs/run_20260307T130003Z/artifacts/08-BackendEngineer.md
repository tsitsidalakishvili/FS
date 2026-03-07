# Stage 6 — BackendEngineer

## First Rewrite Implementation Slice (Increment 1, bounded)

### Scope anchor (what this slice includes)
This slice implements a production-ready backend foundation for:
- People (list/create/update core profile)
- Tasks (create/update status/list)
- Events (create/read basics)
- Public registration deep-link foundations (token-bound registration write path)

### Pre-gate alignment (must remain true)
- ✅ Token-bound public registration is mandatory (no client-provided `eventId` accepted for public writes).
- ✅ Public flow cannot mutate canonical `Person` fields.
- ✅ Internal APIs are authenticated and deny-by-default by policy.
- ✅ Write operations emit audit context fields for traceability.
- ✅ Retention/DSAR remains policy-owned and out of this implementation slice (only compatibility fields/hooks included).

---

## 1) API endpoints to implement now (minimal but real)

Base path: `/api/v1`

### Platform
1. `GET /healthz`
   - Purpose: liveness/readiness probe.
   - Auth: none.

### Internal (OIDC JWT required; deny-by-default authZ)
2. `GET /people?q=&limit=&includeArchived=`
   - Role allow: `platform_admin`, `ops_coordinator`, `case_worker`, `read_only_auditor`
3. `POST /people`
   - Role allow: `platform_admin`, `ops_coordinator`, `case_worker`
4. `PATCH /people/{personId}`
   - Role allow: `platform_admin`, `ops_coordinator`, `case_worker` (assignment scoping can be added in next slice)

5. `GET /tasks?status=&ownerId=&limit=`
   - Role allow: `platform_admin`, `ops_coordinator`, `case_worker`, `read_only_auditor`
6. `POST /tasks`
   - Role allow: `platform_admin`, `ops_coordinator`, `case_worker`
7. `PATCH /tasks/{taskId}/status`
   - Role allow: `platform_admin`, `ops_coordinator`, `case_worker`

8. `POST /events`
   - Role allow: `platform_admin`, `ops_coordinator`
9. `GET /events/{eventId}`
   - Role allow: `platform_admin`, `ops_coordinator`, `case_worker`, `read_only_auditor`
10. `POST /events/{eventId}/deeplinks`
   - Role allow: `platform_admin`, `ops_coordinator`
   - Returns opaque link token (store hash only in Neo4j).
11. `GET /events/{eventId}/registrations?limit=`
   - Role allow: `platform_admin`, `ops_coordinator`, `case_worker`, `read_only_auditor`

### Public (token-only write path)
12. `POST /public/registrations`
   - Auth model: validated deep-link token scope `registration:write`.
   - Request body excludes `eventId`; event is derived server-side from token claims/store.
   - Allowed mutable fields: registration-scoped only (`status`, `guestCount`, `accessibilityNeeds`, `consentVersion`, `notes`).

### Explicitly out-of-scope for this slice
- Bulk imports, outreach/segments, deliberation, advanced RBAC tiers, DSAR job executors.

---

## 2) Module/file structure proposal

```text
crm_backend/
  app/
    main.py
    api/
      v1/
        router.py
        endpoints/
          health.py
          people.py
          tasks.py
          events.py
          public_registrations.py
    core/
      config.py
      logging.py
      authn.py
      authz.py
      request_context.py
    schemas/
      people.py
      tasks.py
      events.py
      registrations.py
      common.py
    services/
      token_service.py
      deep_link_service.py
      registration_service.py
      audit_service.py
    repositories/
      neo4j/
        base.py
        people_repo.py
        tasks_repo.py
        events_repo.py
        registrations_repo.py
        audit_repo.py
    cypher/
      people.cypher
      tasks.cypher
      events.cypher
      deep_links.cypher
      registrations_public.cypher
      registrations_internal.cypher
      audit.cypher
tests/
  unit/
  integration/
  contract/
```

Implementation note:
- Keep this backend separate from `deliberation/api` to avoid cross-domain coupling during Increment 1 migration.

---

## 3) Cypher/repository boundary contract

### Repository contract rules
1. Controllers/services never embed raw Cypher; only repositories execute queries.
2. Every write repository method requires `ctx` with:
   - `requestId`, `traceId`, `actorType`, `actorId`, `route`, `method`,
   - `authzDecision`, `authzPolicyId`, `authzPolicyVersion`, `decisionReason`,
   - optional hashed client metadata (`ipHash`, `uaHash`).
3. Public registration repository signature **must not accept `eventId`**.
4. Public registration repository must reject canonical `Person` mutation input.
5. Public registration write transaction must atomically:
   - validate token record eligibility,
   - enforce replay protection (`jti` uniqueness),
   - upsert `Registration`,
   - mark token consumed,
   - append `AuditLog`.

### Required repository method signatures (slice 1)
- `PeopleRepo.list_people(q, limit, include_archived) -> list[PersonRow]`
- `PeopleRepo.create_person(input, ctx) -> PersonRow`
- `PeopleRepo.update_person(person_id, patch, ctx) -> PersonRow`
- `TasksRepo.list_tasks(filters, limit) -> list[TaskRow]`
- `TasksRepo.create_task(input, ctx) -> TaskRow`
- `TasksRepo.update_task_status(task_id, status, ctx) -> TaskRow`
- `EventsRepo.create_event(input, ctx) -> EventRow`
- `EventsRepo.get_event(event_id) -> EventRow | None`
- `DeepLinksRepo.create_event_registration_link(event_id, ttl, max_uses, ctx) -> DeepLinkOut`
- `RegistrationsRepo.list_event_registrations(event_id, limit) -> list[RegistrationRow]`
- `PublicRegistrationsRepo.upsert_from_token(token_hash, registration_input, ctx) -> RegistrationRow`

### Cypher ownership split
- `people.cypher`, `tasks.cypher`, `events.cypher`: internal authenticated CRUD/list.
- `registrations_public.cypher`: isolated public write path, registration-only mutations.
- `deep_links.cypher`: link issue/resolve, token hash storage only.
- `audit.cypher`: append-only audit writes.

---

## 4) Test plan for backend (Increment 1)

## Tooling
- `pytest`, `httpx`/`fastapi.testclient`, `testcontainers` Neo4j (or ephemeral Neo4j CI service).

### A) Unit tests
- Schema validation (required/optional fields, enum checks).
- AuthZ policy evaluation (deny by default; explicit allow list).
- Token service validation behavior (expired/invalid/replayed).
- Public field allowlist guard rejects canonical `Person` fields.

### B) Repository integration tests (Neo4j)
- People create/list/update with audit fields.
- Tasks create/status transition/list with filters.
- Events create/get.
- Deep link issuance persists hash (never raw token).
- Public registration atomic flow:
  - valid token succeeds,
  - replay (`jti`) rejected,
  - token/event mismatch rejected,
  - no canonical `Person` fields changed.

### C) API contract tests
- 2xx happy paths and 4xx validation/auth failures per endpoint.
- Unauthorized/forbidden coverage across all internal endpoints.
- `POST /public/registrations` rejects payload containing `eventId`.

### D) Regression/security checks (gate-level)
- Query checks for:
  - public registrations missing token binding,
  - missing audit context fields,
  - any `Person.writeChannel='PUBLIC'` style anomaly indicator.
- CI must fail on non-zero violations.

### E) Minimal E2E slice test
1. Create event (internal).
2. Issue deep link.
3. Submit public registration with token.
4. Read event registrations internally and confirm visibility.

---

## 5) Risks and fallback plan

## Top risks
1. **Direct DB writes from legacy Streamlit bypass new controls**
   - Mitigation: route new write actions through API first; add runtime warning/telemetry for legacy write paths.
2. **Token replay or race conditions**
   - Mitigation: `TokenUse(jti)` uniqueness + single transaction conflict handling (`409` deterministic).
3. **AuthZ gaps during early endpoint rollout**
   - Mitigation: centralized policy middleware with deny-by-default and route coverage tests.
4. **Model drift between legacy `REGISTERED_FOR` and new `Registration` node model**
   - Mitigation: temporary dual-read fallback + reconciliation query job.

## Fallback / rollback
- Feature-flag API usage per domain (`people_api_enabled`, `tasks_api_enabled`, `events_api_enabled`, `public_registration_api_enabled`).
- If incident occurs:
  1. Disable affected API flag,
  2. Revert callers to existing Streamlit/legacy path for that domain,
  3. Keep data (non-destructive rollback),
  4. Run reconciliation + replay-safe recovery.
- Keep migration scripts idempotent; no destructive schema rollback in slice 1.

---

## Concrete backend tasks (first implementation slice)
- **BE-1**: Bootstrap `crm_backend` FastAPI app, config, request context middleware, structured logging.
- **BE-2**: Implement authN/authZ middleware and deny-by-default policy table for in-scope routes.
- **BE-3**: Implement people endpoints + repository + Cypher + integration tests.
- **BE-4**: Implement task endpoints + repository + Cypher + integration tests.
- **BE-5**: Implement event create/get + deep-link issuance endpoints + token hash storage.
- **BE-6**: Implement `POST /public/registrations` with token-bound atomic transaction and audit append.
- **BE-7**: Add CI test stages (unit, integration, contract) and release-blocking security query checks.

BackendEngineer Artifact: READY
