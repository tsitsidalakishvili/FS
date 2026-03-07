# Freedom Square Frontend (Next.js)

Production-oriented Next.js + TypeScript + Tailwind UI aligned to the FastAPI deliberation contracts in:

- `../deliberation/api/app/routes.py`
- `../deliberation/api/app/schemas.py`

## Route / page structure

### Core deliberation routes

- `/` — conversations index with quick actions
- `/conversations/new` — create conversation
- `/conversations/[conversationId]/participate` — vote + submit comments
- `/conversations/[conversationId]/configure` — update settings, seed comments, simulate votes
- `/conversations/[conversationId]/moderate` — approve/reject pending comments
- `/conversations/[conversationId]/reports` — run analysis + metrics report

### Public questionnaire parity route

- `/questionnaire/deliberation?conversation_id=<id>`
  - card-style one-question-at-a-time voting
  - anonymous comment submission

### Due diligence parity route

- `/due-diligence`
  - workflow architecture steps
  - external app launch with prefilled query params

## Reusable UI components

- `src/components/app-shell.tsx` — responsive app shell + nav
- `src/components/conversation-card.tsx` — reusable conversation summary/actions
- `src/components/conversation-tabs.tsx` — conversation route tabs
- `src/components/vote-button-group.tsx` — standardized vote actions
- `src/components/report-metrics-table.tsx` — reusable report table
- `src/components/ui/*` — button/card/input/select/textarea/badge + loading/error/empty states

## Typed API client + contracts

- `src/lib/api/contracts.ts`
  - Zod schemas mirroring documented FastAPI request/response shapes
- `src/lib/api/client.ts`
  - typed client methods for documented endpoints only
  - runtime contract validation
  - normalized `ApiError` handling

## State/query strategy

- TanStack Query (`src/providers/query-provider.tsx`)
- Query key factory (`src/lib/api/query-keys.ts`)
- Route-level hooks (`src/lib/api/hooks.ts`)
  - invalidate + refetch by concern (conversations/comments/report)
  - optimistic UX through loading/error/success mutation states

## Environment variables

Create `.env.local` in this folder:

```bash
NEXT_PUBLIC_DELIBERATION_API_URL=http://localhost:8010
NEXT_PUBLIC_DUE_DILIGENCE_APP_URL=
```

## Local development

```bash
cd frontend
npm install
npm run dev
```

## Tests

```bash
npm run test
```

Current test coverage includes:

- typed API client contract handling (`src/lib/api/client.test.ts`)
- reusable vote button behavior (`src/components/vote-button-group.test.tsx`)
