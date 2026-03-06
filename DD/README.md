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

## Schedule weekly job (Windows)

1. Update paths in `schedule_weekly.ps1`.
2. Run in PowerShell to register the task:
   - `./schedule_weekly.ps1`

## Notes

- News ingestion uses NewsAPI if `NEWS_API_KEY` is set.
- OpenSanctions enrichment requires `OPENSANCTIONS_API_KEY` (get a key from OpenSanctions).
- The current UI includes placeholders for enrichment and reporting.
