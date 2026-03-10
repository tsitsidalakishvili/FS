# FS Deliberation (Standalone Directory)

This folder is a standalone Deliberation Streamlit app inside the monorepo.

It shares:
- one Deliberation backend (`/deliberation/api`)
- one Neo4j database
- shared UI/backend clients in `/crm`

## Run UI locally

From repo root:

```bash
streamlit run Deliberation/app.py
```

## Run API locally

```bash
python -m uvicorn deliberation.api.app.main:app --host 0.0.0.0 --port 8010
```

## Deploy

Use this file as app entrypoint:

- `Deliberation/app.py`
