"""10-slide client demo presentation for Freedom Square CRM + Deliberation."""

import streamlit as st


_SLIDES = [
    {
        "number": 1,
        "title": "Freedom Square — Civic Platform Overview",
        "icon": "🏛️",
        "content": """
**What we built:**  
An end-to-end civic engagement platform that unifies supporter relationship management,
campaign coordination, and structured public deliberation in a single, web-based tool.

**Core pillars:**
- 🗂 **CRM** — track every supporter, member, volunteer, and contact in one graph
- 🗳 **Deliberation** — run transparent, AI-assisted civic conversations and votes
- 🤖 **AI Team** — a multi-agent assistant that helps staff plan, analyze, and act

**Who it is for:**  
Political campaigns, civic organisations, community movements, and local governments
that need to move fast, stay organised, and engage citizens at scale.
""",
    },
    {
        "number": 2,
        "title": "The Problem We Solve",
        "icon": "🎯",
        "content": """
**Campaigns and civic groups today struggle with:**

| Problem | Impact |
|---|---|
| Supporters scattered across spreadsheets & email lists | Missed follow-ups, duplicate contacts |
| No single view of who is doing what | Staff duplication, volunteer burn-out |
| Public feedback collected but never acted on | Citizen disengagement |
| Data locked in siloed tools (NationBuilder, Mailchimp, etc.) | High cost, no graph insight |
| No AI assistance for field staff | Slow decision-making |

**Our answer:** one platform, one graph, real-time intelligence.
""",
    },
    {
        "number": 3,
        "title": "Technology Architecture",
        "icon": "⚙️",
        "content": """
```
┌─────────────────────────────────────────────────┐
│               Browser (any device)               │
└──────────────────────┬──────────────────────────┘
                       │ HTTPS
         ┌─────────────▼──────────────┐
         │    Streamlit UI  (app.py)   │  ← Python / fast to ship
         └──────┬──────────────┬───────┘
                │              │ REST
       Bolt/TLS │        ┌─────▼──────────────┐
    ┌───────────▼───┐    │  Deliberation API   │  ← FastAPI + Uvicorn
    │  Neo4j Graph  │    │  (deliberation/api) │
    │  (AuraDB /    │    └─────────────────────┘
    │   Desktop)    │
    └───────────────┘
                │
         ┌──────▼──────┐
         │  AI Team     │  ← OpenAI GPT-4 + agent chain
         │  (AIteam/)  │
         └─────────────┘
```

**Stack highlights:**  
Python 3.11 · Streamlit · FastAPI · Neo4j · OpenAI API · Docker · Altair · PyDeck
""",
    },
    {
        "number": 4,
        "title": "Graph Data Model (Neo4j)",
        "icon": "🕸️",
        "content": """
**Why a graph database?**  
Relationships between people, campaigns, and activities are first-class citizens —
not foreign keys in flat tables.

**Key nodes:**
`Person · SupporterType · Tag · Skill · Address · Campaign · Event · Contribution · Activity · Path · Goal`

**Key relationships (sample):**
```
(Person)-[:CLASSIFIED_AS]→(SupporterType)
(Person)-[:LIVES_AT]→(Address)
(Person)-[:SUPPORTS / :VOLUNTEERS_FOR / :DONATED_TO]→(Campaign)
(Person)-[:REGISTERED_FOR]→(Event)
(Person)-[:REFERRED_BY]→(Person)   ← referral network
(Person)-[:HAS_ACTIVITY]→(Activity)
(Nation)-[:HAS_GOAL]→(Goal)-[:HAS_PATH]→(Path)
```

**What this enables:**
- Segment by any combination of tags, skills, geography, and behaviour in milliseconds
- Traverse referral chains to find your best advocates
- Track per-person journey through campaign paths
""",
    },
    {
        "number": 5,
        "title": "CRM — Supporters & Members",
        "icon": "👥",
        "content": """
**People hub — everything about each contact in one place:**

- Full profile: name, email, phone, address, gender, age, social links
- Classification: **Supporter** vs **Member** (auto-derived from graph tags)
- Effort score, events attended, referrals given, donations made
- Free-text "about" and time-availability fields
- Inline editing with instant Neo4j write-back

**Segmentation engine:**
- Filter by supporter type, tag, skill, involvement area, geography
- Boolean set operations with optional Venn diagram visualisation
- Save named segments and export to CSV

**Import / Export:**
- Bulk CSV import (NationBuilder-compatible columns)
- One-click CSV export of any filtered view
""",
    },
    {
        "number": 6,
        "title": "Engagement Tools — Tasks, Events & Volunteers",
        "icon": "📋",
        "content": """
**Tasks**
- Create, assign, and track tasks per person (Open → In Progress → Done)
- Due dates, descriptions, and status filters
- Dashboard "action feed" always shows what needs attention today

**Events**
- Create events with date, location, capacity, and status
- Register attendees directly from People search
- Track attendance counts and open slots

**Volunteers**
- Dedicated volunteer roster with skill matching
- See who is available and when
- Link volunteers to campaigns and activities

**Outreach**
- Log outreach activities (call, email, meeting, door-knock)
- Track subject, outcome, and next-action per contact
- Surfaced in the dashboard action feed

All of these write directly to the Neo4j graph — no sync lag, no dual entry.
""",
    },
    {
        "number": 7,
        "title": "Map & Geographic Intelligence",
        "icon": "🗺️",
        "content": """
**Interactive map powered by PyDeck (WebGL):**

- Plot every contact as a geo-point (lat/lon from address geocoding)
- Colour-code by supporter type, tag, or custom segment
- Heat-map density layer to find geographic clusters
- Click a marker to open the full person profile

**Why this matters for campaigns:**
- Identify under-served neighbourhoods at a glance
- Route canvassers and door-knockers efficiently
- Correlate event turnout with address density

**Data flow:**
```
Address text → geocoded lat/lon → stored on Person node
               → rendered live on PyDeck ScatterplotLayer
```
""",
    },
    {
        "number": 8,
        "title": "Deliberation — Structured Civic Dialogue",
        "icon": "🗳️",
        "content": """
**What is the Deliberation module?**  
A purpose-built platform for running transparent, structured public conversations
— inspired by Pol.is and participatory democracy principles.

**How it works:**
1. **Conversations** — create a topic with a public URL
2. **Statements** — participants submit short statements / proposals
3. **Voting** — others vote Agree / Disagree / Pass on each statement
4. **AI Analysis** — GPT-4 clusters statements into opinion groups and surfaces consensus

**Key features:**
- Moderation queue: approve / reject statements before publishing
- Real-time vote tallies and participation metrics
- CSV export of raw votes for independent analysis
- Accessible via public link — no login required for citizens

**FastAPI backend** keeps the Deliberation service independently deployable
and consumable by third-party apps via REST.
""",
    },
    {
        "number": 9,
        "title": "AI Team — Multi-Agent Assistant",
        "icon": "🤖",
        "content": """
**What is the AI Team?**  
An internal multi-agent framework (inspired by AutoGPT / CrewAI) that lets
staff and developers orchestrate specialist AI agents over a shared "blackboard".

**Agents available:**
| Agent | Role |
|---|---|
| Supervisor | Breaks down goals into sub-tasks, delegates |
| Analyst | Queries Neo4j, interprets CRM data |
| Writer | Drafts emails, posts, policy summaries |
| Coder | Proposes and applies safe code changes |
| Outreach | Plans canvassing and volunteer campaigns |

**How staff use it:**
- Open the AI Console (`AIteam/console.py`) via Streamlit
- Type a high-level goal: *"Plan our volunteer drive for next Saturday"*
- Agents collaborate, produce a structured plan, and optionally apply changes

**Chatbox on Dashboard:**  
An embedded conversational interface lets any staff member ask questions
about the CRM data in plain English — no Cypher required.
""",
    },
    {
        "number": 10,
        "title": "Deployment, Security & Next Steps",
        "icon": "🚀",
        "content": """
**Deployment options:**

| Option | Detail |
|---|---|
| **Local** | Neo4j Desktop + `streamlit run app.py` |
| **Cloud (recommended)** | Docker image → any container host (AWS, GCP, Fly.io) |
| **Neo4j AuraDB** | Fully managed graph, TLS, zero ops |
| **Streamlit Community Cloud** | One-click deploy from GitHub |

**Security controls:**
- Supporter access code gates the full CRM (set `SUPPORTER_ACCESS_CODE` in `.env`)
- `PUBLIC_ONLY` mode exposes only the Deliberation tab to citizens
- All secrets via environment variables — nothing hard-coded
- Neo4j connection over encrypted Bolt/TLS

**Roadmap (next 90 days):**
- [ ] Email / SMS outreach integration (SendGrid, Twilio)
- [ ] NationBuilder two-way sync
- [ ] Mobile-optimised canvassing view
- [ ] Role-based access control (admin / staff / read-only)
- [ ] Multi-language UI (Georgian, English, Russian)

**Questions? Let's discuss how we tailor this to your campaign.**
""",
    },
]


def render_slides_page():
    st.subheader("📊 Client Demo — Solution Presentation")
    st.caption("10 slides describing the Freedom Square CRM + Deliberation platform.")

    st.markdown("---")

    total = len(_SLIDES)
    if "slide_index" not in st.session_state:
        st.session_state.slide_index = 0

    # Navigation controls (top)
    nav_cols = st.columns([1, 6, 1])
    with nav_cols[0]:
        if st.button("◀ Prev", disabled=st.session_state.slide_index == 0, use_container_width=True):
            st.session_state.slide_index -= 1
            st.rerun()
    with nav_cols[1]:
        st.markdown(
            f"<p style='text-align:center; color:#6b7280; margin:0;'>Slide "
            f"{st.session_state.slide_index + 1} of {total}</p>",
            unsafe_allow_html=True,
        )
    with nav_cols[2]:
        if st.button("Next ▶", disabled=st.session_state.slide_index == total - 1, use_container_width=True):
            st.session_state.slide_index += 1
            st.rerun()

    slide = _SLIDES[st.session_state.slide_index]

    # Slide card
    st.markdown(
        f"""
<div style="
    background: linear-gradient(135deg, #1e3a5f 0%, #2d6a4f 100%);
    border-radius: 16px;
    padding: 40px 48px;
    margin: 16px 0;
    min-height: 480px;
    box-shadow: 0 4px 24px rgba(0,0,0,0.18);
">
  <div style="font-size:3rem; margin-bottom:8px;">{slide['icon']}</div>
  <div style="
    font-size:0.85rem;
    color:#a7c4bc;
    letter-spacing:0.12em;
    text-transform:uppercase;
    margin-bottom:4px;
  ">Slide {slide['number']} of {total}</div>
  <h2 style="color:#ffffff; margin:0 0 24px 0; font-size:1.8rem;">{slide['title']}</h2>
</div>
""",
        unsafe_allow_html=True,
    )

    # Content rendered natively (supports markdown tables, code blocks, etc.)
    st.markdown(slide["content"])

    st.markdown("---")

    # Thumbnail strip
    st.markdown("**Jump to slide:**")
    thumb_cols = st.columns(total)
    for i, s in enumerate(_SLIDES):
        with thumb_cols[i]:
            is_active = i == st.session_state.slide_index
            label = f"{'**' if is_active else ''}{s['icon']} {s['number']}{'**' if is_active else ''}"
            if st.button(label, key=f"thumb_{i}", use_container_width=True):
                st.session_state.slide_index = i
                st.rerun()
