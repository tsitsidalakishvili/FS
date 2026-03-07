# Migration PRD: CRM + Deliberation + Due Diligence

## 1) Document control
- **Owner:** Product Owner
- **Date:** 2026-03-07
- **Status:** Draft for architecture kickoff
- **Target branch:** `cursor/migration-product-definition-5877`

## 2) Problem statement
The product currently works, but critical capabilities are split across a large Streamlit shell (`app.py`), a separate Deliberation FastAPI service, and a Due Diligence (DD) subsystem. Migration is needed to reduce delivery risk, stabilize contracts, and enable incremental releases without breaking current campaign operations.

## 3) Migration objective
Deliver a **contract-first, modular, and releasable migration** that:
1. Preserves current user workflows (CRM + Deliberation + DD).
2. Improves configuration/security baseline for production use.
3. Aligns graph data contracts across modules.
4. Enables safe cutover with measurable rollback readiness.

## 4) Scope (incremental and releasable)
### Release Slice R1 (P0): Foundations and no-regression baseline
- Feature F1: Configuration and secrets baseline
- Feature F2: Deliberation API contract freeze + compatibility

### Release Slice R2 (P0): Data migration reliability
- Feature F3: Migration-safe import and replay metrics
- Feature F4: Cross-module graph schema alignment

### Release Slice R3 (P1): UI shell migration
- Feature F5: Streamlit app shell decomposition and navigation compatibility

### Release Slice R4 (P1): DD Phase 2 minimum workflow
- Feature F6: Case workflow MVP on top of existing DD Phase 1

### Release Slice R5 (P0): Cutover and rollback readiness
- Feature F7: Runbook, pilot, and go/no-go gates

## 5) Resolved ambiguities (must be settled before architecture)
| Ambiguity | Decision (resolved) | Why |
|---|---|---|
| What is the migration unit? | Feature-level slices (R1-R5), each releasable independently. | Reduces blast radius and supports weekly release cadence. |
| What is the source of truth for user-facing behavior? | Current production behavior in existing CRM/Deliberation/DD flows is baseline. | Migration is not a redesign; regression risk is primary. |
| Which identity standard is used in deliberation votes/comments? | Keep participant hashing model; require non-default salt in non-dev environments. | Preserves anonymity model while hardening security. |
| Tenant isolation model during migration? | Keep existing nation/tenant model unchanged in this phase. | Avoids cross-tenant regressions during core migration. |
| How much downtime is acceptable at cutover? | Planned maintenance window up to 15 minutes; rollback path mandatory. | Balances operational reality and continuity requirements. |
| Are we introducing RBAC/auth redesign now? | No; only minimal hardening needed for migration safety. | Keeps scope controlled and shippable. |

## 6) PRD requirements
1. Migration must ship in slices that can be deployed independently.
2. Every feature must include testable acceptance criteria.
3. Data integrity checks are required before and after each migration step.
4. Rollback procedure must be validated before final cutover.
5. No user-visible degradation in core workflows: People, Tasks, Outreach, Deliberation participation, DD launch path.

## 7) Prioritized backlog
| ID | Feature | Priority | Release | Business value | Effort (S/M/L) | Dependency |
|---|---|---|---|---|---|---|
| F1 | Configuration and secrets baseline | P0 | R1 | Prevents production incidents and secret leakage | S | None |
| F2 | Deliberation API contract freeze + compatibility | P0 | R1 | Stabilizes frontend/backend integration | M | F1 |
| F3 | Migration-safe import/replay metrics | P0 | R2 | Enables trustworthy data backfills and audits | M | F2 |
| F4 | Cross-module graph schema alignment | P0 | R2 | Prevents duplication/inconsistent IDs and broken queries | L | F3 |
| F5 | App shell decomposition + nav compatibility | P1 | R3 | Reduces monolith risk while preserving UX | M | F2, F4 |
| F6 | DD Phase 2 case workflow MVP | P1 | R4 | Unlocks end-to-end investigator workflow | M | F4, F5 |
| F7 | Cutover + rollback runbook and pilot | P0 | R5 | Operational readiness for production migration | M | F1-F6 |

## 8) Acceptance criteria by feature (testable)

### F1 - Configuration and secrets baseline (R1, P0)
1. **Secret hygiene check**
   - Given the repository default branch,
   - When secret scanning runs on the codebase,
   - Then no plaintext runtime credentials are present in tracked files.
2. **Environment parity**
   - Given `.env.example`,
   - When a new developer follows setup docs,
   - Then CRM UI and Deliberation API both boot successfully using documented keys only.
3. **Config completeness**
   - Given runtime startup checks,
   - When required non-dev variables are missing,
   - Then the app/service fails fast with explicit error messages.

### F2 - Deliberation API contract freeze + compatibility (R1, P0)
1. **Contract coverage**
   - Given the documented endpoint set used by CRM,
   - When contract tests run against API and client adapter,
   - Then all endpoints used by CRM pass (HTTP status, required fields, field types).
2. **Backward compatibility**
   - Given current CRM Deliberation UI flows,
   - When run against migrated API release,
   - Then create/list/comment/vote/report workflows succeed with no UI-breaking schema changes.
3. **Performance guardrail**
   - Given baseline test dataset,
   - When API smoke performance tests execute,
   - Then p95 latency for core read endpoints does not regress more than 15% from baseline.

### F3 - Migration-safe import and replay metrics (R2, P0)
1. **Deterministic import accounting**
   - Given a fixed CSV fixture,
   - When bulk import endpoints run twice,
   - Then counters (`received`, `valid`, `imported`, `skipped`, `unique`) are deterministic and idempotent.
2. **Row-level validation**
   - Given malformed rows,
   - When import executes,
   - Then invalid rows are skipped and reported without aborting valid rows.
3. **Auditability**
   - Given an import job,
   - When job completes,
   - Then an artifact/log exists with totals and timestamp for reconciliation.

### F4 - Cross-module graph schema alignment (R2, P0)
1. **Constraint convergence**
   - Given CRM, Deliberation, and DD schema initialization,
   - When schema checks run,
   - Then required uniqueness constraints/indexes exist and no conflicts remain.
2. **Identity consistency**
   - Given Person/Conversation/Comment/Participant entities,
   - When sample records are created across modules,
   - Then IDs and key properties conform to a single documented contract.
3. **Data quality gate**
   - Given migration dry-run data snapshot,
   - When reconciliation query suite executes,
   - Then duplicate rate for key entities is <= 0.5% and all exceptions are listed.

### F5 - App shell decomposition + navigation compatibility (R3, P1)
1. **No-regression navigation**
   - Given existing and legacy nav keys,
   - When users navigate via sidebar,
   - Then all mapped destinations resolve to correct pages without dead-end states.
2. **Module boundary enforcement**
   - Given decomposed page handlers,
   - When static checks/import checks run,
   - Then new page logic is located in module files, not re-introduced into monolithic shell blocks.
3. **Smoke coverage**
   - Given standard supporter workflow,
   - When smoke tests execute,
   - Then Dashboard, People, Tasks, Outreach, Events, Deliberation, DD paths render successfully.

### F6 - DD Phase 2 case workflow MVP (R4, P1)
1. **Case creation**
   - Given a selected subject (CRM or rival intake),
   - When user starts a DD case,
   - Then a case record is created with subject, type, created timestamp, and status.
2. **Evidence linkage**
   - Given weekly monitoring/enrichment outputs,
   - When attached to a case,
   - Then linked evidence includes source and ingestion timestamp.
3. **Action handoff**
   - Given a completed DD review,
   - When user triggers next steps,
   - Then at least one CRM follow-up action can be created from the DD workflow.

### F7 - Cutover + rollback runbook and pilot (R5, P0)
1. **Runbook completeness**
   - Given migration runbook,
   - When reviewed by engineering + ops,
   - Then it includes pre-checks, cutover steps, validation queries, rollback steps, and owners.
2. **Pilot success gate**
   - Given pilot tenant/group,
   - When migrated release is used for one full cycle,
   - Then no Sev-1 incidents occur and critical workflows pass daily checks.
3. **Rollback drill**
   - Given pre-cutover snapshot and rollback script,
   - When rollback drill executes in staging,
   - Then service is restored to pre-cutover state within 30 minutes.

## 9) Success metrics
- 0 plaintext credentials in tracked repository files.
- 100% pass rate for contract tests covering CRM-used Deliberation endpoints.
- Import reconciliation mismatch <= 0.5% for key entities.
- 0 Sev-1 incidents during pilot slice.
- Core smoke suite pass rate >= 98% across R1-R5 releases.

## 10) Non-goals (explicitly out of scope)
1. Full RBAC redesign and identity-provider migration.
2. UI/UX redesign of CRM pages unrelated to migration risk.
3. Major analytics model overhaul (clustering/consensus algorithm changes).
4. Multi-region or high-availability infrastructure redesign.
5. Replacing Neo4j with a different database technology.
6. Broad feature expansion outside defined migration slices.

## 11) Risks and mitigations
- **Risk:** Hidden schema coupling across modules.  
  **Mitigation:** F4 reconciliation queries + dry-run quality gates before production writes.
- **Risk:** API drift between CRM client and Deliberation service.  
  **Mitigation:** F2 contract tests as release gate.
- **Risk:** Operational cutover failure.  
  **Mitigation:** F7 rollback drill + explicit go/no-go checklist.

## 12) Go/no-go checklist for architecture handoff
- [ ] Ambiguities in Section 5 accepted by Eng + QA.
- [ ] Feature ownership assigned for F1-F7.
- [ ] Test fixtures defined for contract/import/schema checks.
- [ ] Pilot cohort selected and rollback environment validated.

