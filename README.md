# Freedom Square CRM + Deliberation

This folder now contains the **combined** application:
- **CRM UI** (Streamlit): supporters, members, maps, analytics
- **Deliberation API** (FastAPI): conversations, comments, votes, analysis

## Folder structure
```
./
  app.py                  # CRM + Deliberation UI entrypoint
  crm/                    # modularized CRM app code
  data/                   # sample CSVs (imports)
  scripts/                # local utilities (e.g., testneo4j.py)
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

### (Optional) Use from Cursor Terminal (CLI)
If you want to stay mostly inside Cursor (without the Streamlit console UI), you can drive the chain via:
```
python -m AIteam.chain_cli create-run "Add a new volunteer follow-up workflow in app.py"
python -m AIteam.chain_cli autopilot --run-id <RUN_ID> --text "Plan the change and produce a bounded code_change_plan.json"
python -m AIteam.chain_cli message --run-id <RUN_ID> --agent Supervisor --text "Give me next steps"
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

## Streamlit Cloud + Render setup (Deliberation)
If your Streamlit app is deployed publicly, `localhost` is not reachable from Streamlit Cloud.

Set this in Streamlit app **Secrets**:
```toml
DELIBERATION_API_URL = "https://fs-deliberation-api.onrender.com"
```

Optional timeout override (recommended for free Render cold starts):
```toml
DELIBERATION_API_TIMEOUT_S = "70"
```

Optional fallback (used when primary URL is localhost/unreachable):
```toml
DELIBERATION_API_FALLBACK_URL = "https://fs-stns.onrender.com"
```

Notes:
- Free Render web services can sleep and take ~50+ seconds to wake.
- The app now uses a longer timeout automatically for `*.onrender.com` APIs.

## WhatsApp group chats connection
The Outreach page now supports WhatsApp group chat campaigns through a webhook connector.

Set these in `.env` (local) or Streamlit secrets (cloud):
```toml
WHATSAPP_GROUP_WEBHOOK_URL = "https://your-automation-endpoint.example/webhook"
WHATSAPP_GROUP_WEBHOOK_TOKEN = ""
```

How it works:
- Add your WhatsApp groups in **Outreach → WhatsApp group chats** (name + invite link).
- Write a campaign message and click **Send to WhatsApp group**.
- The app sends a POST request to your webhook; your automation layer (Make/Zapier/worker) delivers it to WhatsApp.

Webhook payload format:
```json
{
  "platform": "whatsapp",
  "channel": "group",
  "source": "outreach_page",
  "group": {
    "groupId": "uuid",
    "name": "Group Name",
    "inviteLink": "https://chat.whatsapp.com/..."
  },
  "message": "Campaign message text"
}
```

## Slack connection
You can connect Slack using an Incoming Webhook and send shareable links directly from:
- Questionnaire templates (survey + deliberation links)
- Events registration link sharing
- Admin page (test message)

Set these in `.env` (local) or Streamlit secrets (cloud):
```toml
SLACK_WEBHOOK_URL = "https://hooks.slack.com/services/XXX/YYY/ZZZ"
SLACK_USERNAME = "Freedom Square CRM"
```

## Due Diligence tab integration
The CRM **Due Diligence** tab now has:
- **How it works**: workflow-style architecture + block connection timeline
- **Actual app**: launch/embed the dedicated DD app

Set this in `.env` or Streamlit secrets to connect the external DD app:
```toml
DUE_DILIGENCE_APP_URL = "https://your-dd-app.example"
```
