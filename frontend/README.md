# CRM Rewrite Frontend

React + TypeScript + Vite UI for the Streamlit-to-production migration.

## Run

```bash
npm install
cp .env.example .env
npm run dev -- --host 0.0.0.0 --port 5173
```

## Environment

- `VITE_API_BASE_URL` (default `http://localhost:8020/api/v1`)
- `VITE_DELIBERATION_API_BASE_URL` (default `http://localhost:8010`)
- `VITE_DUE_DILIGENCE_APP_URL` (optional external DD app URL)

## Current parity routes

- `/app/dashboard`
- `/app/people`, `/app/people/new`, `/app/people/:personId`
- `/app/tasks`
- `/app/outreach`
- `/app/map`
- `/app/events`, `/app/events/:eventId`
- `/app/due-diligence`
- `/app/data`
- `/app/admin`
- `/app/deliberation`
- `/public/event-registration`
- `/public/questionnaire` (placeholder parity route)
- `/public/survey` (placeholder parity route)
