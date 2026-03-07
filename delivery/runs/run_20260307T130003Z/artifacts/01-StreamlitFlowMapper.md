# Stage 1 — StreamlitFlowMapper

## Mission Output
Map current Streamlit behavior for parity-safe rewrite planning.

## Critical flows (priority order)
1. People lifecycle (directory + profile CRUD)
2. Tasks operations
3. Outreach + segments workflow
4. Events + public registration deep links
5. Deliberation lifecycle (configure/participate/moderate/report)
6. Dashboard/map/data operations
7. Admin controls
8. Due diligence integration

## Parity constraints for rewrite
- Preserve deep-link entrypoints (`questionnaire`, `event_registration`, `survey`) and URL contracts.
- Preserve access-mode behavior (`PUBLIC_ONLY`, supporter access code gates).
- Preserve people workflows currently embedded in `app.py`.
- Preserve deliberation dual mode (public + admin).

## Wave plan
- Wave 1: Core continuity (People, Tasks, event registration route, deliberation participation).
- Wave 2: Campaign orchestration + moderation + integrations.
- Wave 3: Advanced analytics/admin/DD parity.

## Artifact status
- Explicit artifact delivered: YES
- Gate status: INFO (non-gating discovery stage)
