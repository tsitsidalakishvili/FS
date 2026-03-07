# Defect and Rerun Log — run_20260307T130003Z

## D-001 — Security pre-gate failure
- Stage: 5 SecurityPrivacyReviewer (initial)
- Symptom: Pre-implementation gate returned FAIL due token binding, public PII mutation boundary, authZ specificity, retention/DSAR gaps.
- Action: Routed back only to responsible agents (ProductManager, SolutionArchitect, Neo4jDBEngineer) and PrivacyCompliance cross-check.
- Rerun result: Stage 5 rerun PASS after remediation artifacts.

## D-002 — Privacy cross-check fail
- Stage: Auxiliary PrivacyCompliance cross-check (initial)
- Symptom: Missing lawful-basis matrix, PII inventory minimization rationale, governance cadence evidence.
- Action: Added privacy governance addendum.
- Rerun result: PrivacyCompliance cross-check PASS.

## D-003 — Test runner unavailable
- Stage: Post-implementation QA verification
- Symptom: `python3 -m pytest` failed (`No module named pytest`).
- Action: Installed `pytest`.
- Rerun result: Test execution proceeded.

## D-004 — Missing runtime dependencies
- Stage: Post-implementation QA verification
- Symptom: `ModuleNotFoundError: fastapi` and later missing `httpx`.
- Action: Installed `fastapi`, `uvicorn`, `neo4j`, `httpx`.
- Rerun result: Tests executed successfully.

## D-005 — Response validation mismatch
- Stage: Test run
- Symptom: `ResponseValidationError` (extra fields forbidden on output models).
- Action: Split schema base classes into strict input models (`extra=forbid`) and output models (`extra=ignore`).
- Rerun result: All tests passed.

## Final rerun summary
- Final test command: `python3 -m pytest -q crm_backend/tests/test_api_slice.py`
- Final result: `6 passed`
