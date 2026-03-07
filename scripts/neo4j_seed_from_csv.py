#!/usr/bin/env python3
"""Seed CRM graph data from CSV into Neo4j.

Example:
  python scripts/neo4j_seed_from_csv.py \
    --csv data/tbilisi_supporters_members.csv \
    --migration-id 2026-03-07-seed-01
"""

from __future__ import annotations

import argparse
import csv
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from neo4j import GraphDatabase


@dataclass(frozen=True)
class Neo4jConfig:
    uri: str
    user: str
    password: str
    database: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed Neo4j CRM data from CSV.")
    parser.add_argument("--csv", required=True, help="Path to CSV file.")
    parser.add_argument("--chunk-size", type=int, default=500, help="Rows per transaction.")
    parser.add_argument(
        "--default-supporter-type",
        default="Supporter",
        help="Fallback supporter type when CSV value is missing.",
    )
    parser.add_argument(
        "--migration-id",
        default=_default_migration_id(),
        help="Migration batch id recorded on created entities.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Parse and preview only.")
    return parser.parse_args()


def _default_migration_id() -> str:
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"seed-{now}"


def load_config() -> Neo4jConfig:
    uri = os.getenv("NEO4J_URI", "").strip()
    user = os.getenv("NEO4J_USER", "neo4j").strip()
    password = os.getenv("NEO4J_PASSWORD", "").strip()
    database = os.getenv("NEO4J_DATABASE", "neo4j").strip()
    if not uri or not user or not password:
        raise ValueError("Missing NEO4J_URI / NEO4J_USER / NEO4J_PASSWORD environment variables.")
    return Neo4jConfig(uri=uri, user=user, password=password, database=database)


def clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


def split_list(value: Any) -> list[str]:
    text = clean_text(value)
    if not text:
        return []
    return [item.strip() for item in text.split(",") if item.strip()]


def normalize_header(name: str) -> str:
    return (
        str(name)
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
        .replace(".", "")
    )


def pick_column(header_map: dict[str, str], candidates: list[str]) -> str | None:
    for candidate in candidates:
        key = normalize_header(candidate)
        if key in header_map:
            return header_map[key]
    return None


def as_int(value: Any) -> int | None:
    text = clean_text(value)
    if not text:
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def as_float(value: Any) -> float | None:
    text = clean_text(value)
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def normalize_supporter_type(value: Any, default_value: str) -> str:
    text = clean_text(value)
    if not text:
        return default_value
    return "Member" if "member" in text.lower() else "Supporter"


def parse_rows(csv_path: Path, default_supporter_type: str) -> list[dict[str, Any]]:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None:
            return []

        header_map = {normalize_header(name): name for name in reader.fieldnames}
        col_email = pick_column(header_map, ["email", "primary_email", "email_address"])
        col_email_secondary = pick_column(header_map, ["secondary_email", "alternate_email", "alt_email"])
        if not col_email:
            raise ValueError("CSV must include an email column.")

        col_first = pick_column(header_map, ["first_name", "firstname", "first"])
        col_last = pick_column(header_map, ["last_name", "lastname", "last"])
        col_gender = pick_column(header_map, ["gender", "sex"])
        col_age = pick_column(header_map, ["age"])
        col_phone = pick_column(header_map, ["phone", "primary_phone", "mobile"])
        col_address = pick_column(header_map, ["address", "fulladdress", "full_address"])
        col_lat = pick_column(header_map, ["lat", "latitude"])
        col_lon = pick_column(header_map, ["lon", "lng", "longitude"])
        col_type = pick_column(header_map, ["supporter_type", "type", "group"])
        col_effort = pick_column(header_map, ["effort_hours", "volunteer_hours", "hours"])
        col_events = pick_column(header_map, ["events_attended", "events_attended_count"])
        col_refs = pick_column(header_map, ["referral_count", "references", "referrals"])
        col_education = pick_column(header_map, ["education", "education_level"])
        col_skills = pick_column(header_map, ["skills", "skill_list", "skill"])
        col_tags = pick_column(header_map, ["tags", "tag_list"])
        col_involvement = pick_column(header_map, ["involvement_areas", "involvement_area", "areas"])

        rows: list[dict[str, Any]] = []
        for raw in reader:
            email = clean_text(raw.get(col_email))
            if not email and col_email_secondary:
                email = clean_text(raw.get(col_email_secondary))
            if not email:
                continue

            rows.append(
                {
                    "email": email,
                    "firstName": clean_text(raw.get(col_first)) if col_first else None,
                    "lastName": clean_text(raw.get(col_last)) if col_last else None,
                    "gender": clean_text(raw.get(col_gender)) if col_gender else None,
                    "age": as_int(raw.get(col_age)) if col_age else None,
                    "phone": clean_text(raw.get(col_phone)) if col_phone else None,
                    "address": clean_text(raw.get(col_address)) if col_address else None,
                    "lat": as_float(raw.get(col_lat)) if col_lat else None,
                    "lon": as_float(raw.get(col_lon)) if col_lon else None,
                    "supporterType": normalize_supporter_type(
                        raw.get(col_type) if col_type else None,
                        default_supporter_type,
                    ),
                    "effortHours": as_float(raw.get(col_effort)) if col_effort else None,
                    "eventsAttendedCount": as_int(raw.get(col_events)) if col_events else None,
                    "referralCount": as_int(raw.get(col_refs)) if col_refs else None,
                    "education": clean_text(raw.get(col_education)) if col_education else None,
                    "skills": split_list(raw.get(col_skills)) if col_skills else [],
                    "tags": split_list(raw.get(col_tags)) if col_tags else [],
                    "involvementAreas": split_list(raw.get(col_involvement)) if col_involvement else [],
                }
            )
    return rows


SEED_QUERY = """
UNWIND $rows AS row
WITH row
WHERE row.email IS NOT NULL AND trim(row.email) <> ""
MERGE (p:Person {email: row.email})
ON CREATE SET p.personId = randomUUID(), p.createdAt = datetime()
SET p.firstName = coalesce(row.firstName, p.firstName),
    p.lastName = coalesce(row.lastName, p.lastName),
    p.gender = coalesce(row.gender, p.gender),
    p.age = coalesce(row.age, p.age),
    p.phone = coalesce(row.phone, p.phone),
    p.effortHours = coalesce(row.effortHours, p.effortHours),
    p.eventsAttendedCount = coalesce(row.eventsAttendedCount, p.eventsAttendedCount),
    p.referralCount = coalesce(row.referralCount, p.referralCount),
    p.updatedAt = datetime()
WITH p, row
MERGE (st:SupporterType {name: coalesce(row.supporterType, "Supporter")})
ON CREATE SET st.createdAt = datetime()
SET st.updatedAt = datetime()
MERGE (p)-[rType:CLASSIFIED_AS]->(st)
ON CREATE SET rType.createdAt = datetime(), rType.migrationBatchId = $migrationId
SET rType.updatedAt = datetime()
WITH p, row
FOREACH (_ IN CASE WHEN row.address IS NULL OR row.address = "" THEN [] ELSE [1] END |
  MERGE (a:Address {fullAddress: row.address})
  ON CREATE SET a.createdAt = datetime(), a.migrationBatchId = $migrationId
  SET a.latitude = coalesce(row.lat, a.latitude),
      a.longitude = coalesce(row.lon, a.longitude),
      a.updatedAt = datetime()
  FOREACH (__ IN CASE WHEN a.latitude IS NULL OR a.longitude IS NULL THEN [] ELSE [1] END |
    SET a.location = point({latitude: toFloat(a.latitude), longitude: toFloat(a.longitude)})
  )
  MERGE (p)-[rAddr:LIVES_AT]->(a)
  ON CREATE SET rAddr.createdAt = datetime(), rAddr.migrationBatchId = $migrationId
  SET rAddr.updatedAt = datetime()
)
WITH p, row
FOREACH (educationName IN CASE WHEN row.education IS NULL OR row.education = "" THEN [] ELSE [row.education] END |
  MERGE (ed:EducationLevel {name: educationName})
  ON CREATE SET ed.createdAt = datetime()
  MERGE (p)-[rEd:HAS_EDUCATION]->(ed)
  ON CREATE SET rEd.createdAt = datetime(), rEd.migrationBatchId = $migrationId
  SET rEd.updatedAt = datetime()
)
FOREACH (skillName IN coalesce(row.skills, []) |
  MERGE (sk:Skill {name: skillName})
  ON CREATE SET sk.createdAt = datetime()
  MERGE (p)-[rSkill:CAN_CONTRIBUTE_WITH]->(sk)
  ON CREATE SET rSkill.createdAt = datetime(), rSkill.migrationBatchId = $migrationId
  SET rSkill.updatedAt = datetime()
)
FOREACH (tagName IN coalesce(row.tags, []) |
  MERGE (t:Tag {name: tagName})
  ON CREATE SET t.createdAt = datetime()
  MERGE (p)-[rTag:HAS_TAG]->(t)
  ON CREATE SET rTag.createdAt = datetime(), rTag.migrationBatchId = $migrationId
  SET rTag.updatedAt = datetime()
)
FOREACH (areaName IN coalesce(row.involvementAreas, []) |
  MERGE (ia:InvolvementArea {name: areaName})
  ON CREATE SET ia.createdAt = datetime()
  MERGE (p)-[rArea:INTERESTED_IN]->(ia)
  ON CREATE SET rArea.createdAt = datetime(), rArea.migrationBatchId = $migrationId
  SET rArea.updatedAt = datetime()
)
RETURN count(p) AS processed;
"""


def chunks(items: list[dict[str, Any]], size: int) -> list[list[dict[str, Any]]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def run_seed(
    config: Neo4jConfig,
    rows: list[dict[str, Any]],
    chunk_size: int,
    migration_id: str,
    dry_run: bool,
) -> None:
    if not rows:
        print("No valid rows to seed.")
        return

    print(f"Rows parsed: {len(rows)}")
    if dry_run:
        preview = rows[:3]
        print("Dry run enabled. Preview:")
        for row in preview:
            print(row)
        return

    driver = GraphDatabase.driver(config.uri, auth=(config.user, config.password))
    try:
        with driver.session(database=config.database) as session:
            session.execute_write(
                lambda tx: tx.run(
                    """
                    MERGE (m:MigrationBatch {migrationId: $migrationId})
                    ON CREATE SET m.startedAt = datetime(), m.status = "running"
                    SET m.notes = "CSV seed import"
                    """,
                    {"migrationId": migration_id},
                ).consume()
            )

            total = 0
            for idx, chunk in enumerate(chunks(rows, chunk_size), start=1):
                session.execute_write(
                    lambda tx: tx.run(
                        SEED_QUERY,
                        {"rows": chunk, "migrationId": migration_id},
                    ).consume()
                )
                total += len(chunk)
                print(f"Committed chunk {idx}: +{len(chunk)} rows (total={total})")

            session.execute_write(
                lambda tx: tx.run(
                    """
                    MATCH (m:MigrationBatch {migrationId: $migrationId})
                    SET m.status = "completed", m.completedAt = datetime()
                    """,
                    {"migrationId": migration_id},
                ).consume()
            )
            print(f"Seed completed. Total rows committed: {total}")
    finally:
        driver.close()


def main() -> None:
    args = parse_args()
    csv_path = Path(args.csv)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
    if args.chunk_size <= 0:
        raise ValueError("--chunk-size must be > 0")

    rows = parse_rows(csv_path, args.default_supporter_type)
    config = load_config()
    run_seed(
        config=config,
        rows=rows,
        chunk_size=args.chunk_size,
        migration_id=args.migration_id,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
