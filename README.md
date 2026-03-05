# Freedom Square CRM + Deliberation

This folder now contains the **combined** application:
- **CRM UI** (Streamlit): supporters, members, maps, analytics
- **Deliberation API** (FastAPI): conversations, comments, votes, analysis

## Folder structure
```
TM/
  app.py                  # CRM + Deliberation UI
  .env                    # shared env config
  deliberation/
    api/                  # FastAPI service
    data/                 # seed CSVs
    scripts/              # import/generate helpers
```

## Run locally

### 1) Start deliberation API
```
cd TM/deliberation/api
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8010
```

### 2) Start CRM UI
```
cd TM
python -m streamlit run app.py --server.address 0.0.0.0 --server.port 8506
```

Open: `http://localhost:8506`

## Seed data
```
cd TM/deliberation/scripts
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
