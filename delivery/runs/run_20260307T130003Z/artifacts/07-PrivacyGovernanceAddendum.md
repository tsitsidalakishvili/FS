# Stage 7 — Privacy Governance Addendum (Gap Closure)

This addendum closes the remaining privacy governance gaps identified in Stage 6.

## 1) Lawful-basis-by-processing matrix

| Processing activity | Purpose | PII used (minimum) | Lawful basis | Special conditions / controls |
|---|---|---|---|---|
| Deep-link token issuance and validation | Bind invitation subject to event and prevent unauthorized registration writes | `subjectPersonId`, `eventId`, token metadata (`jti`, `exp`, `aud`, scope) | **Contract** (service requested by organizer/participant) + **Legitimate Interest** (security/abuse prevention) | One-time token replay checks; no alternate identifier path for public writes. |
| Public registration submission | Record RSVP and participation preferences | `status`, `guestCount`, `accessibilityNeeds` (optional), `consentVersion`, registration notes (optional) | **Contract** (registration fulfillment) + **Consent** for optional sensitive-like fields (`accessibilityNeeds`) where required by jurisdiction | Public flow cannot mutate canonical `Person`; optional fields are not required to complete RSVP. |
| Canonical person profile management (internal only) | Maintain operational contact and case coordination data | `fullName`, `email`, `phone`, `address`, `dob` (if required), tags, internal notes | **Legitimate Interest** (service operations) and/or **Legal Obligation** where mandated records apply | Role-restricted internal routes; deny-by-default policy; access review controls. |
| Task/case/event operations (internal) | Coordinate service delivery and event execution | Minimal identity linkage (`personId`), role/assignment metadata | **Legitimate Interest** | Use IDs over raw contact fields wherever possible; no unnecessary profile replication. |
| Audit logging and security telemetry | Detect abuse, prove access decisions, support investigations/compliance | `actorId/serviceId`, request/trace IDs, action/outcome, policy decision, hashed IP/UA | **Legal Obligation** (where applicable) + **Legitimate Interest** (security/accountability) | PII-safe logs, immutable audit trail, 7-year minimum retention. |
| Retention and DSAR workflows | Fulfill erasure/anonymization and retention obligations | Subject graph keys (`personId`, related registration IDs), DSAR job/evidence metadata | **Legal Obligation** | 72h acknowledgement / 30-day fulfillment SLA, legal-hold override, signed completion evidence. |

### Lawful basis control notes
- Purpose limitation applies per row above; reuse outside listed purposes requires privacy/legal approval.
- When consent is the basis (or required locally), withdrawal is honored prospectively and triggers DSAR/processing restriction workflow where applicable.
- Region-specific legal basis overrides must be captured in a jurisdiction annex before launch in that region.

## 2) PII category inventory with minimization rationale (in-scope fields)

| Entity | Field | PII category | Required? | Public write allowed? | Minimization rationale |
|---|---|---|---|---|---|
| `Person` | `personId` | Indirect identifier | Yes | No | Internal stable key; avoids repeated use of direct identifiers in joins. |
| `Person` | `fullName` | Direct identifier | Conditional | No | Needed only for internal operational contact/context; null on DSAR anonymization. |
| `Person` | `email` | Direct identifier | Conditional | No | Needed for direct communications when required; not required for every workflow. |
| `Person` | `phone` | Direct identifier | Conditional | No | Used only when phone contact is necessary; excluded from public writes. |
| `Person` | `address` | Direct identifier | Optional | No | Collected only if service logistics require location-specific handling. |
| `Person` | `dob` | Sensitive/high-risk identifier | Optional | No | Prohibited unless a documented business/legal requirement exists. |
| `Person` | `tags` | Behavioral/profile metadata | Optional | No | Limited to controlled taxonomy; avoid free-text personal profiling. |
| `Person` | `internalNotes` | Potentially sensitive free text | Optional | No | Strictly internal, least-privilege access; discouraged for unnecessary personal detail. |
| `Registration` | `registrationId`/`registrationKey` | Indirect identifier | Yes | System-managed | Required to ensure idempotent, auditable registration operations. |
| `Registration` | `status` | Participation metadata | Yes | Yes | Core RSVP outcome, minimal needed for event planning. |
| `Registration` | `guestCount` | Non-direct personal data | Optional | Yes | Capacity planning; optional for registrant. |
| `Registration` | `accessibilityNeeds` | Sensitive/special-category-adjacent | Optional | Yes | Collected only to provide accommodations; never mandatory for RSVP completion. |
| `Registration` | `consentVersion` / consent flags | Compliance metadata | Yes (if consent flow applies) | Yes | Proof of notice/consent state; avoids storing full policy text repeatedly. |
| `Registration` | `notes` | Potentially sensitive free text | Optional | Yes | Optional field; retention-limited and anonymized per policy. |
| `Registration` | `contactEmail` / `contactPhone` / `guestName` (if used) | Direct identifier | Optional | Yes (if enabled by form config) | Only when operationally needed; anonymized after retention window or DSAR. |
| `DeepLinkToken` | `jti`, `eventId`, `subjectPersonId`, `exp`, `aud`, scope | Indirect/security identifiers | Yes | No (except consumption state by service) | Minimum token claims required for secure binding and replay protection. |
| `AuditLog` | `actorId`, `requestId`, `traceId`, action/outcome, policy fields, hashed client metadata | Accountability/security metadata | Yes | No | Required for non-repudiation and compliance evidence; client network/user-agent stored as hashes. |

### Inventory governance rules
- New PII fields require Privacy + Security review with documented purpose, lawful basis, retention, and deletion behavior before release.
- Optional fields must remain optional in API/schema unless legal mandate is approved and documented.
- Free-text fields must be monitored and minimized; structured alternatives are preferred.

## 3) Governance evidence cadence (access reviews + authZ policy changes)

| Control area | Cadence | Owner | Required evidence artifacts | Retention of evidence |
|---|---|---|---|---|
| Role/access review (all privileged/internal roles) | **Monthly** reviewer-led check; **Quarterly** formal certification | Security Owner + System Owner | Export of active principals/roles, review decisions (keep/revoke/change), remediation tickets, completion attestation | 7 years |
| Joiner/Mover/Leaver access adjustment | Within **1 business day** of HR/system-of-record change | IAM Ops | Provisioning/deprovisioning logs, ticket/workflow IDs, approval records | 7 years |
| AuthZ policy baseline review (deny-by-default matrix coverage) | **Quarterly** | App Security Architect | Current policy snapshot, route coverage report, diff vs prior baseline, sign-off record | 7 years |
| AuthZ policy change control (standard) | Per change; pre-deploy approval + post-deploy verification within **48h** | Change Owner + Security Reviewer | PR/commit link, approved change request, policy diff, test evidence, deployment record, rollback plan | 7 years |
| Emergency authZ policy change | Immediate implementation; retrospective approval within **24h** | Incident Commander + Security Reviewer | Incident ID, emergency justification, applied diff, retrospective approval, compensating controls | 7 years |
| Audit trail integrity verification | **Daily** automated check; **Monthly** manual exception review | Security Operations | Integrity check job output, alert history, exception handling records | 7 years |

### Release-gate closure statement
- Lawful basis mapping is explicitly documented for all in-scope processing activities.
- PII inventory/classification and minimization rationale are documented at field level.
- Access review and authZ policy-change evidence cadence, ownership, and retention are defined.

These controls close all outstanding Stage 6 governance gaps.

**PrivacyCompliance Cross-check: PASS**
