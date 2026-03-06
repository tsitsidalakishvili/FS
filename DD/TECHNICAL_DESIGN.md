# Technical Design Document
## Graph-Centric Due Diligence and Media Intelligence Platform
(Python + Streamlit + Neo4j, Local Deployment)

---

## 1. Purpose and Core Philosophy

The goal of this system is to build a relationship-first due diligence platform that aggregates publicly available information about people, companies, and organizations, with heavy emphasis on connections:

- Family members
- Friends and close associates
- Business partners
- Directors, shareholders, founders
- Shared addresses, education, employers
- Co-mentions in media
- Historical and indirect links

Entities do not exist in isolation.
Risk, influence, and context emerge from connections.

The system generates:

- Interactive graph-based intelligence views
- Weekly media monitoring linked to entities and their networks
- Human-readable due diligence reports (PDF)

All data is publicly available, locally processed, and traceable to sources.

---

## 2. High-Level Architecture

```
┌─────────────────────┐
│   Streamlit UI      │
│  (Search, Graph,    │
│   Reports, Alerts)  │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ Python Application  │
│ (Ingestion, NLP,    │
│  Enrichment Logic)  │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│     Neo4j Graph     │
│  (Entities + ALL    │
│   Relationships)    │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ External Sources    │
│ (OpenSanctions,     │
│  Wikipedia, News,   │
│  Registries, RSS)   │
└─────────────────────┘
```

---

## 3. Design Principle: Everything Is a Connection

### Key Rule

No fact is stored unless it is attached to a relationship or entity with provenance.

Examples:

- "John Doe is married" -> `(:Person)-[:SPOUSE_OF]->(:Person)`
- "Company A mentioned in scandal" -> `(:Company)-[:MENTIONED_IN]->(:NewsArticle)`
- "Two people appear together in articles" -> `(:Person)-[:CO_MENTIONED_WITH]->(:Person)`
- "Same home address" -> `(:Person)-[:SHARES_ADDRESS_WITH]->(:Person)`

---

## 4. Graph Data Model (Neo4j)

### 4.1 Core Node Types

#### Person

```
(:Person {
  id,
  full_name,
  aliases[],
  birth_date,
  nationality,
  summary,
  source_refs[]
})
```

#### Company / Organization

```
(:Company {
  id,
  name,
  registration_id,
  jurisdiction,
  industry,
  status,
  source_refs[]
})
```

#### NewsArticle

```
(:NewsArticle {
  id,
  title,
  source,
  published_date,
  url,
  sentiment,
  topics[],
  summary
})
```

#### Location

```
(:Location {
  id,
  type,        // country, city, address
  name
})
```

#### Sanctions / Watchlist Entry

```
(:SanctionList {
  name,
  authority,
  risk_level
})
```

---

### 4.2 Relationship Types (Most Important)

#### Family and Personal Relationships

```
(:Person)-[:SPOUSE_OF]->(:Person)
(:Person)-[:CHILD_OF]->(:Person)
(:Person)-[:SIBLING_OF]->(:Person)
(:Person)-[:RELATIVE_OF {degree}]->(:Person)
(:Person)-[:FRIEND_OF]->(:Person)
```

Confidence score can be attached when inferred (for example, from media).

---

#### Professional and Business Relationships

```
(:Person)-[:WORKS_FOR]->(:Company)
(:Person)-[:DIRECTOR_OF]->(:Company)
(:Person)-[:FOUNDER_OF]->(:Company)
(:Company)-[:OWNED_BY]->(:Company or :Person)
(:Company)-[:SUBSIDIARY_OF]->(:Company)
```

---

#### Media and Narrative Relationships

```
(:Person)-[:MENTIONED_IN]->(:NewsArticle)
(:Company)-[:MENTIONED_IN]->(:NewsArticle)
(:Person)-[:CO_MENTIONED_WITH]->(:Person)
(:Company)-[:CO_MENTIONED_WITH]->(:Company)
```

---

#### Location and Asset Relationships

```
(:Person)-[:RESIDES_IN]->(:Location)
(:Company)-[:REGISTERED_IN]->(:Location)
(:Person)-[:SHARES_ADDRESS_WITH]->(:Person)
```

---

#### Risk and Compliance

```
(:Person)-[:LISTED_IN]->(:SanctionList)
(:Company)-[:LISTED_IN]->(:SanctionList)
```

---

## 5. Entity Creation and Enrichment Flow

### Step 1: User Search

User searches for:

- Person
- Company
- OR uploads a list

### Step 2: Graph Lookup

- Check Neo4j for existing node
- If found -> load neighborhood graph
- If not -> create minimal node

### Step 3: Public Data Enrichment

Sources:

- OpenSanctions (sanctions, PEPs)
- Wikipedia / Wikidata
- Company registries
- Public news and RSS feeds

Each source:

- Adds nodes
- Adds relationships
- Adds source metadata

---

### Step 4: Relationship Expansion (Critical)

For every discovered person/company:

- Pull connected people
- Pull family references
- Pull business roles
- Pull co-mentions in media

This creates second-degree and third-degree graphs, which is where hidden risk often appears.

---

## 6. Media Monitoring (Weekly, Relationship-Aware)

### Schedule

- Weekly cron job (local)

### Process

For each entity and its close connections:

1. Search news by:
   - Name
   - Aliases
   - Known associates
2. Store articles
3. Link:
   - Entity -> Article
   - Co-mentioned entities -> Each other

### NLP Enrichment

- Sentiment (positive / neutral / negative)
- Topic extraction (for example, corruption, fraud, politics)
- Quote extraction (what the person/company said)

Example:

```
(:Person)-[:MENTIONED_IN {sentiment:-0.7}]->(:NewsArticle)
(:Person)-[:CO_MENTIONED_WITH]->(:Person)
```

---

## 7. Streamlit Frontend (Graph-First UI)

### Core Views

#### 1. Entity Overview

- Basic profile
- Risk indicators
- Key connections

#### 2. Relationship Graph View (Main Feature)

- Interactive Neo4j graph
- Filters:
  - Family only
  - Business only
  - Media only
  - Risk-related

#### 3. Media Timeline

- News over time
- Sentiment trend
- Connected entities per article

#### 4. Network Risk View

- "Show me risky people within 2 hops"
- "Show all companies linked to sanctioned individuals"

---

## 8. PDF Due Diligence Report

### Sections

1. Executive Summary
2. Entity Profile
3. Family and Close Associates
4. Business Network
5. Media and Public Statements
6. Risk Indicators
7. Source Appendix

### Key Feature

Every claim links back to a relationship and a source.

---

## 9. Local Deployment

### Stack

- Python 3.11
- Streamlit
- Neo4j (Docker)
- Cron (weekly jobs)

### No Cloud Required

- All data processed locally
- Optional API keys stored in `.env`

---

## 10. Why This Design Works

- Connections reveal hidden risk
- Graph queries answer complex questions
- New data fits naturally into relationships
- Scales from simple profiles to investigations
- Matches real investigative workflows

This architecture mirrors how journalists, compliance teams, and investigators actually think, not rows and columns, but networks of influence.

---

## 11. Next Steps for Developers

1. Set up Neo4j schema
2. Implement entity creation and enrichment pipeline
3. Build relationship inference logic
4. Add weekly media monitoring
5. Build Streamlit graph UI
6. Add PDF export
