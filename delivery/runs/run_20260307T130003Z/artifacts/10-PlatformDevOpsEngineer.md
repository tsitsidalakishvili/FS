# Stage 8 — PlatformDevOpsEngineer

## Deployment/Ops Slice for Rewrite (Backend + Frontend)

This artifact defines how the new platform runs across environments, how configuration/secrets are governed, which CI gates are release-blocking, and how operations handles release, rollback, and incidents.

Aligned requirements from prior stages:
- Token-bound public registration is mandatory.
- Public flow cannot mutate canonical `Person` fields.
- Internal APIs are authenticated/authorized with deny-by-default policy.
- Write operations must emit immutable audit context.
- Retention/DSAR controls are policy-bound and verifiable.

---

## 1) Local / Dev / Stage / Prod run model (new backend/frontend)

### Environment topology
| Environment | Purpose | Backend runtime | Frontend runtime | Data dependencies | Deployment model |
|---|---|---|---|---|---|
| Local | Fast inner-loop development | FastAPI app with local config | SPA dev server with API proxy | Local Neo4j + local mocks for IdP/audit sinks | Manual run; no shared uptime guarantee |
| Dev | Shared integration and branch validation | Containerized backend in cluster namespace | Built frontend served via dev ingress/CDN | Shared non-prod Neo4j + non-prod IdP | Automated deploy on merge to `develop` and preview deploys |
| Stage | Pre-prod validation with production-like controls | Same artifact as prod, stage config | Same built artifact class as prod | Production-like isolated data set, staged secrets | Automated deploy on release candidate tag + approval gate |
| Prod | Customer-facing workload | Horizontally scaled backend with autoscaling and pod disruption budgets | Immutable static assets + edge caching | Production Neo4j, production IdP, production audit/telemetry backends | Progressive rollout (canary/blue-green) with SLO gates |

### Runtime model by layer
- **Backend**
  - Stateless API pods; readiness includes DB connectivity + dependency check.
  - Token validation, authZ middleware, and audit append are always enabled in every environment.
  - DB schema migrations run as controlled pre-deploy jobs (forward-only and idempotent).
- **Frontend**
  - Build once per commit SHA; environment-specific config injected at deploy time.
  - Internal routes require OIDC-backed session; public token route remains token-bound server-side.
  - Rollout uses immutable artifact versioning to support instant version switchback.

### Promotion path
1. Local verification -> PR checks.
2. Merge -> Dev deploy + integration checks.
3. Release candidate tag -> Stage deploy + full gate suite.
4. Manual approval + SLO health check -> Prod progressive rollout.

---

## 2) Environment variables, secrets, and policy

### Configuration classes
| Class | Examples | Storage source | Repo policy |
|---|---|---|---|
| Non-secret config | `APP_ENV`, `LOG_LEVEL`, feature flags | Environment config maps | Allowed in repo as defaults/templates |
| Sensitive secrets | DB passwords, OIDC client secret, signing keys | Secret manager + runtime injection | Never committed to repo |
| High-risk crypto material | JWT private keys, key-encryption keys | Dedicated KMS/HSM-backed secret path | Access strictly limited + audited |

### Required env vars/secrets (minimum)
| Key | Component | Type | Notes |
|---|---|---|---|
| `APP_ENV` | Backend/Frontend | Config | `local/dev/stage/prod` |
| `API_BASE_URL` | Frontend | Config | Points to `/api/v1` base |
| `OIDC_ISSUER_URL` | Backend/Frontend | Config | Must match trusted issuer |
| `OIDC_AUDIENCE` | Backend | Config | API audience enforcement |
| `OIDC_CLIENT_ID` | Frontend | Config | Public client id |
| `OIDC_CLIENT_SECRET` | Backend | Secret | Confidential client only |
| `NEO4J_URI` | Backend | Config | Cluster endpoint |
| `NEO4J_USERNAME` | Backend | Secret | Service identity |
| `NEO4J_PASSWORD` | Backend | Secret | Rotated credential |
| `TOKEN_SIGNING_KEY_REF` | Backend | Secret reference | KMS/secret-manager key reference |
| `AUDIT_SINK_URL` | Backend | Config | Immutable audit sink endpoint |
| `AUDIT_SINK_TOKEN` | Backend | Secret | Ingest credential |
| `TRACE_EXPORTER_ENDPOINT` | Backend | Config | OTEL collector destination |
| `FEATURE_PUBLIC_REGISTRATION_API_ENABLED` | Backend | Config | Safety flag for rollback control |
| `FEATURE_INTERNAL_PEOPLE_API_ENABLED` | Backend | Config | Domain cutover control |

### Secret and config policy
1. **No plaintext secrets in git**, CI variables, or logs.
2. **Least privilege** per environment (dev credentials cannot access stage/prod assets).
3. **Rotation cadence**
   - App credentials: every 90 days (or faster on incident).
   - Signing/crypto keys: scheduled rotation with overlapping verification window.
4. **Runtime-only secret exposure**
   - Inject at runtime; never baked into container image/static frontend bundle.
5. **Change control**
   - Secret/config changes require ticket reference, reviewer approval, and audit trail.
6. **Break-glass**
   - Time-bounded emergency access with mandatory post-incident review.

---

## 3) CI pipeline gates mapped to security/QA requirements

### Pipeline stages
1. **Static & quality gates**: lint, type checks, dependency/license policy.
2. **Unit/component tests**: backend + frontend test suites with coverage thresholds.
3. **Security gates**: SAST, secret scanning, dependency vulnerability scan.
4. **Contract/integration gates**: API contract tests + Neo4j integration checks.
5. **E2E and policy gates**: authenticated internal flows + token-bound public flow.
6. **Release gates**: signed artifacts, SBOM/provenance, stage verification, approval.

### Control-to-gate mapping (release-blocking)
| Gate ID | Requirement source | Requirement | CI evidence/check | Block on failure |
|---|---|---|---|---|
| G1 | ProductManager AC #1 / SolutionArchitect NFR | Public registration is token-bound | API/E2E tests reject missing/expired/replayed token; no alternate identifier path | Yes |
| G2 | ProductManager AC #2 / Neo4j remediation | Public flow cannot mutate canonical `Person` | Integration tests + query assertions detect zero public-context `Person` mutations | Yes |
| G3 | ProductManager AC #3 / SolutionArchitect | Internal authN/authZ deny-by-default | Route authorization coverage test (100% route-policy mapping) + forbidden-path tests | Yes |
| G4 | ProductManager AC #5 / SolutionArchitect | Immutable audit context on writes | Contract tests assert required audit fields on all write operations | Yes |
| G5 | SolutionArchitect + Neo4j remediation | Replay-safe token handling | Concurrency test validates single-winner token consumption (`409` deterministic for duplicates) | Yes |
| G6 | Privacy requirements | Retention/DSAR controls exist and remain compatible | Policy artifact presence check + migration compatibility tests | Yes |
| G7 | Platform supply chain baseline | Artifact integrity | Container/image signing verification + SBOM generation + provenance attestation | Yes |
| G8 | QA reliability baseline | No regression in core flows | Stage smoke + E2E suite for people/tasks/events/public registration | Yes |

### Minimum quality/security thresholds
- Unit + integration + contract tests pass 100% (no flaky-test bypass in protected branches).
- Critical/high vulnerabilities: **zero** unresolved for releasable artifacts.
- Secret scanning: **zero** active findings.
- Coverage floor: maintain team threshold, with mandatory tests for new security-sensitive code paths.

---

## 4) Rollback and release strategy

### Release strategy
- **Artifact versioning**: every deploy pinned to immutable commit SHA + release tag.
- **Progressive production rollout**:
  1. Deploy canary slice.
  2. Monitor SLOs, security denials, and error rates.
  3. Ramp to full traffic only if gates remain green.
- **Feature-flagged cutover**:
  - Domain toggles (`people`, `tasks`, `events`, `public_registration`) allow targeted enable/disable without full rollback.
- **Migration strategy**:
  - Forward-only, idempotent DB migrations.
  - Backward-compatible app behavior during rollout window.

### Rollback playbook levels
1. **L1: Application rollback (fast)**
   - Trigger: elevated 5xx, auth failures, policy mis-enforcement.
   - Action: switch deployment to prior stable backend/frontend artifact.
2. **L2: Feature rollback (targeted)**
   - Trigger: single-domain issue (e.g., public registration instability).
   - Action: disable affected feature flag; keep unaffected domains live.
3. **L3: Data-safety rollback posture**
   - Trigger: migration compatibility risk.
   - Action: stop rollout, keep writes constrained, run reconciliation checks; avoid destructive schema rollback.
4. **L4: Incident rollback + containment**
   - Trigger: security/privacy event.
   - Action: emergency disable impacted endpoint/path, rotate credentials/keys, preserve forensic evidence.

### Rollback readiness requirements
- Previous stable release artifacts always deployable.
- One-command/environment rollback path documented and exercised in stage drills.
- Post-rollback verification checklist includes:
  - API health/readiness
  - authN/authZ enforcement
  - token-bound public flow behavior
  - audit pipeline continuity

---

## 5) Observability and runbook checklist

### Observability baseline
- **Logs**: structured, correlation IDs required, PII-redaction by default.
- **Metrics**:
  - request rate, latency, error rate, saturation (golden signals),
  - token validation failures and replay conflicts,
  - authZ denies by route/role,
  - audit write success/lag,
  - DSAR/retention job backlog and SLA risk.
- **Tracing**: end-to-end traces across gateway -> backend -> Neo4j -> async jobs.
- **Dashboards**:
  - service health (backend/frontend),
  - security controls (token/authZ/audit),
  - data lifecycle jobs (retention/DSAR),
  - release health (pre/post deployment).

### Alerting expectations
- P1: sustained availability/security control failure (e.g., audit append failure, auth bypass signal).
- P2: degraded performance or rising token/auth failures.
- P3: non-critical job lag or threshold warnings.

### Runbook checklist (pre-release and on-call)
| Checklist item | Pre-release | Incident response | Owner |
|---|---:|---:|---|
| Stage deploy completed with full gate pass | Yes | N/A | Platform DevOps |
| Token-bound registration negative tests passed | Yes | Re-verify | Backend + QA |
| AuthZ deny-by-default coverage report complete | Yes | Re-verify | Backend + Security |
| Audit field completeness check green | Yes | Mandatory | Platform + Security |
| Dashboard/alerts validated (synthetic check) | Yes | Mandatory | SRE/DevOps |
| Rollback command tested for current release line | Yes | Execute if trigger met | Platform DevOps |
| Communication template + incident channel prepared | Yes | Mandatory | Incident Commander |
| Post-incident review captured with action items | N/A | Mandatory | Engineering Mgmt |

### First-response runbook (condensed)
1. Triage alert severity and affected scope (backend/frontend/domain).
2. Confirm blast radius via dashboards + logs + traces.
3. If security/control degradation is confirmed, disable affected feature path immediately.
4. Execute rollback level (L1/L2/L3/L4) based on impact.
5. Validate recovery checks and document timeline/evidence.
6. Open follow-up tasks for permanent fix and gate hardening.

PlatformDevOpsEngineer Artifact: READY
