# Stage 3 — SolutionArchitect Route-Back Remediation

## Security blocker to architecture-control mapping
| Security blocker | Architecture control (remediation) | Owning components |
|---|---|---|
| Public registration token binding not mandatory | Token is a mandatory server-side precondition for every public registration write; no alternate identifiers accepted | API Gateway/WAF, Registration API, Token Validation Service |
| Public path can overwrite canonical `Person` PII | Strict write boundary: public channel can write only `Registration`-scoped attributes; canonical `Person` mutations blocked in public context | Registration API, Domain Policy Layer, Neo4j constraints |
| Internal authN/authZ not concretely specified | OIDC-backed authN + deny-by-default route authZ matrix with policy enforcement point and auditable decisions | IdP, API Gateway, AuthZ Policy Engine, FastAPI middleware |
| Retention/deletion/anonymization policy missing | Dedicated retention + DSAR orchestrator services with schedule, legal-hold checks, anonymization workflows, SLA tracking | Retention Service, DSAR Service, Neo4j Data Access Layer, Audit Service |

## 1) Token-bound public registration flow sequence (mandatory)
### Components
- **Public Web Client**: receives deep link, submits token + registration payload.
- **API Gateway/WAF**: TLS termination, rate limiting, bot/challenge controls, request normalization.
- **Registration API (FastAPI)**: validates request schema, enforces data boundary and auth context.
- **Token Validation Service**: verifies token signature/claims/replay status.
- **Neo4j Repository Layer**: transactional writes to `Registration` graph only.
- **Audit Event Writer**: append-only immutable security/audit records.

### Sequence
1. User opens deep link containing signed token (`jti`, `sub`, `eventId`, `scope=registration:write`, `exp`, `aud`).
2. Client calls `POST /api/v1/public/registrations` with token and registration payload.
3. API Gateway applies IP/device rate limit + abuse checks before upstream forwarding.
4. Registration API rejects request if token missing (`400/401`) before any data lookup.
5. Token Validation Service verifies signature, expiry, audience, scope, issuer, and one-time-use status (`jti` replay check).
6. Registration API resolves `eventId` and subject identity **only from validated token claims**; ignores user-supplied IDs.
7. Registration API applies schema allowlist for public fields; strips/rejects canonical `Person` fields.
8. Neo4j transaction performs:
   - idempotent upsert of `Registration` node/edge for token subject + event,
   - token-consumption mark (`jti` consumed) in same atomic unit (or transactional outbox pattern with idempotency key).
9. Audit Event Writer records immutable event (`actor=public_token_subject`, `action=registration.write`, `outcome`).
10. API returns success/failure with correlation ID; no internal identifiers leaked.

### Failure controls
- Invalid/expired/replayed token -> `401/409`, no write.
- Token/event mismatch -> `403`, no write.
- Concurrency collision on same token -> single winner; losers receive deterministic conflict response.

## 2) Public vs canonical data boundary (enforced contract)
### Boundary rule
Public channel is **untrusted** and may mutate only registration-scoped participation data. Canonical person profile is **trusted internal data** and cannot be changed by public flows.

### Allowed mutation matrix
| Data entity | Field examples | Public write | Internal write |
|---|---|---:|---:|
| `Registration` | RSVP status, attendance intent, guest count, accessibility preferences, consent flags, free-text registration notes | Yes | Yes |
| `Person` (canonical) | legal/preferred name, primary email, phone, address, tags, internal notes | No | Yes |
| `Event` | title, schedule, capacity, venue metadata | No | Yes |
| Linkage metadata | token metadata, invitation linkage state | Limited (consume token only) | Yes |

### Enforcement points
- DTO/schema allowlist in public API handlers.
- Domain policy guard that hard-fails if canonical `Person` fields appear in public context.
- Neo4j write-path segregation (`RegistrationRepository` separate from `PersonRepository`).
- Integration tests asserting public endpoint cannot mutate canonical nodes/properties.

## 3) Internal authN/authZ matrix shape (deny-by-default)
### AuthN model
- **Human users**: OIDC/OAuth2 access tokens from enterprise IdP.
- **Service identities**: mTLS + JWT service principals with scoped audiences.
- **Session requirements**: short-lived tokens, key rotation, clock-skew tolerance, revoked-token handling.

### AuthZ model shape
- Route-level policy table with dimensions: **Principal Type x Role x Resource x Action x Constraint x Effect**.
- Default effect for undefined policy: **Deny**.
- Enforcement chain: API Gateway coarse checks -> FastAPI policy middleware fine-grained checks -> repository-level ownership constraints.

### Minimum role set
- `platform_admin`
- `ops_coordinator`
- `case_worker`
- `read_only_auditor`
- `service_registration_worker` (machine)

### Matrix skeleton (Increment 1)
| Resource/Route group | platform_admin | ops_coordinator | case_worker | read_only_auditor | service_registration_worker |
|---|---|---|---|---|---|
| People (`/people`) | CRUD | CRU (restricted delete) | R/U assigned | R | Deny |
| Events (`/events`) | CRUD | CRU | R | R | Deny |
| Tasks (`/tasks`) | CRUD | CRU | CRU assigned | R | Deny |
| Registrations internal (`/registrations`) | CRUD | CRU | CRU assigned | R | R/W scoped |
| Public registration resolver (`/public/registrations`) | Deny (human) | Deny (human) | Deny (human) | Deny | W via token scope only |
| Deep-link/token admin (`/deeplinks`) | CRUD | CRU | Deny | R metadata only | Deny |

## 4) Retention + DSAR service responsibilities
### Service decomposition
- **Retention Policy Service**
  - owns retention schedules and legal-hold exceptions.
  - computes deletion/anonymization eligibility windows daily.
- **DSAR Orchestrator**
  - receives/validates DSAR requests, tracks workflow state and SLA.
  - dispatches erasure/anonymization jobs to domain repositories.
- **Neo4j Privacy Job Runner**
  - executes deterministic anonymization transforms and hard-delete where legally allowed.
  - emits per-entity completion evidence.
- **Compliance Evidence Store**
  - stores signed DSAR outcome records and retention execution reports.

### Baseline policy values (subject to legal sign-off)
- Registration PII retention: **24 months** after event end.
- Unused/expired deep-link token metadata retention: **30 days**.
- DSAR response SLA: acknowledge within **72 hours**, fulfill within **30 days**.
- Legal hold: supersedes deletion/anonymization until released.
- Immutable audit records: retained **7 years** minimum.

### DSAR execution contract
1. Verify requester identity and scope.
2. Build subject graph across `Person`, `Registration`, token linkage, and derived indexes.
3. Apply legal-hold check.
4. Execute delete/anonymize plan with idempotent job IDs.
5. Persist signed completion artifact with entity counts and timestamps.
6. Notify requester and compliance channel.

## 5) Immutable audit + observability requirements
### Immutable audit requirements
- All security-sensitive writes produce append-only audit events.
- Required fields: `event_id`, `timestamp`, `actor_type`, `actor_id/service_id`, `action`, `resource_type`, `resource_id`, `policy_decision`, `request_id`, `trace_id`, `outcome`, `reason_code`.
- Tamper-evidence: hash-chain or signed batch digests with periodic verification.
- Storage: WORM-capable backend or equivalent immutability controls; no update/delete API.

### Observability requirements
- Structured logs with PII redaction-by-default and explicit safe-field allowlist.
- End-to-end tracing across gateway, auth, API, Neo4j, and async jobs.
- Metrics and alerts:
  - token validation failures/replay attempts,
  - authZ denials by route/role,
  - DSAR SLA breach risk,
  - audit pipeline lag/drop detection.

## Component responsibilities (concrete ownership)
- **Gateway/WAF**: TLS, rate limits, abuse controls, coarse auth checks, correlation ID propagation.
- **Auth Service/IdP integration**: token issuance/validation keys, principal identity mapping.
- **AuthZ Policy Engine**: route policy evaluation, deny-by-default enforcement, decision logging.
- **Registration API**: token-bound flow orchestration, schema allowlists, boundary enforcement.
- **Person API**: canonical profile mutation endpoints (internal-only).
- **Neo4j Layer**: transactional integrity, constraint enforcement, write-path segregation.
- **Retention Service**: schedule execution and legal-hold-aware lifecycle jobs.
- **DSAR Service**: intake, orchestration, evidence generation, SLA monitoring.
- **Audit Service**: immutable append-only event ingest and verification.
- **Observability Stack**: logs/metrics/traces, dashboards, security/compliance alerts.

## NFR updates (release-gating)
### Security & privacy
- 100% of public registration writes must pass token validation and replay checks.
- 0 tolerated public-context mutations of canonical `Person` fields (enforced in tests and runtime guards).
- 100% route coverage in authZ matrix; undefined route access denied.

### Reliability & integrity
- Registration write operations are idempotent and concurrency-safe for token replays.
- Audit event durability: no acknowledged write without corresponding audit append success (or durable outbox).
- Retention/DSAR jobs are resumable and idempotent.

### Performance
- Token validation p95 <= 75 ms.
- Public registration endpoint p95 <= 300 ms under expected peak.
- AuthZ decision latency p95 <= 20 ms.

### Operability/compliance
- Correlation/trace IDs present in >= 99.9% of request paths.
- DSAR SLA compliance >= 99% monthly.
- Daily integrity check for immutable audit chain with alert on verification failure.

SolutionArchitect Remediation: COMPLETE
