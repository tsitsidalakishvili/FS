# Graph-Centric Due Diligence Platform

Local-first relationship intelligence platform built with Streamlit and Neo4j.

## Prerequisites

- Python 3.11+
- Neo4j running locally (Docker recommended)

## Setup

1. Create a virtual environment and install dependencies:
   - `pip install -r requirements.txt`
2. Copy `.env.example` to `.env` and update Neo4j credentials.
3. Initialize Neo4j schema:
   - `python -m app.scripts.init_db`

## Run the app

- `streamlit run app/main.py`

## Weekly monitoring job

- `python -m app.scripts.run_weekly`

Phase 1 behavior:
- Weekly monitoring now creates `(:Person|:Company)-[:MENTIONED_IN]->(:NewsArticle)` links.
- Entity search uses Neo4j fulltext indexes (created by `init_db`).
- Ingestion writes stamp source + ingestion timestamp metadata on nodes/relationships.

## Schedule weekly job (Windows)

1. Update paths in `schedule_weekly.ps1`.
2. Run in PowerShell to register the task:
   - `./schedule_weekly.ps1`

## Notes

- News ingestion uses NewsAPI if `NEWS_API_KEY` is set.
- OpenSanctions enrichment requires `OPENSANCTIONS_API_KEY` (get a key from OpenSanctions).
- The current UI includes placeholders for enrichment and reporting.

## OpenSanctions for Georgia context

The DD app now auto-discovers and prioritizes Georgia-relevant OpenSanctions datasets from the live API catalog.

Core Georgia datasets:
- `ge_declarations` — Georgia Public Official Asset Declarations
- `ge_ot_list` — Georgian Otkhozoria–Tatunashvili List
- `ext_ge_company_registry` — Georgian Company Registry

Context datasets (broader risk context):
- `wd_peps`
- `sanctions`

In the app (Enrichment panel), use:
- **Dataset preset** selector (Georgia-focused)
- **Run Georgia sweep (core datasets)** to import all core Georgia datasets for the selected subject in one pass.
