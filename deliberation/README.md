# Deliberation Module

This folder contains the Polis-style deliberation backend, scripts, and seed data.

## API
`deliberation/api` is a FastAPI service that provides:
- conversations
- comments + moderation
- voting
- analysis (clusters, consensus, polarizing)

## Scripts
`deliberation/scripts` includes:
- `import_comments.py`
- `generate_votes_csv.py`
- `import_votes.py`

## Data
`deliberation/data` contains seed CSVs.

## Secure Backend (FastAPI + SQLAlchemy + Redis)
`deliberation/api/app/secure_backend` provides a production-oriented backend slice with:
- contract-first request/response schemas
- strict Pydantic validation (`extra="forbid"`, strict payload parsing)
- token-based authN + role-based authZ
- structured error responses with request IDs
- request tracing middleware (`X-Request-ID`)
- SQLAlchemy models + Alembic migrations
- Redis-backed asynchronous job queue with idempotent submissions
- integration tests for API + DB + worker task flow

### Key files
- App entrypoint: `deliberation/api/app/secure_backend/main.py`
- OpenAPI artifact: `deliberation/api/openapi/secure_backend.openapi.json`
- Migration config: `deliberation/api/alembic.ini`
- Initial migration: `deliberation/api/alembic/versions/20260307_0001_create_analysis_jobs.py`
- Integration tests: `deliberation/api/tests/test_secure_backend_integration.py`

### Local commands
From `deliberation/api`:
- `python3 -m alembic -c alembic.ini upgrade head`
- `python3 -m pytest tests/test_secure_backend_integration.py -q`
- `python3 scripts/export_secure_openapi.py`
