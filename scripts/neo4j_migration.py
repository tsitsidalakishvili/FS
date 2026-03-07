#!/usr/bin/env python3
"""Neo4j production migration runner.

Usage examples:
  python scripts/neo4j_migration.py --phase preflight
  python scripts/neo4j_migration.py --phase schema
  python scripts/neo4j_migration.py --phase migrate --migration-id 2026-03-07-cutover-01
  python scripts/neo4j_migration.py --phase validate --migration-id 2026-03-07-cutover-01
  python scripts/neo4j_migration.py --phase rollback --migration-id 2026-03-07-cutover-01 --confirm-rollback
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from neo4j import GraphDatabase


@dataclass(frozen=True)
class Neo4jConfig:
    uri: str
    user: str
    password: str
    database: str


ROOT_DIR = Path(__file__).resolve().parents[1]
CYPHER_DIR = ROOT_DIR / "neo4j" / "cypher"

PHASE_FILES = {
    "preflight": ["000_preflight_checks.cypher"],
    "schema": ["001_constraints_indexes.cypher"],
    "migrate": ["002_migrate_streamlit_legacy.cypher"],
    "seed": ["003_seed_reference_data.cypher"],
    "validate": ["005_post_migration_validation.cypher"],
    "rollback": ["006_rollback_migration_batch.cypher"],
    "all": [
        "000_preflight_checks.cypher",
        "001_constraints_indexes.cypher",
        "002_migrate_streamlit_legacy.cypher",
        "003_seed_reference_data.cypher",
        "005_post_migration_validation.cypher",
    ],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Neo4j production migration phases.")
    parser.add_argument(
        "--phase",
        choices=sorted(PHASE_FILES.keys()),
        default="all",
        help="Migration phase to run.",
    )
    parser.add_argument(
        "--migration-id",
        default=_default_migration_id(),
        help="Migration batch id used for migration/validation/rollback phases.",
    )
    parser.add_argument(
        "--fail-on-warnings",
        action="store_true",
        help="Treat warning-level validation results as failures.",
    )
    parser.add_argument(
        "--confirm-rollback",
        action="store_true",
        help="Required safety flag to run rollback phase.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print statements without executing.",
    )
    return parser.parse_args()


def _default_migration_id() -> str:
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"prod-migration-{now}"


def load_config() -> Neo4jConfig:
    uri = os.getenv("NEO4J_URI", "").strip()
    user = os.getenv("NEO4J_USER", "neo4j").strip()
    password = os.getenv("NEO4J_PASSWORD", "").strip()
    database = os.getenv("NEO4J_DATABASE", "neo4j").strip()
    if not uri or not user or not password:
        raise ValueError("Missing NEO4J_URI / NEO4J_USER / NEO4J_PASSWORD environment variables.")
    return Neo4jConfig(uri=uri, user=user, password=password, database=database)


def read_statements(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    return split_cypher_statements(text)


def split_cypher_statements(text: str) -> list[str]:
    statements: list[str] = []
    buf: list[str] = []
    in_single = False
    in_double = False
    in_backtick = False
    prev = ""

    for ch in text:
        if ch == "'" and not in_double and not in_backtick and prev != "\\":
            in_single = not in_single
        elif ch == '"' and not in_single and not in_backtick and prev != "\\":
            in_double = not in_double
        elif ch == "`" and not in_single and not in_double:
            in_backtick = not in_backtick

        if ch == ";" and not in_single and not in_double and not in_backtick:
            statement = _clean_statement("".join(buf))
            if statement:
                statements.append(statement)
            buf = []
        else:
            buf.append(ch)
        prev = ch

    tail = _clean_statement("".join(buf))
    if tail:
        statements.append(tail)
    return statements


def _clean_statement(statement: str) -> str:
    cleaned_lines = []
    for line in statement.splitlines():
        stripped = line.strip()
        if stripped.startswith("//"):
            continue
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines).strip()


def print_rows(rows: Iterable[dict[str, Any]]) -> None:
    rows = list(rows)
    if not rows:
        print("  (no rows)")
        return
    for row in rows:
        print(f"  {row}")


def evaluate_rows(rows: Iterable[dict[str, Any]], *, fail_on_warnings: bool) -> list[str]:
    failures: list[str] = []
    for row in rows:
        if "duplicate_count" in row and int(row["duplicate_count"] or 0) > 0:
            failures.append(str(row))
            continue
        if "violation_count" in row and int(row["violation_count"] or 0) > 0:
            severity = str(row.get("severity", "error")).lower()
            if severity == "error" or fail_on_warnings:
                failures.append(str(row))
    return failures


def run_phase(
    *,
    phase: str,
    config: Neo4jConfig,
    migration_id: str,
    dry_run: bool,
    fail_on_warnings: bool,
) -> None:
    files = PHASE_FILES[phase]
    is_read_phase = phase in {"preflight", "validate"}
    params = {"migrationId": migration_id}
    failures: list[str] = []

    driver = GraphDatabase.driver(config.uri, auth=(config.user, config.password))
    try:
        with driver.session(database=config.database) as session:
            for filename in files:
                path = CYPHER_DIR / filename
                if not path.exists():
                    raise FileNotFoundError(f"Cypher file not found: {path}")

                statements = read_statements(path)
                print(f"\n==> {filename} ({len(statements)} statements)")
                for idx, statement in enumerate(statements, start=1):
                    preview = " ".join(statement.split())[:140]
                    print(f"[{idx:02d}] {preview}")
                    if dry_run:
                        continue

                    if is_read_phase:
                        rows = session.execute_read(lambda tx: [r.data() for r in tx.run(statement, params)])
                    else:
                        rows = session.execute_write(lambda tx: [r.data() for r in tx.run(statement, params)])
                    print_rows(rows)
                    failures.extend(evaluate_rows(rows, fail_on_warnings=fail_on_warnings))

    finally:
        driver.close()

    if failures:
        print("\nMigration checks failed:")
        for item in failures:
            print(f"- {item}")
        raise SystemExit(2)


def main() -> None:
    args = parse_args()

    if args.phase == "rollback" and not args.confirm_rollback:
        raise SystemExit("Rollback requires --confirm-rollback")

    config = load_config()
    print(
        f"Connecting to {config.uri} (db={config.database}) | phase={args.phase} "
        f"| migrationId={args.migration_id} | dry_run={args.dry_run}"
    )

    run_phase(
        phase=args.phase,
        config=config,
        migration_id=args.migration_id,
        dry_run=args.dry_run,
        fail_on_warnings=args.fail_on_warnings,
    )

    print("\nDone.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
