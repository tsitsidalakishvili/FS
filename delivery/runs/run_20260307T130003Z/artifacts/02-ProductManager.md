# Stage 2 — ProductManager

## Approved bounded scope (Increment 1)
- People core lifecycle (list/search/create/update/archive)
- Tasks core lifecycle (create/assign/status/filter)
- Events core lifecycle + public registration deep links
- Production baseline controls (auth guard, audit fields, structured logging)

## Out of scope (Increment 1)
- Outreach/segments bulk orchestration
- Deliberation full lifecycle/reporting migration
- Dashboard/map/admin/DD parity migration
- Multi-tenant and advanced RBAC

## Acceptance criteria (extract)
1. People CRUD continuity with audit metadata.
2. Task creation/status transitions persist correctly.
3. Event publish and deep-link resolution preserved.
4. Public registration validation blocks invalid payloads.
5. Internal unauthenticated access denied.
6. Automated tests cover core happy/error paths.

## Milestones
- M1: People + auth/audit/logging
- M2: Tasks
- M3: Events + deep-link registration

## Gate result
- ProductManager Gate: PASS
- Artifact delivered: YES
