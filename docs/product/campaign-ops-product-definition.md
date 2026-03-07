# Campaign Ops Product Definition (PM)

## 1) What to build and why

### Product objective
Build a lightweight campaign operations workflow that helps organizers turn supporter data into consistent follow-up actions and measurable progress.

### Value hypothesis
If organizers can reliably do this loop in one place:

1. define who to contact (segments),
2. create and execute follow-up actions (tasks/outreach),
3. track outcomes (task status + event activity),

then campaigns will increase volunteer activation and reduce missed follow-ups without needing a large operations team.

### Campaign ops value
- Faster organizer execution (less spreadsheet hopping).
- Better follow-up consistency (fewer dropped leads).
- Clearer weekly operating rhythm (what is open, overdue, done).
- Better leadership visibility into field progress.

---

## 2) Personas

| Persona | Primary goal | Current pain | Frequency |
|---|---|---|---|
| Field Organizer (primary) | Move supporters from interest to action | Hard to prioritize who to contact next; outreach lists and follow-up tracking are fragmented | Daily |
| Volunteer Coordinator | Activate volunteers and fill event capacity | Volunteer matching is manual; weak visibility into who is available and engaged | Daily/weekly |
| Campaign Operations Manager | Ensure execution quality across teams | Cannot quickly audit pipeline health (open, overdue, completion velocity) | Weekly |
| Campaign Director | See if operations are converting into real engagement | Outcomes are visible late and often anecdotal | Weekly |

---

## 3) Jobs to be done (JTBD)

1. **Segment execution job**  
   When a new field priority appears, I want to quickly define a segment of relevant people, so I can start outreach the same day.

2. **Follow-up pipeline job**  
   When outreach tasks are created, I want a single queue with clear status and due dates, so I can manage completion and avoid dropped follow-ups.

3. **Volunteer activation job**  
   When events need staffing, I want to identify high-fit supporters by skills/availability/engagement, so I can fill roles faster.

4. **Leadership visibility job**  
   When I review weekly operations, I want simple, trusted metrics (open, done, overdue, conversion signals), so I can adjust strategy early.

5. **Data quality job**  
   When new records are imported, I want quick data health checks, so segmentation and outreach decisions stay reliable.

---

## 4) MVP scope (small shippable iterations)

### MVP definition
MVP is a **closed-loop campaign ops workflow**:

- segment people,
- generate follow-up tasks,
- execute and update tasks,
- review weekly outcomes.

### MVP in-scope (Release 1)
1. Segment creation + saved reusable filters.
2. Segment preview and bulk task generation from segment results.
3. Task queue with status filters, due dates, and person linkage.
4. Basic dashboard metrics for task progress and pipeline health.
5. Event list visibility to support organizer planning context.

### MVP acceptance criteria
- Organizer can create a segment and generate tasks in under 5 minutes.
- Task queue can be filtered by status and group and updated without leaving page.
- Team can view weekly counts: open, in progress, done, cancelled, overdue.
- Data import path for supporters/members remains functional.

### Explicit non-goals (MVP)
- No built-in mass SMS/email sending engine.
- No predictive scoring or ML recommender for outreach priority.
- No full role-based permissions redesign (beyond existing access modes).
- No advanced BI/report builder.
- No mobile-native app.

---

## 5) Roadmap (incremental)

### Phase 0 (Now): Stabilize the existing ops loop
- Harden segment -> outreach -> task flow.
- Add missing task health indicators (overdue, due soon, completion trend).
- Define baseline metrics and instrumentation.

**Exit criteria:** team can run weekly outreach cycles in one tool without spreadsheet backfill.

### Phase 1 (Next): Improve execution quality
- Add duplicate-task guardrails for bulk creation.
- Add task ownership/assignee and queue views by organizer.
- Add quick outcome logging (contacted, unreachable, interested, committed).

**Exit criteria:** completion velocity and outreach outcome visibility improve week-over-week.

### Phase 2 (Later): Introduce campaign channels and conversion reporting
- Launch minimal messaging campaign module (starting with templates + send tracking).
- Add conversion funnel views: segmented -> contacted -> engaged -> volunteer action.
- Add cohort comparison by segment and campaign path.

**Exit criteria:** leadership can attribute ops effort to engagement outcomes.

---

## 6) Success metrics

### North-star metric
**Weekly Activated Supporters** = unique people who complete a meaningful action (task done linked to outreach outcome or event participation).

### Operational metrics (leading indicators)
- **Segment-to-task cycle time (median):** target < 5 min.
- **Task completion rate within 7 days:** target >= 60% in MVP, >= 75% by Phase 2.
- **Overdue task ratio:** target <= 20% in MVP, <= 10% by Phase 2.
- **Weekly active organizers:** target growth +25% from baseline by Phase 1.

### Outcome metrics (lagging)
- **Volunteer activation rate:** contacted -> active volunteer conversion.
- **Event staffing fill rate:** assigned volunteers / required volunteers.
- **Repeat engagement rate (30-day):** supporters with 2+ meaningful actions.

### Data quality and trust metrics (guardrails)
- Missing key fields (email, name, group, availability) below agreed threshold.
- Duplicate person/task incidents tracked and reduced release-over-release.
- Query/API response p95 within agreed operational threshold for list pages.

---

## 7) Risks, assumptions, dependencies

### Key assumptions
- Organizers will adopt task-based execution if setup is fast.
- Data quality is sufficient for segmentation to feel trustworthy.
- Weekly review cadence exists for metric-driven adjustment.

### Risks
- Low-quality imports produce noisy segments and weak trust.
- Feature scope drift into "full campaign suite" slows delivery.
- Missing ownership model in tasks limits accountability.

### Dependencies
- Neo4j query performance and schema consistency.
- Stable backend endpoints for task/segment operations.
- Streamlit UX polish for high-frequency organizer flows.

---

## 8) Team relationship map and operating model

| Collaboration | Purpose | Required output |
|---|---|---|
| Supervisor <-> PM | Clarify scope, priorities, acceptance criteria | Approved bounded plan with release goal, in-scope, non-goals |
| Supervisor <-> CampaignOpsExpert | Validate organizer workflow realism | Workflow validation notes and critical edge cases |
| PM <-> StreamlitEngineer | Align UX with product goals | UX flow aligned to JTBD and MVP acceptance criteria |
| Neo4jArchitect <-> BackendEngineer | Agree data boundaries and query/API approach | Data contract + query/API design notes |
| SecurityReviewer + PrivacyCompliance | Cross-check PII, secrets, access control, audit | Security/privacy sign-off checklist |
| QAReviewer | Define done and regression checks | Test matrix + release gate criteria |
| ExecutorEngineer | Implement only after bounded plan and sign-offs | Code changes linked to approved plan |

### Delivery gate (autopilot flow)
1. Supervisor produces bounded plan with PM acceptance criteria.
2. CampaignOpsExpert validates operational realism.
3. Architecture (Neo4j + backend) agrees data/API boundaries.
4. Security and privacy checks pass.
5. QA defines regression checks and "done".
6. ExecutorEngineer implements.

No implementation starts before steps 1-5 are complete.

---

## 9) Definition of done (for campaign ops increments)

An increment is done only when:
- Acceptance criteria are met and demoed.
- Non-goals are still respected (no scope creep).
- Security/privacy checklist passes for touched surfaces.
- Regression checks pass on core flows (people, segments, outreach/tasks, events, data import/export).
- Success metrics instrumentation exists for the shipped scope.
