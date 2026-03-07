# Bounded Delivery Plan — Streamlit to Production Rewrite (Neo4j)

## Scope for this run (implemented)
- New backend slice in `crm_backend/`:
  - Health + People + Tasks + Events + DeepLink + Public Registration
  - Token-bound public registration
  - Deny-by-default internal route authorization
  - Focused regression tests

## Out of scope for this run
- Full frontend rewrite
- Deliberation rewrite
- Outreach/segments and analytics parity
- Full DSAR job executor implementation

## Ordered stage execution commitment
1. StreamlitFlowMapper
2. ProductManager
3. SolutionArchitect
4. Neo4jDBEngineer
5. SecurityPrivacyReviewer
6. BackendEngineer
7. FrontendEngineer
8. PlatformDevOpsEngineer
9. QAReleaseReviewer
10. Supervisor final decision

## Gate policy for this run
- Implementation blocked until pre-gates passed:
  - ProductManager PASS
  - SolutionArchitect PASS
  - Neo4jDBEngineer PASS
  - SecurityPrivacyReviewer PASS (after rerun)
- Post-implementation completion requires QAReleaseReviewer PASS.
