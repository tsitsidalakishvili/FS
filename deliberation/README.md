# Deliberation Module

This folder contains the Polis-style deliberation backend, scripts, and seed data.

## API
`deliberation/api` is a FastAPI service that provides:
- conversations
- comments + moderation
- voting
- analysis (clusters, consensus, polarizing)
- mobile participation PWA at `/participate`

### Participation PWA
The API serves a mobile-first participation web app:
- `GET /participate` (app shell)
- `GET /participate/manifest.webmanifest`
- `GET /participate/sw.js`

Mobile app data endpoints:
- `GET /participation/conversations` (open conversations)
- `GET /participation/conversations/{conversation_id}/deck?limit=20&cursor=...`
- `POST /vote` with header `X-Participant-Id`
- `POST /conversations/{conversation_id}/comments` (optional)

Optional abuse controls (disabled by default):
- `PARTICIPATION_INVITE_TOKENS` (comma-separated invite tokens; requires `X-Invite-Token`)
- `VOTE_RATE_LIMIT_PER_MINUTE` (integer limit per anonymous participant hash)

## Scripts
`deliberation/scripts` includes:
- `import_comments.py`
- `generate_votes_csv.py`
- `import_votes.py`

## Data
`deliberation/data` contains seed CSVs.
