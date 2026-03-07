# Stage 2 Rerun — ProductManager Remediation

## Security-driven AC updates (blocking)
1. Public registration must be token-bound; invalid/expired token rejects request.
2. Public flow cannot mutate canonical `Person` profile fields.
3. Internal routes must have explicit deny-by-default authN/authZ matrix.
4. PII retention + DSAR policy must be documented before implementation.
5. All write paths must emit immutable audit records with actor, action, outcome, request IDs.

## Scope clarifications
- In scope: requirements/contracts to close security blockers.
- Out of scope: advanced RBAC tiers, multi-tenant redesign, non-Increment-1 domains.

## Definition of done (updated)
- Pre-implementation requires approved contract docs for token enforcement, data boundaries,
  auth matrix, and retention/DSAR policy.

ProductManager Remediation: COMPLETE
# Stage 2 — ProductManager Route-Back Remediation

## Updated acceptance criteria (blocking security/privacy items)
1. **Token-only public registration enforced:** Public registration create/update endpoints SHALL reject requests that do not include a valid, unexpired, server-resolved deep-link token bound to a specific `eventId` (no fallback identifier paths).
2. **No public overwrite of canonical Person PII:** Public registration flows SHALL write only to `Registration`-scoped fields. Any create/update of canonical `Person` profile fields (e.g., name, phone, email, address, notes) from public context is prohibited.
3. **Internal authN/authZ specification is explicit and deny-by-default:** A route-level authorization matrix SHALL define actor roles, allowed actions, and denied actions for all in-scope internal APIs/UI routes; unspecified access defaults to deny.
4. **Retention + DSAR policy is defined for PII lifecycle:** A documented policy SHALL define retention windows, legal hold behavior, deletion/anonymization rules, DSAR request handling SLA, and system-of-record update obligations for Person and Registration PII.
5. **Auditability of security/privacy controls:** All in-scope write operations SHALL capture actor/system identity, timestamp, action, target entity, and outcome in immutable audit records sufficient for compliance review.

## Scope clarifications
### In scope for this remediation update
- Requirements and contracts for token-bound public registration.
- Data-boundary rules separating public registration data from canonical `Person` profile data.
- Internal authN/authZ route matrix definition for Increment 1 flows (People, Tasks, Events, Registration, DeepLink resolution).
- PII retention/DSAR policy requirements and acceptance evidence expected before implementation starts.

### Explicitly out of scope (this remediation cycle)
- Implementing advanced RBAC tiers, SSO, or multi-tenant isolation mechanics.
- Building anti-abuse controls beyond baseline requirements already tracked separately (e.g., advanced bot defense tooling).
- Full legal program redesign beyond the defined retention/DSAR policy needed for Increment 1.
- Re-scoping non-Increment-1 domains (deliberation/reporting, bulk outreach orchestration, dashboard/admin parity).

## Definition of Done updates (pre-implementation gate)
Pre-implementation gate for ProductManager is **PASS-ready only when all artifacts below exist and are approved**:

1. **Public registration API contract** documents token as mandatory precondition, invalid/expired token behavior, and no alternate write path.
2. **Data mutation boundary spec** states that public requests cannot mutate canonical `Person` PII; includes allowed `Registration` fields and mapping rules.
3. **AuthN/authZ matrix** covers every Increment 1 internal route with role/action permissions and deny-by-default rule.
4. **Retention + DSAR policy doc** includes retention periods, deletion vs anonymization decisions, DSAR workflow, SLAs, and audit evidence requirements.
5. **Security/privacy traceability map** links each blocker to specific acceptance criteria and designated owner for implementation verification.

ProductManager Remediation: COMPLETE
