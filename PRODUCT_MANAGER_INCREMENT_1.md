# Production Migration Increment 1 Scope (CRM + Neo4j)

## 1) Approved scope for first implementation increment (bounded)

**Goal:** Ship a production-ready thin slice that preserves critical CRM behavior for daily operations while reducing migration risk.

**In scope (Increment 1):**
- **People lifecycle (core):**
  - Directory list/search/filter for people records.
  - Profile detail view.
  - Create and update person profile (no hard delete; soft-archive only).
- **Tasks operations (core):**
  - Create task, assign owner, due date, status.
  - Update status (Open/In Progress/Done) and list tasks by owner/status.
  - Link task to person record.
- **Events + public registration deep links (minimum viable):**
  - Create/manage event basics (title, date/time, location/capacity, published flag).
  - Generate and resolve public registration deep link.
  - Persist registrations in Neo4j and show event registration list in CRM.
- **Baseline production foundations for above flows:**
  - Authenticated internal access for CRM views.
  - Audit fields (`createdAt`, `updatedAt`, `createdBy`, `updatedBy`) on scoped entities.
  - Structured logging + error handling for scoped APIs/pages.

**Boundaries:**
- Single workspace/tenant assumptions remain for Increment 1.
- Data model changes are limited to People, Tasks, Events, Registrations (+ required relationships).
- UI parity is functional, not pixel-perfect parity with Streamlit.

---

## 2) Priorities and out-of-scope list

### Priorities (highest to lowest)
1. **P0:** People directory/profile CRUD parity needed for daily operator continuity.
2. **P0:** Task creation + status workflow tied to people for follow-up operations.
3. **P1:** Event creation + public registration deep links to preserve inbound pipeline.
4. **P1:** Production controls (auth, audit, logs) on all in-scope flows.
5. **P2:** UX polish/performance improvements after parity and correctness.

### Explicit out-of-scope for Increment 1
- Outreach/segments/event **bulk** workflows.
- Deliberation lifecycle and deliberation reporting.
- Dashboard/map/data/admin/DD integrations beyond what is required for in-scope entities.
- Advanced permissions model (RBAC tiers), SSO, and multi-tenant isolation.
- Data migration of historical edge cases beyond agreed seed/backfill set.
- Non-critical notifications/automations (Slack/WhatsApp campaign orchestration).

---

## 3) Acceptance criteria (testable, numbered)

1. **People list/read:** Given authenticated user access, when opening People, then list returns existing people with search by name/phone/email and filter by status in <=2s for 10k records (p95).
2. **People create:** Given valid required fields, when creating a person, then record is persisted in Neo4j with unique ID and audit fields populated.
3. **People update:** Given an existing person, when editing profile fields, then changes persist and `updatedAt/updatedBy` reflect the editor.
4. **People archive:** Given an existing person, when archived, then person is hidden from default active view but retrievable with archived filter.
5. **Task create/link:** Given an existing person, when creating a task linked to that person, then task appears in both task list and person profile timeline/related tasks section.
6. **Task status flow:** Given an open task, when moved through statuses, then transition is saved and visible after refresh; invalid status values are rejected with 4xx.
7. **Task filtering:** Given mixed task states/owners, when filtering by owner and status, then returned set is correct and deterministic.
8. **Event publish + deep link:** Given a published event, when requesting registration URL, then system generates stable deep link that resolves to public registration page.
9. **Public registration submit:** Given valid registrant input via deep link, when submitted, then registration node/relationship is created in Neo4j and shown in CRM event attendee list.
10. **Registration validation:** Given invalid registration payload (missing required fields), when submitted, then user receives validation error and no partial registration is created.
11. **Auth guard:** Given unauthenticated access to internal CRM routes, then access is denied/redirected.
12. **Observability baseline:** For each in-scope API action (create/update/list), structured logs include request ID, actor, entity type, outcome, and error details on failure.
13. **Regression protection:** Automated tests cover happy-path + validation/error-path for People, Tasks, Events/Registration endpoints with all tests passing in CI.

---

## 4) Release slicing recommendation (M1/M2/M3)

- **M1 (2-3 weeks): Foundation + People**
  - Auth guard, audit fields, core Neo4j schema constraints/indexes.
  - People list/profile/create/update/archive.
  - CI tests for People + platform smoke tests.
  - Exit gate: AC #1-4, #11-13 pass.

- **M2 (1-2 weeks): Tasks**
  - Task create/update/status/filter and person-task linkage.
  - Task-focused API/UI tests + regression suite expansion.
  - Exit gate: AC #5-7, #11-13 pass.

- **M3 (1-2 weeks): Events + Public registration links**
  - Event create/publish, deep link generation/resolution, public registration submit/validate.
  - End-to-end tests from public form -> Neo4j -> CRM attendee list.
  - Exit gate: AC #8-10, #11-13 pass.

---

## 5) Risks and mitigations

- **Risk:** Hidden Streamlit behavior dependencies not documented.
  - **Mitigation:** Capture behavior contracts from current app with golden-path demos + fixture-based regression tests before cutover.

- **Risk:** Neo4j query performance degradation at production volumes.
  - **Mitigation:** Add indexes/constraints early, profile critical queries, enforce p95 targets in CI perf checks.

- **Risk:** Public deep links abuse/spam.
  - **Mitigation:** Add tokenized link validation, rate limiting, server-side input validation, and bot/spam heuristics.

- **Risk:** Data integrity issues during dual-run migration period.
  - **Mitigation:** Use idempotent writes, immutable event logs for critical mutations, and reconciliation scripts for People/Tasks/Registrations.

- **Risk:** Scope creep from parallel high-priority flows.
  - **Mitigation:** Strict Increment 1 change-control: any new flow must map to current AC set or defer to M2+ backlog.

ProductManager Gate: PASS
