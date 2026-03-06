# Neo4j Migrations Runbook

## Files

- `001_core_schema.cypher`  
  Unified normalization + duplicate audit + constraints/indexes for CRM and Deliberation.

## Recommended execution order

1. Backup database.
2. Run the migration in a staging database.
3. Inspect duplicate audit result rows from section 2 of the script.
4. Resolve duplicates (especially `Person.emailNormalized`) if any are returned.
5. Re-run `001_core_schema.cypher` until all constraints/indexes apply successfully.
6. Promote to production using the same script and sequence.

## Example command

```bash
cypher-shell \
  -a "$NEO4J_URI" \
  -u "$NEO4J_USER" \
  -p "$NEO4J_PASSWORD" \
  -d "${NEO4J_DATABASE:-neo4j}" \
  -f neo4j/migrations/001_core_schema.cypher
```

## Validation checks

```cypher
SHOW CONSTRAINTS;
SHOW INDEXES;

MATCH (p:Person)
WHERE p.emailNormalized IS NOT NULL
WITH p.emailNormalized AS key, count(*) AS c
WHERE c > 1
RETURN key, c
ORDER BY c DESC;
```
