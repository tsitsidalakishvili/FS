# Freedom Square CRM + Deliberation

This folder now contains the **combined** application:
- **CRM UI** (Streamlit): supporters, members, maps, analytics
- **Deliberation API** (FastAPI): conversations, comments, votes, analysis

## Folder structure
```
./
  app.py                  # CRM + Deliberation UI (platform app)
  AIteam/
    console.py            # Agent Chain console UI
    agent_chain/          # in-repo multi-agent framework (runs are not committed)
  .env                    # local env config (not committed)
  .env.example            # env template
  deliberation/
    api/                  # FastAPI service
    data/                 # seed CSVs
    scripts/              # import/generate helpers
```

## Run locally

### 1) Start deliberation API
```
cd deliberation/api
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8010
```

### 2) Start CRM UI
```
python -m streamlit run app.py --server.address 0.0.0.0 --server.port 8506
```

Open: `http://localhost:8506`

## Agent Chain Console (multi-agent dev console)
The console orchestrates specialist agents over a shared run state (blackboard), keeps run history, and can optionally apply safe code changes and run git automation.

### 1) Configure env
- Copy `.env.example` to `.env` and set at least:
  - `OPENAI_API_KEY`
  - `OPENAI_MODEL` (optional)
  - `SLACK_WEBHOOK_URL` (optional)

### 2) Run the console
```
python -m streamlit run AIteam/console.py --server.address 0.0.0.0 --server.port 8501
```

## Seed data
```
cd deliberation/scripts
python import_comments.py --csv ../data/georgian_politics_comments.csv
```

Generate votes CSV:
```
python generate_votes_csv.py --conversation-id <id> --output ../data/georgian_politics_votes.csv
python import_votes.py --csv ../data/georgian_politics_votes.csv
```

## Access modes
- **Supporter mode** (default): CRM + deliberation tab
- **Public-only**: set `PUBLIC_ONLY=true` in `.env`
- **Supporter gate**: set `SUPPORTER_ACCESS_CODE` in `.env`
