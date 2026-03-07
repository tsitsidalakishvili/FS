# Environment Configuration Specification

This repository uses environment variables for runtime configuration.  
Do **not** commit secrets into the repository; only commit templates (`.env.example`).

## Secret management policy

- Local development: use a local `.env` file (gitignored).
- CI/CD and production: use your platform secret manager (GitHub Actions Secrets, Vault, AWS/GCP secret managers, etc).
- Never hardcode credentials, tokens, DSNs, or API keys in Python modules or YAML manifests.

## Variables by service

### Shared / global

| Variable | Required | Secret | Description |
| --- | --- | --- | --- |
| `LOG_LEVEL` | No | No | Logging level (`INFO`, `WARNING`, `ERROR`, `DEBUG`). |
| `APP_RELEASE` | No | No | Release identifier (commit SHA/tag). |
| `SENTRY_ENVIRONMENT` | No | No | Sentry environment name (e.g. `staging`, `production`). |
| `SENTRY_TRACES_SAMPLE_RATE` | No | No | Sentry tracing sample rate `0.0..1.0`. |
| `SENTRY_PROFILES_SAMPLE_RATE` | No | No | Sentry profiling sample rate `0.0..1.0`. |
| `SENTRY_SEND_DEFAULT_PII` | No | No | Include PII in Sentry events (`true/false`). |
| `SENTRY_DSN` | No | Yes | Default Sentry DSN fallback for all services. |

### CRM (Streamlit UI)

| Variable | Required | Secret | Description |
| --- | --- | --- | --- |
| `DELIBERATION_API_URL` | Yes | No | Base URL for deliberation API. |
| `DELIBERATION_API_FALLBACK_URL` | No | No | Fallback URL if primary URL is local/unreachable. |
| `DELIBERATION_API_TIMEOUT_S` | No | No | API timeout in seconds. |
| `PUBLIC_ONLY` | No | No | Enables public-only mode. |
| `SUPPORTER_ACCESS_CODE` | No | Yes | Optional supporter access gate value. |
| `CRM_SENTRY_DSN` | No | Yes | CRM-specific Sentry DSN (overrides `SENTRY_DSN`). |
| `SENTRY_ENABLE_STREAMLIT` | No | No | Enables/disables Streamlit Sentry init. |

### Deliberation API (FastAPI)

| Variable | Required | Secret | Description |
| --- | --- | --- | --- |
| `NEO4J_URI` | Yes | No | Neo4j Bolt endpoint. |
| `NEO4J_USER` | Yes | No | Neo4j username. |
| `NEO4J_PASSWORD` | Yes | Yes | Neo4j password. |
| `NEO4J_DATABASE` | No | No | Neo4j database name (default `neo4j`). |
| `DELIBERATION_DB_MODE` | No | No | `local` or `sandbox` DB mode selector. |
| `DELIBERATION_NEO4J_URI` | No | No | Explicit DB URI override for deliberation API. |
| `DELIBERATION_NEO4J_USER` | No | No | Explicit DB user override. |
| `DELIBERATION_NEO4J_PASSWORD` | No | Yes | Explicit DB password override. |
| `DELIBERATION_NEO4J_DATABASE` | No | No | Explicit DB database override. |
| `DELIBERATION_SKIP_DB_INIT` | No | No | Skip DB constraints init on startup (useful for tests). |
| `ANON_SALT` | No | Yes | Salt used to hash participant identifiers. |
| `REDIS_URL` | No | No | Redis endpoint for optional cache (`redis://host:6379/0`). |
| `REDIS_CACHE_TTL_SECONDS` | No | No | Redis cache TTL for list endpoints. |
| `DELIBERATION_SENTRY_DSN` | No | Yes | API-specific Sentry DSN (overrides `SENTRY_DSN`). |

### Additional integrations

| Variable | Required | Secret | Description |
| --- | --- | --- | --- |
| `SLACK_WEBHOOK_URL` | No | Yes | Incoming webhook URL for Slack integration. |
| `WHATSAPP_GROUP_WEBHOOK_TOKEN` | No | Yes | Token for WhatsApp webhook auth. |
| `OPENAI_API_KEY` | No | Yes | OpenAI API key for Agent Chain console. |

## Validation in CI

`scripts/ci/deploy_readiness.py` validates:

- required deployment/config files exist
- required env keys are present in `.env.example`
- secret-like keys in `.env.example` do not include real values
