# Stage 7 — FrontendEngineer

## First Rewrite Frontend Slice (aligned to Stage 6 backend)

This slice delivers the first production web-client paths for the in-scope Increment 1 domains:
- People
- Tasks
- Events
- Public event registration via deep-link token

Out of scope for this slice:
- Outreach/segments orchestration
- Deliberation lifecycle rewrite
- Dashboard/admin/full parity migration beyond routes listed below

---

## 1) UI routes/pages to implement now

Route base: `/app` for internal authenticated UI; `/public` for token-driven pages.

## Internal authenticated routes (must require valid OIDC session)
1. `GET /app/people`
   - Page: People directory
   - Capabilities now: search (`q`), include archived toggle, paginated/limited list, entrypoint to create/edit
   - Backend dependency: `GET /api/v1/people`

2. `GET /app/people/new`
   - Page: Create person
   - Capabilities now: submit minimal canonical profile fields allowed by backend
   - Backend dependency: `POST /api/v1/people`

3. `GET /app/people/:personId`
   - Page: Person profile edit
   - Capabilities now: update editable fields only; no direct delete in this slice
   - Backend dependency: `PATCH /api/v1/people/{personId}`

4. `GET /app/tasks`
   - Page: Task board/list
   - Capabilities now: filter by status/owner, create task, transition task status
   - Backend dependencies:
     - `GET /api/v1/tasks`
     - `POST /api/v1/tasks`
     - `PATCH /api/v1/tasks/{taskId}/status`

5. `GET /app/events`
   - Page: Event list + create event entry
   - Capabilities now: create event, open event detail
   - Backend dependency: `POST /api/v1/events`

6. `GET /app/events/:eventId`
   - Page: Event detail
   - Capabilities now: show event data, issue registration deep link, list registrations
   - Backend dependencies:
     - `GET /api/v1/events/{eventId}`
     - `POST /api/v1/events/{eventId}/deeplinks`
     - `GET /api/v1/events/{eventId}/registrations`

## Public routes (no internal OIDC; token-bound behavior)
7. `GET /public/event-registration`
   - Required query param: `token`
   - Page: Public registration form (registration-scoped fields only)
   - Backend dependency: `POST /api/v1/public/registrations`
   - Rule: never collect or send `eventId` from client payload

## Placeholder parity routes (preserve deep-link entrypoints)
8. `GET /public/questionnaire`
   - Behavior now: preserve URL contract and show migration notice/fallback handoff
   - Purpose: avoid breaking legacy links while feature is out of scope

9. `GET /public/survey`
   - Behavior now: preserve URL contract and show migration notice/fallback handoff
   - Purpose: avoid breaking legacy links while feature is out of scope

---

## 2) Component/state strategy

## Architecture choice
- Component model: feature-sliced pages with shared UI primitives.
- Data/state:
  - **Server state**: query/mutation client (cache + retry + invalidation).
  - **Local UI state**: form controls, filters, dialog state.
  - **Auth/session state**: centralized provider for OIDC token + role claims.

## Proposed frontend module shape
```text
frontend/
  src/
    app/
      routes.tsx
      providers/
        AuthProvider.tsx
        QueryProvider.tsx
    features/
      people/
        pages/PeopleListPage.tsx
        pages/PeopleCreatePage.tsx
        pages/PeopleDetailPage.tsx
        components/PeopleTable.tsx
        components/PersonForm.tsx
        api/peopleApi.ts
      tasks/
        pages/TasksPage.tsx
        components/TaskList.tsx
        components/TaskForm.tsx
        components/TaskStatusMenu.tsx
        api/tasksApi.ts
      events/
        pages/EventsPage.tsx
        pages/EventDetailPage.tsx
        components/EventForm.tsx
        components/DeepLinkPanel.tsx
        components/RegistrationTable.tsx
        api/eventsApi.ts
      publicRegistration/
        pages/PublicEventRegistrationPage.tsx
        components/PublicRegistrationForm.tsx
        api/publicRegistrationApi.ts
    shared/
      api/client.ts
      api/errors.ts
      ui/
      utils/deeplink.ts
```

## State rules
1. API data is canonical in query cache; do not duplicate response objects in global stores.
2. Mutations must invalidate specific query keys:
   - `people:list`, `people:detail:{id}`
   - `tasks:list`
   - `events:list`, `events:detail:{id}`, `events:registrations:{id}`
3. Public registration form stores only registration-scoped fields (`status`, `guestCount`, `accessibilityNeeds`, `consentVersion`, `notes`).
4. Auth gating is route-level plus component-level capability checks (hide forbidden actions and handle server `403` safely).

---

## 3) API integration contract + error handling

## Shared API client contract
- Base URL: `/api/v1`
- Headers:
  - Internal routes: `Authorization: Bearer <oidc_access_token>`
  - Public registration: no internal token; token supplied in body
  - `X-Request-ID` propagated if present from app runtime
- Timeouts/retries:
  - GET retry: up to 2 retries on transient network failure/5xx
  - POST/PATCH: no automatic retry except idempotent-safe flows explicitly marked

## Endpoint usage in this slice
- People:
  - `GET /people?q=&limit=&includeArchived=`
  - `POST /people`
  - `PATCH /people/{personId}`
- Tasks:
  - `GET /tasks?status=&ownerId=&limit=`
  - `POST /tasks`
  - `PATCH /tasks/{taskId}/status`
- Events:
  - `POST /events`
  - `GET /events/{eventId}`
  - `POST /events/{eventId}/deeplinks`
  - `GET /events/{eventId}/registrations?limit=`
- Public:
  - `POST /public/registrations` with `{ token, status, guestCount, accessibilityNeeds, consentVersion, notes }`
  - Explicitly excluded from payload: `eventId`, canonical `Person` fields

## Error-handling matrix (UI behavior)
| API status | Meaning | UI handling |
|---|---|---|
| `400` | Validation error / malformed request | Inline field errors when possible; otherwise form-level error banner |
| `401` | Unauthenticated / invalid token | Internal: redirect to sign-in. Public: show token invalid/expired message |
| `403` | Forbidden | Show permission error panel; hide action controls on subsequent render |
| `404` | Resource not found | Show not-found state with return navigation |
| `409` | Conflict (token replay/status collision) | Show deterministic conflict message and safe recovery action (refresh/back to event) |
| `422` | Semantic validation failure | Map backend validation details to field messages |
| `429` | Rate-limited | Show retry-after messaging and disable submit temporarily |
| `5xx` | Server/system issue | Non-destructive error banner + retry action; keep unsaved form state |

## Frontend error object normalization
- Parse backend error payload into a single `AppError` shape:
  - `status`
  - `code` (if supplied)
  - `message` (safe user-facing fallback)
  - `requestId`/`traceId` (if supplied)
  - `fieldErrors[]` (optional)
- Always log normalized errors with route + action metadata (PII-redacted).

---

## 4) Parity notes for Streamlit deep links

From Stage 1 parity constraints, preserve deep-link entrypoints:
- `questionnaire`
- `event_registration`
- `survey`

## Parity decisions for this slice
1. **`event_registration`**: fully implemented in rewrite via `/public/event-registration?token=...`.
2. **`questionnaire` and `survey`**: URL contracts preserved as placeholder routes to prevent broken inbound links; show controlled fallback/handoff until those domains migrate.
3. Query-string contract must remain stable for inbound links; unknown params are ignored but retained in telemetry for compatibility analysis.
4. Public flow remains token-bound and does not allow client-selected event identity, matching backend security contract.
5. Link-generated UX from internal event detail must produce copy/open actions that preserve opaque token values exactly.

---

## 5) Frontend test plan

## A) Unit tests
- API client:
  - Auth header injection for internal routes
  - Error normalization (`AppError`) for all key status codes
- Form validation:
  - Public registration field allowlist (no `eventId`, no canonical `Person` fields)
  - People/task/event form required-field guards
- Deep-link utilities:
  - Token extraction/parsing from URL query

## B) Component tests
- People list/search rendering and loading/error states
- Task status transition control behavior for success/failure
- Event detail deep-link issuance panel behavior
- Public registration form:
  - happy path submit
  - invalid/expired token UX
  - conflict (`409`) UX

## C) Route/integration tests (mock API)
- Auth-guard redirects for internal routes when session missing
- End-to-end page-level flows:
  1. Create person -> edit person
  2. Create task -> change status -> refetch list
  3. Create event -> issue deep link -> open public route -> submit registration
- Negative paths:
  - `403` on protected actions shows forbidden state
  - `404` event/person routes show not-found page
  - `5xx` shows recoverable error with retry

## D) E2E smoke (real backend in CI environment)
- Internal authenticated journey:
  - create person, create task, create event, issue deeplink
- Public journey:
  - open deeplink URL with token and submit registration
- Verification:
  - event registration list displays submitted record
  - replay submit yields deterministic conflict behavior

## E) Parity regression tests for deep links
- Existing inbound link shapes for `event_registration`, `questionnaire`, `survey` do not break routing.
- `event_registration` preserves token-based flow semantics.
- Placeholder routes return deterministic migration notice state (not generic 404).

FrontendEngineer Artifact: READY
