import os
import json
from uuid import uuid4

import altair as alt
import pandas as pd
import pydeck as pdk
import requests
import streamlit as st

from crm.clients.deliberation import (
    delib_api_get,
    delib_api_patch,
    delib_api_post,
    render_delib_api_unavailable,
)
from crm.config import (
    PUBLIC_ONLY,
    SUPPORTER_ACCESS_CODE,
    NEO4J_SANDBOX_DATABASE,
    NEO4J_SANDBOX_PASSWORD,
    NEO4J_SANDBOX_URI,
    NEO4J_SANDBOX_USER,
)
from crm.db.neo4j import init_driver, run_query, run_write
import crm.db.neo4j as neo4j_db
from crm.services.feedback import render_feedback_widget
from crm.ui.components.import_export import (
    render_import_export_section as render_import_export_section_ui,
)
from crm.ui.pages.admin import render_admin_page
from crm.ui.pages.dashboard import render_dashboard_page
from crm.ui.pages.deliberation import render_deliberation as render_deliberation_page
from crm.ui.pages.events import render_events_page
from crm.ui.pages.map import render_map_page
from crm.ui.pages.outreach import render_outreach_page
from crm.ui.pages.profiles import render_profiles_tab as render_profiles_tab_page
from crm.ui.pages.segments import render_segments_tab as render_segments_tab_page
from crm.ui.pages.tasks import render_tasks_tab as render_tasks_tab_page
from crm.ui.pages.volunteers import render_volunteers_page
from crm.ui.pages.data import render_data_page
from crm.ui.pages.slides import render_slides_page

try:
    import matplotlib.pyplot as plt
    from matplotlib_venn import venn2, venn3
except Exception:
    plt = None
    venn2 = None
    venn3 = None

st.set_page_config(page_title="Freedom Square CRM (Short)", layout="wide")

st.markdown(
    """
<style>
/* Make Streamlit tooltip icons more visible */
[data-testid="stTooltipIcon"] {
  opacity: 1 !important;
  color: #6b7280 !important;
}
[data-testid="stTooltipIcon"] svg {
  width: 18px !important;
  height: 18px !important;
}
</style>
""",
    unsafe_allow_html=True,
)



def upsert_person(payload):
    query = """
    MERGE (p:Person {email: $email})
    ON CREATE SET p.personId = randomUUID(), p.createdAt = datetime()
    SET p.firstName = $firstName,
        p.lastName = $lastName,
        p.gender = $gender,
        p.age = $age,
        p.phone = $phone,
        p.lat = $lat,
        p.lon = $lon,
        p.effortHours = coalesce($effortHours, p.effortHours),
        p.eventsAttendedCount = coalesce($eventsAttendedCount, p.eventsAttendedCount),
        p.referralCount = coalesce($referralCount, p.referralCount)
    WITH p
    MERGE (st:SupporterType {name: $supporterType})
    MERGE (p)-[:CLASSIFIED_AS]->(st)
    WITH p
    FOREACH (_ IN CASE WHEN $address IS NULL OR $address = '' THEN [] ELSE [1] END |
        MERGE (a:Address {fullAddress: $address})
        ON CREATE SET a.latitude = $lat, a.longitude = $lon
        ON MATCH SET a.latitude = coalesce($lat, a.latitude),
                    a.longitude = coalesce($lon, a.longitude)
        MERGE (p)-[:LIVES_AT]->(a)
    )
    """
    return run_write(query, payload)


TASK_STATUSES = ["Open", "In Progress", "Done", "Cancelled"]


def create_task(person_email, title, description=None, due_date=None, status="Open"):
    person_email = clean_text(person_email)
    title = clean_text(title)
    if not person_email or not title:
        return False
    due_date = clean_text(due_date)
    status = status if status in TASK_STATUSES else "Open"
    return run_write(
        """
        MATCH (p:Person {email: $email})
        CREATE (t:Task {
          taskId: randomUUID(),
          title: $title,
          description: $description,
          status: $status,
          dueDate: $dueDate,
          createdAt: datetime(),
          updatedAt: datetime()
        })
        MERGE (p)-[:HAS_TASK]->(t)
        """,
        {
            "email": person_email,
            "title": title,
            "description": clean_text(description),
            "status": status,
            "dueDate": due_date,
        },
    )


def update_task_status(task_id, status):
    task_id = clean_text(task_id)
    status = status if status in TASK_STATUSES else None
    if not task_id or not status:
        return False
    return run_write(
        """
        MATCH (t:Task {taskId: $taskId})
        SET t.status = $status,
            t.updatedAt = datetime()
        """,
        {"taskId": task_id, "status": status},
    )


def list_tasks(status=None, person_email=None, group=None, limit=300):
    status = clean_text(status)
    person_email = clean_text(person_email)
    group = clean_text(group)
    group = group if group in {"Supporter", "Member"} else None
    try:
        limit = int(limit)
    except Exception:
        limit = 300
    limit = max(10, min(1000, limit))

    query = """
    MATCH (p:Person)-[:HAS_TASK]->(t:Task)
    OPTIONAL MATCH (p)-[:CLASSIFIED_AS]->(st:SupporterType)
    WITH p, t, collect(DISTINCT st.name) AS types
    WITH p, t,
      CASE WHEN any(x IN types WHERE toLower(x) CONTAINS 'member') THEN 'Member' ELSE 'Supporter' END AS group
    WHERE ($status IS NULL OR t.status = $status)
      AND ($email IS NULL OR p.email = $email)
      AND ($group IS NULL OR group = $group)
    RETURN
      t.taskId AS taskId,
      t.title AS title,
      coalesce(t.description, '') AS description,
      coalesce(t.status, 'Open') AS status,
      coalesce(t.dueDate, '') AS dueDate,
      coalesce(p.firstName, '') AS firstName,
      coalesce(p.lastName, '') AS lastName,
      p.email AS email,
      group AS group,
      toString(t.createdAt) AS createdAt,
      toString(t.updatedAt) AS updatedAt
    ORDER BY
      CASE WHEN t.status = 'Done' THEN 1 WHEN t.status = 'Cancelled' THEN 2 ELSE 0 END,
      coalesce(t.dueDate, '9999-12-31') ASC,
      t.createdAt DESC
    LIMIT $limit
    """
    return run_query(
        query,
        {"status": status, "email": person_email, "group": group, "limit": limit},
        silent=True,
    )


def search_people(query, limit=50):
    query = clean_text(query)
    try:
        limit = int(limit)
    except Exception:
        limit = 50
    limit = max(5, min(200, limit))
    if not query:
        return pd.DataFrame()
    return run_query(
        """
        MATCH (p:Person)
        OPTIONAL MATCH (p)-[:CLASSIFIED_AS]->(st:SupporterType)
        WITH p, collect(DISTINCT st.name) AS types
        WITH p,
          (trim(coalesce(p.firstName,'') + ' ' + coalesce(p.lastName,''))) AS fullName,
          CASE WHEN any(x IN types WHERE toLower(x) CONTAINS 'member') THEN 'Member' ELSE 'Supporter' END AS group
        WHERE toLower(p.email) CONTAINS toLower($q)
           OR toLower(fullName) CONTAINS toLower($q)
        RETURN
          CASE WHEN fullName = '' THEN p.email ELSE fullName END AS fullName,
          p.email AS email,
          group AS group,
          coalesce(p.timeAvailability, 'Unspecified') AS timeAvailability
        ORDER BY fullName
        LIMIT $limit
        """,
        {"q": query, "limit": limit},
        silent=True,
    )


def load_person_profile(email):
    email = clean_text(email)
    if not email:
        return pd.DataFrame()
    return run_query(
        """
        MATCH (p:Person {email: $email})
        OPTIONAL MATCH (p)-[:CLASSIFIED_AS]->(st:SupporterType)
        OPTIONAL MATCH (p)-[:HAS_TAG]->(tag:Tag)
        OPTIONAL MATCH (p)-[:CAN_CONTRIBUTE_WITH]->(sk:Skill)
        OPTIONAL MATCH (p)-[:INTERESTED_IN]->(ia:InvolvementArea)
        WITH p,
          collect(DISTINCT st.name) AS supporterTypes,
          collect(DISTINCT tag.name) AS tags,
          collect(DISTINCT sk.name) AS skills,
          collect(DISTINCT ia.name) AS involvementAreas
        RETURN
          p.email AS email,
          p.firstName AS firstName,
          p.lastName AS lastName,
          p.phone AS phone,
          p.gender AS gender,
          p.age AS age,
          coalesce(p.timeAvailability, 'Unspecified') AS timeAvailability,
          coalesce(p.about, '') AS about,
          coalesce(p.agreesWithManifesto, false) AS agreesWithManifesto,
          coalesce(p.interestedInMembership, false) AS interestedInMembership,
          coalesce(p.facebookGroupMember, false) AS facebookGroupMember,
          supporterTypes,
          tags,
          skills,
          involvementAreas
        """,
        {"email": email},
        silent=True,
    )


def update_person_profile(email, payload):
    email = clean_text(email)
    if not email:
        return False
    # Only updates core fields; tags/skills/involvement are left as-is for now.
    return run_write(
        """
        MATCH (p:Person {email: $email})
        SET p.firstName = $firstName,
            p.lastName = $lastName,
            p.phone = $phone,
            p.gender = $gender,
            p.age = $age,
            p.timeAvailability = $timeAvailability,
            p.about = $about,
            p.agreesWithManifesto = $agreesWithManifesto,
            p.interestedInMembership = $interestedInMembership,
            p.facebookGroupMember = $facebookGroupMember
        """,
        {
            "email": email,
            "firstName": clean_text(payload.get("firstName")),
            "lastName": clean_text(payload.get("lastName")),
            "phone": clean_text(payload.get("phone")),
            "gender": clean_text(payload.get("gender")),
            "age": payload.get("age"),
            "timeAvailability": clean_text(payload.get("timeAvailability")),
            "about": clean_text(payload.get("about")),
            "agreesWithManifesto": bool(payload.get("agreesWithManifesto", False)),
            "interestedInMembership": bool(payload.get("interestedInMembership", False)),
            "facebookGroupMember": bool(payload.get("facebookGroupMember", False)),
        },
    )


def upsert_segment(name, description, filter_spec):
    name = clean_text(name)
    if not name:
        return False
    description = clean_text(description) or ""
    filter_json = json.dumps(filter_spec or {}, ensure_ascii=False)
    return run_write(
        """
        MERGE (s:Segment {name: $name})
        ON CREATE SET s.segmentId = randomUUID(), s.createdAt = datetime()
        SET s.description = $description,
            s.filterJson = $filterJson,
            s.updatedAt = datetime()
        """,
        {"name": name, "description": description, "filterJson": filter_json},
    )


def list_segments():
    return run_query(
        """
        MATCH (s:Segment)
        RETURN
          s.segmentId AS segmentId,
          s.name AS name,
          coalesce(s.description,'') AS description,
          toString(s.updatedAt) AS updatedAt
        ORDER BY s.updatedAt DESC
        """,
        silent=True,
    )


def delete_segment(segment_id):
    segment_id = clean_text(segment_id)
    if not segment_id:
        return False
    return run_write(
        """
        MATCH (s:Segment {segmentId: $id})
        DETACH DELETE s
        """,
        {"id": segment_id},
    )


def load_segment_filter(segment_id):
    segment_id = clean_text(segment_id)
    if not segment_id:
        return {}
    df = run_query(
        """
        MATCH (s:Segment {segmentId: $id})
        RETURN coalesce(s.filterJson, '{}') AS filterJson
        """,
        {"id": segment_id},
        silent=True,
    )
    if df.empty or "filterJson" not in df.columns:
        return {}
    try:
        return json.loads(df["filterJson"].iloc[0] or "{}")
    except Exception:
        return {}


def run_segment(filter_spec, limit=500):
    filter_spec = filter_spec or {}
    clauses = []
    params = {"limit": max(10, min(2000, int(limit) if str(limit).isdigit() else 500))}

    group = clean_text(filter_spec.get("group"))
    if group in {"Supporter", "Member"}:
        clauses.append("group = $group")
        params["group"] = group

    time_availability = filter_spec.get("timeAvailability") or []
    if isinstance(time_availability, list) and time_availability:
        vals = [str(x) for x in time_availability if str(x).strip()]
        if vals:
            clauses.append("p.timeAvailability IN $timeAvailability")
            params["timeAvailability"] = vals

    tags = filter_spec.get("tags") or []
    if isinstance(tags, list) and tags:
        vals = [str(x) for x in tags if str(x).strip()]
        if vals:
            clauses.append("any(t IN $tags WHERE t IN tags)")
            params["tags"] = vals

    skills = filter_spec.get("skills") or []
    if isinstance(skills, list) and skills:
        vals = [str(x) for x in skills if str(x).strip()]
        if vals:
            clauses.append("any(s IN $skills WHERE s IN skills)")
            params["skills"] = vals

    name_contains = clean_text(filter_spec.get("nameContains"))
    if name_contains:
        clauses.append("toLower(fullName) CONTAINS toLower($nameContains)")
        params["nameContains"] = name_contains

    address_contains = clean_text(filter_spec.get("addressContains"))
    if address_contains:
        clauses.append("toLower(address) CONTAINS toLower($addressContains)")
        params["addressContains"] = address_contains

    min_effort = filter_spec.get("minEffortHours")
    try:
        min_effort_val = float(min_effort) if min_effort is not None and min_effort != "" else None
    except Exception:
        min_effort_val = None
    if min_effort_val is not None and min_effort_val > 0:
        clauses.append("effortHours >= $minEffortHours")
        params["minEffortHours"] = float(min_effort_val)

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""

    query = f"""
    MATCH (p:Person)
    OPTIONAL MATCH (p)-[:LIVES_AT]->(addr:Address)
    OPTIONAL MATCH (p)-[:CLASSIFIED_AS]->(st:SupporterType)
    WITH p, addr, collect(DISTINCT st.name) AS types
    WITH p, addr,
      (trim(coalesce(p.firstName,'') + ' ' + coalesce(p.lastName,''))) AS fullName,
      CASE WHEN any(x IN types WHERE toLower(x) CONTAINS 'member') THEN 'Member' ELSE 'Supporter' END AS group
    OPTIONAL MATCH (p)-[:HAS_TAG]->(tag:Tag)
    WITH p, addr, fullName, group, collect(DISTINCT tag.name) AS tags
    OPTIONAL MATCH (p)-[:CAN_CONTRIBUTE_WITH]->(sk:Skill)
    WITH p, addr, fullName, group, tags, collect(DISTINCT sk.name) AS skills,
         coalesce(p.effortHours, 0.0) AS effortHours,
         coalesce(p.address, addr.fullAddress, '') AS address
    {where}
    RETURN
      CASE WHEN fullName = '' THEN p.email ELSE fullName END AS fullName,
      p.email AS email,
      group AS group,
      coalesce(p.timeAvailability, 'Unspecified') AS timeAvailability,
      effortHours AS effortHours,
      tags,
      skills
    ORDER BY effortHours DESC
    LIMIT $limit
    """
    return run_query(query, params=params, silent=True)


def clean_text(value):
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


def split_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        items = value
    else:
        items = str(value).split(",")
    cleaned = []
    for item in items:
        text = clean_text(item)
        if text:
            cleaned.append(text)
    return cleaned


def normalize_str_list(values):
    cleaned = []
    for value in values or []:
        text = clean_text(value)
        if text:
            cleaned.append(text)
    return sorted(set(cleaned))


def format_list_label(values, limit=6):
    items = [str(v).strip() for v in values or [] if str(v).strip()]
    items = sorted(set(items))
    if not items:
        return "None"
    if len(items) > limit:
        return ", ".join(items[:limit]) + f" (+{len(items) - limit} more)"
    return ", ".join(items)


def normalize_supporter_type(value, default_type="Supporter"):
    text = clean_text(value)
    if not text:
        return default_type
    if "member" in text.lower():
        return "Member"
    return "Supporter"


def _normalize_column(name):
    return (
        str(name)
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
        .replace(".", "")
    )


def _get_column(df, candidates):
    normalized = {_normalize_column(col): col for col in df.columns}
    for cand in candidates:
        key = _normalize_column(cand)
        if key in normalized:
            return normalized[key]
    return None


def _build_import_rows(df, default_type):
    if df.empty:
        return []
    col_email = _get_column(df, ["email", "primary_email", "e_mail", "e-mail", "email_address"])
    col_email_secondary = _get_column(
        df, ["secondary_email", "alternate_email", "alt_email"]
    )
    if not col_email:
        return []
    col_first = _get_column(df, ["first_name", "firstname", "first"])
    col_last = _get_column(df, ["last_name", "lastname", "last"])
    col_gender = _get_column(df, ["gender", "sex"])
    col_age = _get_column(df, ["age"])
    col_phone = _get_column(df, ["phone", "primary_phone", "mobile"])
    col_phone_secondary = _get_column(df, ["secondary_phone", "alt_phone"])
    col_address = _get_column(df, ["address", "fulladdress", "full_address"])
    col_lat = _get_column(df, ["lat", "latitude"])
    col_lon = _get_column(df, ["lon", "lng", "longitude"])
    col_type = _get_column(df, ["supporter_type", "type", "group"])
    col_effort = _get_column(df, ["effort_hours", "volunteer_hours", "hours", "time_spent"])
    col_events = _get_column(df, ["events_attended", "events_attended_count", "event_attended", "event_attend_count"])
    col_refs = _get_column(df, ["referral_count", "references", "referrals", "recruits"])
    col_education = _get_column(df, ["education", "education_level"])
    col_skills = _get_column(df, ["skills", "skill_list", "skill"])

    rows = []
    for _, row in df.iterrows():
        email = clean_text(row.get(col_email))
        if not email and col_email_secondary:
            email = clean_text(row.get(col_email_secondary))
        if not email:
            continue
        age_val = pd.to_numeric(row.get(col_age), errors="coerce") if col_age else None
        age = int(age_val) if age_val is not None and not pd.isna(age_val) and age_val > 0 else None
        lat_val = pd.to_numeric(row.get(col_lat), errors="coerce") if col_lat else None
        lon_val = pd.to_numeric(row.get(col_lon), errors="coerce") if col_lon else None
        lat = float(lat_val) if lat_val is not None and not pd.isna(lat_val) else None
        lon = float(lon_val) if lon_val is not None and not pd.isna(lon_val) else None
        supporter_type = clean_text(row.get(col_type)) if col_type else None
        effort_val = pd.to_numeric(row.get(col_effort), errors="coerce") if col_effort else None
        effort_hours = float(effort_val) if effort_val is not None and not pd.isna(effort_val) else None
        events_val = pd.to_numeric(row.get(col_events), errors="coerce") if col_events else None
        events_attended = int(events_val) if events_val is not None and not pd.isna(events_val) else None
        refs_val = pd.to_numeric(row.get(col_refs), errors="coerce") if col_refs else None
        referrals = int(refs_val) if refs_val is not None and not pd.isna(refs_val) else None
        education = clean_text(row.get(col_education)) if col_education else None
        skills = split_list(row.get(col_skills)) if col_skills else []
        rows.append(
            {
                "email": email,
                "firstName": clean_text(row.get(col_first)) if col_first else None,
                "lastName": clean_text(row.get(col_last)) if col_last else None,
                "gender": clean_text(row.get(col_gender)) if col_gender else None,
                "age": age,
                "phone": clean_text(row.get(col_phone)) if col_phone else (clean_text(row.get(col_phone_secondary)) if col_phone_secondary else None),
                "address": clean_text(row.get(col_address)) if col_address else None,
                "lat": lat,
                "lon": lon,
                "effortHours": effort_hours,
                "eventsAttendedCount": events_attended,
                "referralCount": referrals,
                "education": education,
                "skills": skills,
                "supporterType": normalize_supporter_type(supporter_type, default_type),
            }
        )
    return rows


def nominatim_search(query, limit=5):
    if not query:
        return []
    try:
        response = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": query, "format": "json", "limit": limit},
            headers={"User-Agent": "freedom-square-crm-short"},
            timeout=10,
        )
        if response.ok:
            return response.json()
    except Exception:
        return []
    return []


def get_distinct_values(label, prop="name"):
    if neo4j_db.driver is None:
        return []
    query = f"""
    MATCH (n:{label})
    WHERE n.{prop} IS NOT NULL
    RETURN DISTINCT n.{prop} AS value
    ORDER BY value
    """
    df = run_query(query, silent=True)
    if df.empty or "value" not in df.columns:
        return []
    return [str(v) for v in df["value"].dropna().tolist() if str(v).strip()]


def bulk_upsert_people(rows):
    if not rows:
        return False
    query = """
    UNWIND $rows AS row
    WITH row
    WHERE row.email IS NOT NULL AND trim(row.email) <> ""
    MERGE (p:Person {email: row.email})
    ON CREATE SET p.personId = randomUUID(), p.createdAt = datetime()
    SET p.firstName = row.firstName,
        p.lastName = row.lastName,
        p.gender = row.gender,
        p.age = row.age,
        p.phone = row.phone,
        p.lat = row.lat,
        p.lon = row.lon,
        p.effortHours = coalesce(row.effortHours, p.effortHours),
        p.eventsAttendedCount = coalesce(row.eventsAttendedCount, p.eventsAttendedCount),
        p.referralCount = coalesce(row.referralCount, p.referralCount)
    WITH p, row
    FOREACH (_ IN CASE WHEN row.education IS NULL OR row.education = '' THEN [] ELSE [1] END |
        MERGE (ed:EducationLevel {name: row.education})
        MERGE (p)-[:HAS_EDUCATION]->(ed)
    )
    FOREACH (skill IN coalesce(row.skills, []) |
        MERGE (sk:Skill {name: skill})
        MERGE (p)-[:CAN_CONTRIBUTE_WITH]->(sk)
    )
    MERGE (st:SupporterType {name: coalesce(row.supporterType, 'Supporter')})
    MERGE (p)-[:CLASSIFIED_AS]->(st)
    WITH p, row
    FOREACH (_ IN CASE WHEN row.address IS NULL OR row.address = '' THEN [] ELSE [1] END |
        MERGE (a:Address {fullAddress: row.address})
        ON CREATE SET a.latitude = row.lat, a.longitude = row.lon
        ON MATCH SET a.latitude = coalesce(row.lat, a.latitude),
                    a.longitude = coalesce(row.lon, a.longitude)
        MERGE (p)-[:LIVES_AT]->(a)
    )
    """
    return run_write(query, {"rows": rows})


def classify_group(types):
    for value in types or []:
        if value and "member" in str(value).lower():
            return "Member"
    return "Supporter"


def _education_score(level):
    if not level:
        return 0.0
    text = str(level).lower()
    if "phd" in text or "doctor" in text:
        return 3.0
    if "master" in text:
        return 2.0
    if "bachelor" in text:
        return 1.0
    if "high" in text:
        return 0.5
    return 0.0


def pick_education(levels):
    best_label = None
    best_score = 0.0
    for level in levels or []:
        score = _education_score(level)
        if score > best_score:
            best_score = score
            best_label = level
    return best_label or "Unspecified", best_score


def calc_rating(effort_score):
    score = max(0.0, float(effort_score or 0))
    if score >= 120:
        return 5
    if score >= 80:
        return 4
    if score >= 40:
        return 3
    if score >= 10:
        return 2
    return 1


def rating_stars(value):
    if value is None or pd.isna(value):
        return "Not rated"
    filled = max(0, min(5, int(value)))
    return "⭐" * filled + "☆" * (5 - filled)


def rating_color(value):
    if value is None or pd.isna(value):
        return [120, 120, 120, 140]
    if value >= 4:
        return [46, 204, 113, 190]
    if value >= 3:
        return [241, 196, 15, 190]
    return [231, 76, 60, 190]


def age_group(value):
    if value is None or pd.isna(value):
        return "Unspecified"
    try:
        age = int(value)
    except (TypeError, ValueError):
        return "Unspecified"
    if age < 18:
        return "Under 18"
    if age < 25:
        return "18-24"
    if age < 35:
        return "25-34"
    if age < 45:
        return "35-44"
    if age < 55:
        return "45-54"
    if age < 65:
        return "55-64"
    return "65+"


def enrich_people_core(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df["types"] = df["types"].apply(lambda v: v or [])
    df["group"] = df["types"].apply(classify_group)
    df["age"] = pd.to_numeric(df["age"], errors="coerce")
    df["ageGroup"] = df["age"].apply(age_group)
    df["activityCount"] = pd.to_numeric(df["activityCount"], errors="coerce").fillna(0).astype(int)
    df["eventJoinCount"] = pd.to_numeric(df["eventJoinCount"], errors="coerce").fillna(0).astype(int)
    df["eventAttendRelCount"] = pd.to_numeric(df["eventAttendRelCount"], errors="coerce").fillna(0).astype(int)
    df["skills"] = df["skills"].apply(lambda v: v or [])
    df["skillCount"] = df["skills"].apply(lambda v: len([x for x in v if x]))
    df["skillsLabel"] = df["skills"].apply(format_list_label)
    df["eventAttendProp"] = pd.to_numeric(df["eventAttendProp"], errors="coerce").fillna(0).astype(int)
    df["referredCount"] = pd.to_numeric(df["referredCount"], errors="coerce").fillna(0).astype(int)
    df["recruitedCount"] = pd.to_numeric(df["recruitedCount"], errors="coerce").fillna(0).astype(int)
    df["referralProp"] = pd.to_numeric(df["referralProp"], errors="coerce").fillna(0).astype(int)
    df["eventAttendCount"] = df["eventAttendRelCount"] + df["eventAttendProp"]
    df["referralCount"] = df["referredCount"] + df["recruitedCount"] + df["referralProp"]
    df["joinCount"] = df["activityCount"] + df["eventJoinCount"]
    df["effortHours"] = pd.to_numeric(df["effortHours"], errors="coerce").fillna(0.0)
    df["donationTotal"] = pd.to_numeric(df["donationTotal"], errors="coerce").fillna(0.0)
    education_values = df["educationLevels"].apply(pick_education)
    df["educationLevel"] = education_values.apply(lambda value: value[0])
    df["educationScore"] = education_values.apply(lambda value: value[1])
    df["effortScore"] = df["effortHours"] + df["eventAttendCount"] + df["referralCount"]
    df["hasParticipation"] = (
        df["activityCount"] + df["eventJoinCount"] + df["eventAttendCount"]
    ) > 0
    df["rating"] = df["effortScore"].apply(calc_rating)
    df.loc[~df["hasParticipation"], "rating"] = pd.NA
    df["ratingStars"] = df["rating"].apply(rating_stars)
    full_name = (df["firstName"].fillna("") + " " + df["lastName"].fillna("")).str.strip()
    df["fullName"] = full_name.mask(full_name == "", df["email"])
    df["age"] = pd.to_numeric(df["age"], errors="coerce")
    return df


@st.cache_data(ttl=60)
def load_supporter_summary():
    df = run_query(
        """
        MATCH (p:Person)
        OPTIONAL MATCH (p)-[:IS_SUPPORTER]->(s:Supporter)
        OPTIONAL MATCH (p)-[:CLASSIFIED_AS]->(st:SupporterType)
        OPTIONAL MATCH (p)-[:HAS_ACTIVITY]->(a:Activity)
        OPTIONAL MATCH (p)-[r:REGISTERED_FOR]->(:Event)
        OPTIONAL MATCH (p)-[:CAN_CONTRIBUTE_WITH]->(sk:Skill)
        OPTIONAL MATCH (p)-[:HAS_EDUCATION]->(ed:EducationLevel)
        OPTIONAL MATCH (p)<-[:REFERRED_BY]-(refP:Person)
        OPTIONAL MATCH (s)-[:RECRUITED]->(sr:Supporter)
        WITH p, s,
             collect(DISTINCT st.name) AS types,
             collect(DISTINCT ed.name) AS educationLevels,
             count(DISTINCT a) AS activityCount,
             count(DISTINCT r) AS eventJoinCount,
             count(DISTINCT CASE WHEN r.status = 'Attended' THEN r ELSE NULL END) AS eventAttendRelCount,
             collect(DISTINCT sk.name) AS skills,
             count(DISTINCT refP) AS referredCount,
             count(DISTINCT sr) AS recruitedCount
        RETURN
          p.email AS email,
          p.firstName AS firstName,
          p.lastName AS lastName,
          coalesce(p.gender, 'Unspecified') AS gender,
          p.age AS age,
          types,
          activityCount,
          eventJoinCount,
          eventAttendRelCount,
          skills,
          educationLevels,
          coalesce(p.eventsAttendedCount, 0) AS eventAttendProp,
          coalesce(p.referralCount, 0) AS referralProp,
          referredCount,
          recruitedCount,
          coalesce(p.effortHours, p.volunteerHours, s.volunteer_hours, s.volunteerHours, 0) AS effortHours,
          coalesce(p.donationTotal, 0) AS donationTotal
        """,
        silent=True,
    )
    if df.empty:
        return df
    return enrich_people_core(df)


@st.cache_data(ttl=60)
def load_map_data():
    df = run_query(
        """
        MATCH (p:Person)
        OPTIONAL MATCH (p)-[:LIVES_AT]->(a:Address)
        WITH p,
             coalesce(p.lat, a.latitude) AS lat,
             coalesce(p.lon, a.longitude) AS lon,
             coalesce(p.address, a.fullAddress) AS address
        WHERE lat IS NOT NULL AND lon IS NOT NULL
        OPTIONAL MATCH (p)-[:IS_SUPPORTER]->(s:Supporter)
        OPTIONAL MATCH (p)-[:CLASSIFIED_AS]->(st:SupporterType)
        OPTIONAL MATCH (p)-[:HAS_ACTIVITY]->(a:Activity)
        OPTIONAL MATCH (p)-[r:REGISTERED_FOR]->(:Event)
        OPTIONAL MATCH (p)-[:CAN_CONTRIBUTE_WITH]->(sk:Skill)
        OPTIONAL MATCH (p)-[:HAS_EDUCATION]->(ed:EducationLevel)
        OPTIONAL MATCH (p)-[:INTERESTED_IN]->(ia:InvolvementArea)
        OPTIONAL MATCH (p)<-[:REFERRED_BY]-(refP:Person)
        OPTIONAL MATCH (s)-[:RECRUITED]->(sr:Supporter)
        WITH p, s, lat, lon, address,
             collect(DISTINCT st.name) AS types,
             collect(DISTINCT ed.name) AS educationLevels,
             collect(DISTINCT ia.name) AS involvementAreas,
             count(DISTINCT a) AS activityCount,
             count(DISTINCT r) AS eventJoinCount,
             count(DISTINCT CASE WHEN r.status = 'Attended' THEN r ELSE NULL END) AS eventAttendRelCount,
             collect(DISTINCT sk.name) AS skills,
             count(DISTINCT refP) AS referredCount,
             count(DISTINCT sr) AS recruitedCount
        RETURN
          lat,
          lon,
          address AS address,
          p.email AS email,
          p.firstName AS firstName,
          p.lastName AS lastName,
          p.age AS age,
          coalesce(p.gender, 'Unspecified') AS gender,
          coalesce(p.timeAvailability, 'Unspecified') AS timeAvailability,
          coalesce(p.about, '') AS about,
          types,
          involvementAreas,
          activityCount,
          eventJoinCount,
          eventAttendRelCount,
          skills,
          educationLevels,
          coalesce(p.eventsAttendedCount, 0) AS eventAttendProp,
          coalesce(p.referralCount, 0) AS referralProp,
          referredCount,
          recruitedCount,
          coalesce(p.effortHours, p.volunteerHours, s.volunteer_hours, s.volunteerHours, 0) AS effortHours,
          coalesce(p.donationTotal, 0) AS donationTotal
        """,
        silent=True,
    )
    if df.empty:
        return df
    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lon"] = pd.to_numeric(df["lon"], errors="coerce")
    df = df.dropna(subset=["lat", "lon"])
    df["timeAvailability"] = df["timeAvailability"].fillna("Unspecified")
    df["about"] = df["about"].fillna("")
    df["address"] = df["address"].fillna("")
    df["addressLabel"] = df["address"].apply(
        lambda value: value if str(value).strip() else "Unspecified"
    )
    df["involvementAreas"] = df["involvementAreas"].apply(lambda v: v or [])
    df["involvementLabel"] = df["involvementAreas"].apply(format_list_label)
    df = enrich_people_core(df)
    df["involvementTitle"] = df["group"].apply(
        lambda value: "Desired involvement"
        if value == "Supporter"
        else "Current involvement"
    )
    df["pointSize"] = (6 + df["effortScore"].clip(lower=0) * 0.2).clip(4, 60)
    df["color"] = df["group"].map(
        {"Supporter": [51, 136, 255, 180], "Member": [142, 68, 173, 180]}
    )
    df["color"] = df["color"].apply(
        lambda value: value if isinstance(value, list) else [120, 120, 120, 180]
    )
    df["ratingColor"] = df["rating"].apply(rating_color)
    return df


def answer_chat(question, df_summary):
    text = question.lower().strip()
    if df_summary.empty:
        return "No supporter data available yet.", None

    if "gender" in text:
        counts = (
            df_summary["gender"]
            .fillna("Unspecified")
            .value_counts()
            .rename_axis("gender")
            .reset_index(name="count")
        )
        return "Here is the gender breakdown.", counts

    if "age" in text:
        age_series = df_summary["age"].dropna()
        if age_series.empty:
            return "No age data available.", None
        stats = (
            age_series.describe()
            .loc[["count", "mean", "min", "max"]]
            .round(2)
            .to_frame("value")
            .reset_index()
            .rename(columns={"index": "metric"})
        )
        return "Age summary (count, mean, min, max).", stats

    if "member" in text or "supporter" in text:
        counts = (
            df_summary["group"]
            .value_counts()
            .rename_axis("group")
            .reset_index(name="count")
        )
        return "Supporter vs member counts.", counts

    if "effort" in text or "hours" in text:
        top = (
            df_summary.sort_values("effortScore", ascending=False)
            .head(10)[["fullName", "email", "group", "effortHours", "eventAttendCount", "referralCount", "ratingStars"]]
        )
        return "Top supporters by effort score.", top

    if "top" in text or "active" in text or "join" in text:
        top = (
            df_summary.sort_values("effortScore", ascending=False)
            .head(10)[["fullName", "email", "group", "effortHours", "eventAttendCount", "referralCount", "ratingStars"]]
        )
        return "Top supporters by effort score.", top

    return (
        "Try asking about gender, age, top joiners, or member counts.",
        None,
    )


def sort_people(df, sort_by):
    if df.empty:
        return df
    if sort_by == "Effort score":
        return df.sort_values("effortScore", ascending=False)
    if sort_by == "Effort hours":
        return df.sort_values("effortHours", ascending=False)
    if sort_by == "Join count":
        return df.sort_values("joinCount", ascending=False)
    if sort_by == "Rating":
        return df.sort_values("rating", ascending=False)
    return df.sort_values("fullName")


def _csv_cluster_by_columns(
    df: pd.DataFrame,
    columns: list[str],
    max_clusters: int = 12,
    min_cluster_size: int = 1,
):
    """
    Deterministic clustering for uploaded CSVs:
    cluster_id = unique combination of selected columns (stringified).
    """
    if df is None or df.empty or not columns:
        return df, pd.DataFrame()

    cols = [c for c in columns if c in df.columns]
    if not cols:
        return df, pd.DataFrame()

    safe = df.copy()
    for c in cols:
        safe[c] = safe[c].astype(str).fillna("").str.strip()
        safe[c] = safe[c].replace({"nan": "", "None": ""})

    safe["_cluster_key"] = safe[cols].apply(lambda row: " | ".join([f"{c}={row[c]}" for c in cols]), axis=1)
    counts = safe["_cluster_key"].value_counts().reset_index()
    counts.columns = ["cluster_key", "count"]

    try:
        max_clusters = int(max_clusters)
    except Exception:
        max_clusters = 12
    max_clusters = max(2, min(50, max_clusters))
    try:
        min_cluster_size = int(min_cluster_size)
    except Exception:
        min_cluster_size = 1
    min_cluster_size = max(1, min(1000, min_cluster_size))

    eligible = counts[counts["count"] >= min_cluster_size]
    top_keys = set(eligible.head(max_clusters)["cluster_key"].tolist())
    safe["cluster_id"] = safe["_cluster_key"].apply(lambda k: k if k in top_keys else "Other")
    summary = safe["cluster_id"].value_counts().reset_index()
    summary.columns = ["cluster_id", "count"]
    return safe.drop(columns=["_cluster_key"]), summary


def render_segments_tab():
    st.subheader("Segments")
    st.caption(
        "Save common filters as segments and re-run them. "
        "Segments = “Who should we work with?” (CRM list-building)."
    )

    st.markdown("#### Create / update segment")
    seg_cols = st.columns([2, 2, 2])
    with seg_cols[0]:
        seg_name = st.text_input("Segment name", key="segments_name", help="A short name for this reusable filter (required).")
        seg_desc = st.text_input("Description (optional)", key="segments_desc", help="Optional note about what this segment is for.")
    with seg_cols[1]:
        group = st.selectbox("Group", ["", "Supporter", "Member"], key="segments_group", help="Optional group restriction.")
        time_availability = st.multiselect(
            "Time availability",
            ["Weekends", "Evenings", "Full-time", "Ad-hoc"],
            default=[],
            key="segments_time",
            help="Match people whose timeAvailability is one of these values.",
        )
        min_effort = st.number_input(
            "Min effort hours",
            min_value=0.0,
            value=0.0,
            step=1.0,
            key="segments_min_effort",
            help="Minimum effort hours threshold (uses the Person.effortHours property).",
        )
    with seg_cols[2]:
        tags = st.multiselect("Tags", get_distinct_values("Tag"), default=[], key="segments_tags", help="Match people who have any of these tags.")
        skills = st.multiselect("Skills", get_distinct_values("Skill"), default=[], key="segments_skills", help="Match people who have any of these skills.")
        name_contains = st.text_input("Name contains", key="segments_name_contains", help="Case-insensitive substring match on the person’s full name.")
        address_contains = st.text_input("Address contains", key="segments_address_contains", help="Case-insensitive substring match on address text.")

    filter_spec = {
        "group": group or None,
        "timeAvailability": time_availability,
        "minEffortHours": min_effort,
        "tags": tags,
        "skills": skills,
        "nameContains": name_contains or None,
        "addressContains": address_contains or None,
    }
    if st.button("Save segment", key="segments_save_btn", help="Save this filter definition as a reusable segment."):
        ok = upsert_segment(seg_name, seg_desc, filter_spec)
        if ok:
            st.session_state["segments_select"] = (seg_name or "").strip()
            st.session_state["segments_saved_notice"] = "Segment saved."
            st.rerun()
        else:
            st.error("Could not save segment (name required).")

    st.markdown("---")
    st.markdown("#### Saved segments")
    if st.session_state.get("segments_saved_notice"):
        st.success(st.session_state.pop("segments_saved_notice"))
    sdf = list_segments()
    if sdf.empty:
        st.info("No segments yet.")
        return

    st.caption("Existing segments")
    st.dataframe(
        sdf[["name", "description", "updatedAt"]].rename(
            columns={"name": "Name", "description": "Description", "updatedAt": "Updated"}
        ),
        use_container_width=True,
    )

    names = sdf["name"].tolist() if "name" in sdf.columns else []
    sel = st.selectbox(
        "Select segment",
        options=[""] + names,
        key="segments_select",
        help="Pick a saved segment to run it and view matching people.",
    )
    if not sel:
        st.caption("Select a segment to run it.")
        return

    seg_rows = sdf[sdf["name"] == sel] if "name" in sdf.columns else pd.DataFrame()
    seg_id = seg_rows["segmentId"].iloc[0] if not seg_rows.empty and "segmentId" in seg_rows.columns else None
    if not seg_id:
        st.error("Could not resolve segment id.")
        return

    run_cols = st.columns([1, 1, 2])
    with run_cols[0]:
        run_limit = st.number_input(
            "Result limit",
            min_value=10,
            max_value=2000,
            value=500,
            step=50,
            key="segments_limit",
            help="Max number of people to return for this segment.",
        )
    with run_cols[1]:
        if st.button("Run segment", key="segments_run_btn", help="Execute this saved segment and show matching people."):
            st.session_state["segments_last_run"] = str(seg_id)
    with run_cols[2]:
        if st.button("Delete segment", key="segments_delete_btn", help="Delete this segment definition from Neo4j."):
            ok = delete_segment(seg_id)
            if ok:
                st.success("Deleted.")
                st.session_state["segments_last_run"] = None
                st.session_state["segments_select"] = ""
                st.rerun()
            else:
                st.error("Delete failed.")

    if st.session_state.get("segments_last_run") == str(seg_id):
        spec = load_segment_filter(seg_id)
        rdf = run_segment(spec, limit=run_limit)
        if rdf.empty:
            st.info("No matches for this segment.")
        else:
            st.dataframe(rdf, use_container_width=True)


def render_deliberation(public_only: bool):
    st.subheader("Deliberation")
    st.caption("Anonymous comments + votes, consensus analysis, and clustering.")
    st.caption(
        "Deliberation = “What do groups of people think?” (insight/clustering from votes)."
    )

    if "delib_anon_id" not in st.session_state:
        st.session_state["delib_anon_id"] = str(uuid4())
    headers = {"X-Participant-Id": st.session_state["delib_anon_id"]}

    conversations = delib_api_get("/conversations", show_error=False)
    if conversations is None:
        render_delib_api_unavailable()
        return
    conversations = conversations or []
    convo_options = {c["topic"]: c["id"] for c in conversations} if conversations else {}
    selected_title = st.selectbox(
        "Select conversation",
        [""] + list(convo_options.keys()),
        key="delib_conversation_select",
        help="Pick which deliberation conversation you want to participate in / analyze.",
    )
    if selected_title:
        st.session_state["delib_conversation_id"] = convo_options[selected_title]

    if public_only:
        tab_participate, tab_reports = st.tabs(["Participate", "Reports"])
    else:
        tab_config, tab_participate, tab_moderate, tab_reports = st.tabs(
            ["Configure", "Participate", "Moderate", "Monitor / Reports"]
        )

        with tab_config:
            st.markdown("### Create conversation")
            topic = st.text_input(
                "Topic",
                key="delib_topic",
                help="Conversation title participants will see.",
            )
            description = st.text_area(
                "Description",
                key="delib_description",
                help="Context shown above the conversation during participation.",
            )
            allow_comment_submission = st.checkbox(
                "Allow participant comments",
                value=True,
                key="delib_allow_comment",
                help="If enabled, participants can submit new comments (may be moderated).",
            )
            allow_viz = st.checkbox(
                "Allow visualization",
                value=True,
                key="delib_allow_viz",
                help="If enabled, show cluster charts/visualizations in reports.",
            )
            moderation_required = st.checkbox(
                "Moderation required",
                value=False,
                key="delib_moderation",
                help="If enabled, submitted comments require approval before becoming voteable.",
            )
            is_open = st.checkbox(
                "Open for participation",
                value=True,
                key="delib_is_open",
                help="If disabled, participation is closed (read-only).",
            )
            if st.button("Create conversation", key="delib_create_convo", help="Create a new deliberation conversation (topic + settings)."):
                if topic.strip():
                    result = delib_api_post(
                        "/conversations",
                        {
                            "topic": topic,
                            "description": description,
                            "allow_comment_submission": allow_comment_submission,
                            "allow_viz": allow_viz,
                            "moderation_required": moderation_required,
                            "is_open": is_open,
                        },
                    )
                    if result:
                        st.success("Conversation created.")
                else:
                    st.warning("Topic is required.")

            convo_id = st.session_state.get("delib_conversation_id")
            if convo_id:
                st.markdown("### Update conversation")
                convo = delib_api_get(f"/conversations/{convo_id}")
                if convo:
                    updated_topic = st.text_input(
                        "Topic (edit)", value=convo.get("topic", ""), key="delib_topic_edit"
                    )
                    updated_description = st.text_area(
                        "Description (edit)",
                        value=convo.get("description") or "",
                        key="delib_description_edit",
                    )
                    updated_allow_comment = st.checkbox(
                        "Allow participant comments (edit)",
                        value=convo.get("allow_comment_submission", True),
                        key="delib_allow_comment_edit",
                    )
                    updated_allow_viz = st.checkbox(
                        "Allow visualization (edit)",
                        value=convo.get("allow_viz", True),
                        key="delib_allow_viz_edit",
                    )
                    updated_moderation = st.checkbox(
                        "Moderation required (edit)",
                        value=convo.get("moderation_required", False),
                        key="delib_moderation_edit",
                    )
                    updated_is_open = st.checkbox(
                        "Open for participation (edit)",
                        value=convo.get("is_open", True),
                        key="delib_is_open_edit",
                    )
                    if st.button("Save settings", key="delib_save_settings", help="Update conversation settings (open/closed, moderation, etc.)."):
                        result = delib_api_patch(
                            f"/conversations/{convo_id}",
                            {
                                "topic": updated_topic,
                                "description": updated_description,
                                "allow_comment_submission": updated_allow_comment,
                                "allow_viz": updated_allow_viz,
                                "moderation_required": updated_moderation,
                                "is_open": updated_is_open,
                            },
                        )
                        if result:
                            st.success("Conversation updated.")

                    st.markdown("### Seed comments (bulk)")
                    seed_text = st.text_area(
                        "One comment per line",
                        key="delib_seed_text",
                        help="Seed statements/questions as separate comments so participants can vote on a shared set.",
                    )
                    if st.button("Add seed comments", key="delib_seed_submit", help="Bulk add seed comments (one per line)."):
                        lines = [line.strip() for line in seed_text.splitlines() if line.strip()]
                        if lines:
                            result = delib_api_post(
                                f"/conversations/{convo_id}/seed-comments:bulk",
                                {"comments": lines},
                            )
                            if result:
                                st.success(f"Added {result.get('created', 0)} comments.")
                        else:
                            st.warning("Add at least one comment.")

                    st.markdown("### Seed comments from CSV column")
                    st.caption("Upload a CSV and pick a column to turn each row into a comment.")
                    csv_upload = st.file_uploader("CSV", type=["csv"], key="delib_seed_csv_upload")
                    if csv_upload is not None:
                        try:
                            df_seed = pd.read_csv(csv_upload)
                        except Exception as exc:
                            st.error(f"Could not read CSV: {exc}")
                            df_seed = pd.DataFrame()
                        if not df_seed.empty:
                            st.dataframe(df_seed.head(10), use_container_width=True)
                            col = st.selectbox(
                                "Column to use as comment text",
                                options=[""] + df_seed.columns.tolist(),
                                key="delib_seed_csv_col",
                            )
                            max_rows = st.number_input(
                                "Max rows to seed",
                                min_value=1,
                                max_value=5000,
                                value=200,
                                step=50,
                                key="delib_seed_csv_max_rows",
                            )
                            if st.button("Seed from CSV", key="delib_seed_csv_btn", help="Create seed comments from the selected CSV column."):
                                if not col:
                                    st.warning("Select a column.")
                                else:
                                    values = [
                                        str(v).strip()
                                        for v in df_seed[col].head(int(max_rows)).tolist()
                                        if str(v).strip() and str(v).strip().lower() not in {"nan", "none"}
                                    ]
                                    values = list(dict.fromkeys(values))  # preserve order, remove dupes
                                    if not values:
                                        st.warning("No valid values found in that column.")
                                    else:
                                        result = delib_api_post(
                                            f"/conversations/{convo_id}/seed-comments:bulk",
                                            {"comments": values},
                                        )
                                        if result:
                                            st.success(f"Seeded {result.get('created', 0)} comments from CSV.")
            else:
                st.info("Select a conversation to edit settings or seed comments.")

    with tab_participate:
        convo_id = st.session_state.get("delib_conversation_id")
        if not convo_id:
            st.info("Select a conversation first.")
        else:
            convo = delib_api_get(f"/conversations/{convo_id}")
            if convo:
                st.subheader(convo["topic"])
                st.caption(convo.get("description") or "")
                if not convo.get("is_open", True):
                    st.warning("This conversation is closed.")

            comments = delib_api_get(f"/conversations/{convo_id}/comments?status=approved") or []
            if not comments:
                st.info("No approved comments yet.")
            else:
                for comment in comments:
                    st.markdown(f"**{comment['text']}**")
                    counts = (
                        f"👍 {comment['agree_count']}  "
                        f"👎 {comment['disagree_count']}  "
                        f"➖ {comment['pass_count']}"
                    )
                    st.caption(counts)
                    cols = st.columns(3)
                    if cols[0].button("Agree", key=f"delib-{comment['id']}-agree", help="Vote Agree on this comment."):
                        delib_api_post(
                            "/vote",
                            {
                                "conversation_id": convo_id,
                                "comment_id": comment["id"],
                                "choice": 1,
                            },
                            headers=headers,
                        )
                    if cols[1].button("Disagree", key=f"delib-{comment['id']}-disagree", help="Vote Disagree on this comment."):
                        delib_api_post(
                            "/vote",
                            {
                                "conversation_id": convo_id,
                                "comment_id": comment["id"],
                                "choice": -1,
                            },
                            headers=headers,
                        )
                    if cols[2].button("Pass", key=f"delib-{comment['id']}-pass", help="Skip/Pass on this comment (neutral / no vote)."):
                        delib_api_post(
                            "/vote",
                            {
                                "conversation_id": convo_id,
                                "comment_id": comment["id"],
                                "choice": 0,
                            },
                            headers=headers,
                        )
                    st.divider()

            if convo and convo.get("allow_comment_submission", True):
                st.markdown("### Submit comment")
                new_comment = st.text_area("Your comment", key="delib_submit_comment")
                if st.button("Submit comment", key="delib_submit_comment_btn", help="Submit a new comment into this conversation (may require moderation)."):
                    if new_comment.strip():
                        delib_api_post(
                            f"/conversations/{convo_id}/comments",
                            {"text": new_comment},
                            headers=headers,
                        )
                    else:
                        st.warning("Comment cannot be empty.")
            else:
                st.caption("Comment submission is disabled for this conversation.")

    if not public_only:
        with tab_moderate:
            convo_id = st.session_state.get("delib_conversation_id")
            if not convo_id:
                st.info("Select a conversation first.")
            else:
                pending = delib_api_get(
                    f"/conversations/{convo_id}/comments?status=pending"
                ) or []
                if not pending:
                    st.info("No pending comments.")
                else:
                    for comment in pending:
                        st.markdown(f"**{comment['text']}**")
                        cols = st.columns(2)
                        if cols[0].button("Approve", key=f"delib-{comment['id']}-approve", help="Approve this pending comment so it becomes voteable."):
                            delib_api_patch(
                                f"/comments/{comment['id']}", {"status": "approved"}
                            )
                        if cols[1].button("Reject", key=f"delib-{comment['id']}-reject", help="Reject this pending comment."):
                            delib_api_patch(
                                f"/comments/{comment['id']}", {"status": "rejected"}
                            )
                        st.divider()

    with tab_reports:
        convo_id = st.session_state.get("delib_conversation_id")
        if not convo_id:
            st.info("Select a conversation first.")
        else:
            report_tab, csv_tab = st.tabs(["Vote-based report", "CSV clustering"])

            with report_tab:
                if st.button("Run analysis", key="delib_run_analysis", help="Compute clusters + consensus/polarizing topics from votes."):
                    report = delib_api_post(f"/conversations/{convo_id}/analyze", {})
                else:
                    report = delib_api_get(f"/conversations/{convo_id}/report")

                if report:
                    metrics = report["metrics"]
                    st.metric("Comments", metrics["total_comments"])
                    st.metric("Participants", metrics["total_participants"])
                    st.metric("Votes", metrics["total_votes"])

                    st.subheader("Potential agreement topics")
                    potential_agreements = report.get("potential_agreements", [])
                    if potential_agreements:
                        for topic in potential_agreements:
                            st.markdown(f"- {topic}")
                    else:
                        st.caption("No strong agreement topics yet.")

                    st.subheader("Consensus statements")
                    consensus_df = pd.DataFrame(metrics["consensus"])
                    if consensus_df.empty:
                        st.caption("No consensus statements yet.")
                    else:
                        st.dataframe(consensus_df, use_container_width=True)

                    st.subheader("Polarizing statements")
                    polarizing_df = pd.DataFrame(metrics["polarizing"])
                    if polarizing_df.empty:
                        st.caption("No polarizing statements yet.")
                    else:
                        st.dataframe(polarizing_df, use_container_width=True)

                    st.subheader("Cluster summaries")
                    summaries_df = pd.DataFrame(report.get("cluster_summaries", []))
                    if summaries_df.empty:
                        st.caption("No cluster summaries available yet.")
                    else:
                        st.dataframe(summaries_df, use_container_width=True)

                    st.subheader("Cluster similarity")
                    similarity_df = pd.DataFrame(report.get("cluster_similarity", []))
                    if similarity_df.empty:
                        st.caption("No similarity data available yet.")
                    else:
                        similarity_df["similarity"] = similarity_df["similarity"].round(3)
                        st.dataframe(similarity_df, use_container_width=True)

                    st.subheader("Venn diagram: shared agreement topics")
                    summaries = report.get("cluster_summaries", [])
                    if not summaries or len(summaries) < 2:
                        st.caption("Need at least two clusters with agreement topics.")
                    elif plt is None or (venn2 is None and venn3 is None):
                        st.caption("matplotlib-venn is required for Venn diagrams.")
                    else:
                        summaries = sorted(
                            summaries, key=lambda s: s.get("size", 0), reverse=True
                        )
                        selected = summaries[:3]
                        sets = [set(item.get("top_agree", [])) for item in selected]
                        if not any(sets):
                            st.caption("No overlapping agreement topics yet.")
                        else:
                            labels = [
                                f"{item.get('cluster_id')} ({item.get('size', 0)})"
                                for item in selected
                            ]
                            fig, ax = plt.subplots()
                            if len(selected) == 2 and venn2:
                                venn2(sets, set_labels=labels, ax=ax)
                            elif len(selected) >= 3 and venn3:
                                venn3(sets[:3], set_labels=labels[:3], ax=ax)
                            st.pyplot(fig, clear_figure=True)

                    points_df = pd.DataFrame(report.get("points", []))
                    if not points_df.empty:
                        st.subheader("Opinion clusters")
                        chart = (
                            alt.Chart(points_df)
                            .mark_circle(size=60, opacity=0.7)
                            .encode(
                                x="x:Q",
                                y="y:Q",
                                color="cluster_id:N",
                                tooltip=["cluster_id", "participant_id"],
                            )
                        )
                        st.altair_chart(chart, use_container_width=True)

            with csv_tab:
                st.subheader("In progress")


from crm.analytics import people as people_analytics
from crm.data import people as people_data
from crm.data import segments as segments_data
from crm.data import tasks as tasks_data
from crm.services import geo as geo_service
from crm.utils import text as text_utils

upsert_person = people_data.upsert_person
search_people = people_data.search_people
load_person_profile = people_data.load_person_profile
update_person_profile = people_data.update_person_profile
get_distinct_values = people_data.get_distinct_values
bulk_upsert_people = people_data.bulk_upsert_people

create_task = tasks_data.create_task
update_task_status = tasks_data.update_task_status
list_tasks = tasks_data.list_tasks
TASK_STATUSES = tasks_data.TASK_STATUSES

upsert_segment = segments_data.upsert_segment
list_segments = segments_data.list_segments
delete_segment = segments_data.delete_segment
load_segment_filter = segments_data.load_segment_filter
run_segment = segments_data.run_segment

clean_text = text_utils.clean_text
split_list = text_utils.split_list
normalize_str_list = text_utils.normalize_str_list
format_list_label = text_utils.format_list_label
normalize_supporter_type = text_utils.normalize_supporter_type
_normalize_column = text_utils._normalize_column
_get_column = text_utils._get_column
_build_import_rows = text_utils.build_import_rows

nominatim_search = geo_service.nominatim_search

classify_group = people_analytics.classify_group
pick_education = people_analytics.pick_education
calc_rating = people_analytics.calc_rating
rating_stars = people_analytics.rating_stars
rating_color = people_analytics.rating_color
age_group = people_analytics.age_group
enrich_people_core = people_analytics.enrich_people_core
load_supporter_summary = people_analytics.load_supporter_summary
load_map_data = people_analytics.load_map_data
answer_chat = people_analytics.answer_chat
sort_people = people_analytics.sort_people


st.title("Freedom Square CRM")

supporter_mode = not PUBLIC_ONLY
if SUPPORTER_ACCESS_CODE:
    st.sidebar.markdown("### Access")
    entered_code = st.sidebar.text_input(
        "Supporter access code",
        type="password",
        help="If set in .env, this code gates access to the CRM tabs. Share only with trusted team members.",
    )
    supporter_mode = entered_code == SUPPORTER_ACCESS_CODE

if not supporter_mode:
    st.info("Public view: deliberation participation only.")
    render_feedback_widget("Deliberation (Public)")
    render_deliberation_page(public_only=True)
    st.stop()

st.sidebar.markdown("### Database")
db_choice = st.sidebar.radio(
    "Connection",
    ["Local (Desktop)", "Sandbox (Web)"],
    index=0,
    key="db_connection_choice",
    help="Switch between your local Neo4j Desktop DB and the Neo4j Sandbox.",
)
if db_choice == "Sandbox (Web)":
    if not NEO4J_SANDBOX_URI or not NEO4J_SANDBOX_PASSWORD:
        st.sidebar.warning(
            "Sandbox credentials missing. Set NEO4J_SANDBOX_URI and NEO4J_SANDBOX_PASSWORD in .env or Streamlit secrets."
        )
        db_ok = False
    else:
        db_ok = init_driver(
            uri=NEO4J_SANDBOX_URI,
            user=NEO4J_SANDBOX_USER,
            password=NEO4J_SANDBOX_PASSWORD,
            database=NEO4J_SANDBOX_DATABASE,
        )
else:
    db_ok = init_driver()

if not db_ok or neo4j_db.driver is None:
    if db_choice == "Sandbox (Web)":
        st.error(
            "Missing or invalid Sandbox Neo4j credentials. Set NEO4J_SANDBOX_URI and NEO4J_SANDBOX_PASSWORD."
        )
    else:
        st.info(
            "Local DBMS not reachable. Start your Neo4j Desktop database and ensure Bolt is running on port 7687."
        )
        st.error("Missing or invalid Neo4j credentials. Set NEO4J_URI and NEO4J_PASSWORD in .env.")
    st.stop()

nav_choice = st.sidebar.radio(
    "Navigate",
    [
        "Dashboard",
        "People",
        "Segments",
        "Outreach",
        "Events",
        "Volunteers",
        "Data",
        "Admin",
        "Deliberation",
        "Slides",
    ],
    index=0,
    key="main_nav",
)

render_feedback_widget(nav_choice)


if nav_choice == "Dashboard":
    render_dashboard_page()
    st.stop()
    dash_overview, dash_chat = st.tabs(["Overview", "Chatbox"])
    with dash_overview:
        st.subheader("Dashboard")
        st.write("Short CRM view focused on supporters, members, activity, and map insights.")
        df_summary = load_supporter_summary()
        if df_summary.empty:
            st.info("No supporters found.")
        else:
            total_people = len(df_summary)
            total_supporters = int((df_summary["group"] == "Supporter").sum())
            total_members = int((df_summary["group"] == "Member").sum())
            avg_effort = float(df_summary["effortScore"].mean()) if total_people else 0.0
            metrics = st.columns(4)
            metrics[0].metric("Total people", f"{total_people:,}")
            metrics[1].metric("Supporters", f"{total_supporters:,}")
            metrics[2].metric("Members", f"{total_members:,}")
            metrics[3].metric("Avg effort score", f"{avg_effort:.1f}")

            group_counts = (
                df_summary["group"]
                .value_counts()
                .rename_axis("group")
                .reset_index(name="count")
            )
            group_chart = (
                alt.Chart(group_counts)
                .mark_bar()
                .encode(x="group:N", y="count:Q", tooltip=["group:N", "count:Q"])
            )

            gender_counts = (
                df_summary["gender"]
                .fillna("Unspecified")
                .value_counts()
                .rename_axis("gender")
                .reset_index(name="count")
            )
            gender_chart = (
                alt.Chart(gender_counts)
                .mark_bar()
                .encode(x="gender:N", y="count:Q", tooltip=["gender:N", "count:Q"])
            )

            rating_counts = (
                df_summary["rating"]
                .value_counts()
                .sort_index()
                .rename_axis("rating")
                .reset_index(name="count")
            )
            rating_chart = (
                alt.Chart(rating_counts)
                .mark_bar()
                .encode(x="rating:O", y="count:Q", tooltip=["rating:O", "count:Q"])
            )

            df_total = run_query(
                """
                MATCH (p:Person)
                RETURN count(p) AS total
                """,
                silent=True,
            )
            total_people = int(df_total["total"].iloc[0]) if not df_total.empty else 0

            df_manifesto = run_query(
                """
                MATCH (p:Person)
                RETURN CASE
                    WHEN p.agreesWithManifesto IS NULL THEN 'Unspecified'
                    WHEN p.agreesWithManifesto THEN 'Yes'
                    ELSE 'No'
                END AS agrees, count(p) AS count
                """,
                silent=True,
            )
            df_membership = run_query(
                """
                MATCH (p:Person)
                RETURN CASE
                    WHEN p.interestedInMembership IS NULL THEN 'Unspecified'
                    WHEN p.interestedInMembership THEN 'Yes'
                    ELSE 'No'
                END AS interested, count(p) AS count
                """,
                silent=True,
            )
            df_facebook = run_query(
                """
                MATCH (p:Person)
                RETURN CASE
                    WHEN p.facebookGroupMember IS NULL THEN 'Unspecified'
                    WHEN p.facebookGroupMember THEN 'Yes'
                    ELSE 'No'
                END AS facebook, count(p) AS count
                """,
                silent=True,
            )

            manifesto_yes = (
                int(df_manifesto.loc[df_manifesto["agrees"] == "Yes", "count"].sum())
                if not df_manifesto.empty
                else 0
            )
            membership_yes = (
                int(df_membership.loc[df_membership["interested"] == "Yes", "count"].sum())
                if not df_membership.empty
                else 0
            )
            facebook_yes = (
                int(df_facebook.loc[df_facebook["facebook"] == "Yes", "count"].sum())
                if not df_facebook.empty
                else 0
            )
            manifesto_pct = (manifesto_yes / total_people * 100) if total_people else 0
            membership_pct = (membership_yes / total_people * 100) if total_people else 0
            facebook_pct = (facebook_yes / total_people * 100) if total_people else 0

            df_types = run_query(
                """
                MATCH (p:Person)-[:CLASSIFIED_AS]->(st:SupporterType)
                RETURN st.name AS type, count(p) AS count
                """,
                silent=True,
            )
            df_type_gender = run_query(
                """
                MATCH (p:Person)-[:CLASSIFIED_AS]->(st:SupporterType)
                RETURN st.name AS type, coalesce(p.gender,'Unspecified') AS gender, count(p) AS count
                """,
                silent=True,
            )
            df_time = run_query(
                """
                MATCH (p:Person)
                RETURN coalesce(p.timeAvailability,'Unspecified') AS availability, count(p) AS count
                """,
                silent=True,
            )
            df_involve = run_query(
                """
                MATCH (p:Person)-[:INTERESTED_IN]->(ia:InvolvementArea)
                RETURN ia.name AS area, count(p) AS count
                ORDER BY count DESC
                LIMIT 10
                """,
                silent=True,
            )
            df_skills = run_query(
                """
                MATCH (p:Person)-[:CAN_CONTRIBUTE_WITH]->(s:Skill)
                RETURN s.name AS skill, count(p) AS count
                ORDER BY count DESC
                LIMIT 10
                """,
                silent=True,
            )

            with st.expander("Statistics", expanded=True):
                stat_cols = st.columns(2)
                with stat_cols[0]:
                    st.markdown("**Supporter vs Member**")
                    st.altair_chart(group_chart, use_container_width=True)
                with stat_cols[1]:
                    st.markdown("**Gender distribution**")
                    st.altair_chart(gender_chart, use_container_width=True)

                stat_cols = st.columns(2)
                with stat_cols[0]:
                    st.markdown("**Rating distribution**")
                    st.altair_chart(rating_chart, use_container_width=True)
                with stat_cols[1]:
                    st.markdown("**Age distribution**")
                    age_df = df_summary.dropna(subset=["age"])
                    if age_df.empty:
                        st.caption("No age data available.")
                    else:
                        age_chart = (
                            alt.Chart(age_df)
                            .mark_bar()
                            .encode(
                                alt.X("age:Q", bin=alt.Bin(maxbins=12)),
                                y="count()",
                                tooltip=["count()"],
                            )
                        )
                        st.altair_chart(age_chart, use_container_width=True)

                st.markdown("**Effort score summary**")
                effort_stats = (
                    df_summary["effortScore"]
                    .describe()
                    .loc[["mean", "min", "max"]]
                    .round(2)
                    .to_frame("value")
                    .reset_index()
                    .rename(columns={"index": "metric"})
                )
                st.dataframe(effort_stats, use_container_width=True)

            with st.expander("Engagement analytics", expanded=False):
                indicator_metrics = st.columns(3)
                indicator_metrics[0].metric("Manifesto Agree (%)", f"{manifesto_pct:.1f}%")
                indicator_metrics[1].metric("Membership Interest (%)", f"{membership_pct:.1f}%")
                indicator_metrics[2].metric("Facebook Group Member (%)", f"{facebook_pct:.1f}%")

            with st.expander("People breakdown", expanded=False):
                if not df_types.empty:
                    type_cols = st.columns(2)
                    with type_cols[0]:
                        st.markdown("**Supporters by Type (Share)**")
                        type_share = (
                            alt.Chart(df_types)
                            .mark_arc(innerRadius=55)
                            .encode(
                                theta=alt.Theta("count:Q"),
                                color=alt.Color("type:N"),
                                tooltip=["type:N", "count:Q"],
                            )
                        )
                        st.altair_chart(type_share, use_container_width=True)
                    with type_cols[1]:
                        st.markdown("**Supporters by Type (Counts)**")
                        type_bar = (
                            alt.Chart(df_types)
                            .mark_bar()
                            .encode(
                                x=alt.X("type:N", sort="-y"),
                                y=alt.Y("count:Q"),
                                tooltip=["type:N", "count:Q"],
                            )
                        )
                        st.altair_chart(type_bar, use_container_width=True)

                if not df_type_gender.empty:
                    st.markdown("**Gender by Supporter Type**")
                    gender_stack = (
                        alt.Chart(df_type_gender)
                        .mark_bar()
                        .encode(
                            x=alt.X("type:N", title="Supporter Type"),
                            y=alt.Y("count:Q"),
                            color=alt.Color("gender:N"),
                            tooltip=["type:N", "gender:N", "count:Q"],
                        )
                    )
                    st.altair_chart(gender_stack, use_container_width=True)

                if not df_time.empty:
                    st.markdown("**Time Availability**")
                    time_bar = (
                        alt.Chart(df_time)
                        .mark_bar()
                        .encode(
                            y=alt.Y("availability:N", sort="-x"),
                            x=alt.X("count:Q"),
                            tooltip=["availability:N", "count:Q"],
                        )
                    )
                    st.altair_chart(time_bar, use_container_width=True)

                indicator_cols = st.columns(3)
                with indicator_cols[0]:
                    if not df_manifesto.empty:
                        st.markdown("**Agrees With Manifesto**")
                        manifesto_chart = (
                            alt.Chart(df_manifesto)
                            .mark_arc(innerRadius=40)
                            .encode(
                                theta=alt.Theta("count:Q"),
                                color=alt.Color("agrees:N"),
                                tooltip=["agrees:N", "count:Q"],
                            )
                        )
                        st.altair_chart(manifesto_chart, use_container_width=True)
                with indicator_cols[1]:
                    if not df_membership.empty:
                        st.markdown("**Interested in Party Membership**")
                        membership_chart = (
                            alt.Chart(df_membership)
                            .mark_arc(innerRadius=40)
                            .encode(
                                theta=alt.Theta("count:Q"),
                                color=alt.Color("interested:N"),
                                tooltip=["interested:N", "count:Q"],
                            )
                        )
                        st.altair_chart(membership_chart, use_container_width=True)
                with indicator_cols[2]:
                    if not df_facebook.empty:
                        st.markdown("**Facebook Group Member**")
                        facebook_chart = (
                            alt.Chart(df_facebook)
                            .mark_arc(innerRadius=40)
                            .encode(
                                theta=alt.Theta("count:Q"),
                                color=alt.Color("facebook:N"),
                                tooltip=["facebook:N", "count:Q"],
                            )
                        )
                        st.altair_chart(facebook_chart, use_container_width=True)

                top_cols = st.columns(2)
                with top_cols[0]:
                    if not df_involve.empty:
                        st.markdown("**Top Involvement Areas**")
                        involve_bar = (
                            alt.Chart(df_involve)
                            .mark_bar()
                            .encode(
                                y=alt.Y("area:N", sort="-x"),
                                x=alt.X("count:Q"),
                                tooltip=["area:N", "count:Q"],
                            )
                        )
                        st.altair_chart(involve_bar, use_container_width=True)
                with top_cols[1]:
                    if not df_skills.empty:
                        st.markdown("**Top Skills**")
                        skill_bar = (
                            alt.Chart(df_skills)
                            .mark_bar()
                            .encode(
                                y=alt.Y("skill:N", sort="-x"),
                                x=alt.X("count:Q"),
                                tooltip=["skill:N", "count:Q"],
                            )
                        )
                        st.altair_chart(skill_bar, use_container_width=True)

    with dash_chat:
        st.subheader("Chatbox")
        st.caption("Ask about supporters, members, gender, age, or top joiners.")
        if "chat_history" not in st.session_state:
            st.session_state["chat_history"] = []

        for message in st.session_state["chat_history"]:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                if message.get("table") is not None:
                    st.dataframe(message["table"], use_container_width=True)

        prompt = st.chat_input("Type your question")
        if prompt:
            st.session_state["chat_history"].append({"role": "user", "content": prompt})
            df_summary = load_supporter_summary()
            response, table = answer_chat(prompt, df_summary)
            st.session_state["chat_history"].append(
                {"role": "assistant", "content": response, "table": table}
            )
            with st.chat_message("assistant"):
                st.markdown(response)
                if table is not None:
                    st.dataframe(table, use_container_width=True)


if nav_choice == "People":
    st.subheader("People")
    section = st.radio(
        "Section",
        ["Directory", "Profiles", "Tasks", "Map"],
        horizontal=True,
        key="people_section",
        help="Switch between people directory, profiles, tasks, and the field map.",
    )
    if section == "Profiles":
        render_profiles_tab_page()
        st.stop()
    if section == "Tasks":
        render_tasks_tab_page()
        st.stop()
    if section == "Map":
        render_map_page()
        st.stop()
    group_view = st.radio(
        "View",
        ["Supporters", "Members"],
        horizontal=True,
        key="people_group_view",
        help="Switch between supporter and member views. The underlying data model is the same Person graph.",
    )

    if group_view == "Supporters":
        st.subheader("Supporters")
        form_col, list_col = st.columns([1, 2])
        with form_col:
            st.markdown("**Search address**")
            search_query = st.text_input(
                "Search address",
                key="supporter_address_search",
                help="Type an address/place name, then click “Find address” to pick a geocoded match.",
            )
            if st.button(
                "Find address",
                key="supporter_address_button",
                help="Lookup address via OpenStreetMap and fill lat/lon.",
            ):
                results = nominatim_search(search_query)
                st.session_state["supporter_address_results"] = results
            if "supporter_address_results" not in st.session_state:
                st.session_state["supporter_address_results"] = []

            options = st.session_state["supporter_address_results"]
            labels = [item.get("display_name", "") for item in options]
            selected_label = st.selectbox(
                "Matches",
                [""] + labels,
                key="supporter_address_select",
                help="Select the best match to auto-fill address + latitude/longitude in the form.",
            )
            if selected_label:
                idx = labels.index(selected_label)
                selected = options[idx]
                st.session_state["supporter_address_value"] = selected.get("display_name")
                st.session_state["supporter_lat_value"] = float(selected.get("lat"))
                st.session_state["supporter_lon_value"] = float(selected.get("lon"))
                st.session_state["supporter_address"] = selected.get("display_name")
                st.session_state["supporter_lat"] = float(selected.get("lat"))
                st.session_state["supporter_lon"] = float(selected.get("lon"))

            st.markdown("**New supporter**")
            default_areas = [
                "Field Organizing",
                "Events",
                "Fundraising",
                "Communications",
                "Tech",
                "Policy",
            ]
            default_skills = [
                "Communication",
                "Fundraising",
                "Data",
                "Design",
                "Engineering",
                "Organizing",
            ]
            supporter_types = ["Supporter"]
            existing_tags = get_distinct_values("Tag")

            with st.form("supporter_form"):
                with st.expander("Contact", expanded=True):
                    col_a, col_b = st.columns(2)
                    with col_a:
                        first_name = st.text_input("First Name")
                        email = st.text_input("Email *")
                        phone = st.text_input("Phone", value="")
                    with col_b:
                        last_name = st.text_input("Last Name")
                        address = st.text_input(
                            "Address",
                            value=st.session_state.get("supporter_address_value", ""),
                            key="supporter_address",
                        )
                        lat_col, lon_col = st.columns(2)
                        with lat_col:
                            latitude = st.number_input(
                                "Latitude",
                                value=float(
                                    st.session_state.get("supporter_lat_value", 0.0) or 0.0
                                ),
                                format="%.6f",
                                key="supporter_lat",
                            )
                        with lon_col:
                            longitude = st.number_input(
                                "Longitude",
                                value=float(
                                    st.session_state.get("supporter_lon_value", 0.0) or 0.0
                                ),
                                format="%.6f",
                                key="supporter_lon",
                            )

                with st.expander("Engagement", expanded=False):
                    col_a, col_b = st.columns(2)
                    with col_a:
                        effort_hours = st.number_input(
                            "Effort Hours", min_value=0.0, value=0.0, step=1.0
                        )
                        time_availability = st.selectbox(
                            "Time Availability",
                            ["", "Weekends", "Evenings", "Full-time", "Ad-hoc"],
                        )
                        supporter_type = st.selectbox(
                            "Supporter Type", supporter_types, index=0
                        )
                        donation_total = st.number_input(
                            "Donation Total (optional)",
                            min_value=0.0,
                            value=0.0,
                            step=10.0,
                        )
                    with col_b:
                        gender = st.selectbox("Gender", ["", "Male", "Female", "Other"])
                        age = st.number_input(
                            "Age", min_value=0, max_value=120, value=0, step=1
                        )
                        agrees = st.checkbox("Agrees with Manifesto", value=False)
                        interested_membership = st.checkbox(
                            "Interested in Party Membership", value=False
                        )
                        facebook_member = st.checkbox("Facebook Group Member", value=False)
                        referrer_email = st.text_input("Referred By (email)", value="")
                    about = st.text_area("About / Motivation", value="")

                with st.expander("Skills & tags", expanded=False):
                    involvement = st.multiselect(
                        "Preferred Areas of Involvement", default_areas, default=[]
                    )
                    skills_sel = st.multiselect("Skills", default_skills, default=[])
                    tags_selected = st.multiselect(
                        "Tags (existing)", existing_tags, default=[]
                    )
                    tags_custom = st.text_input("Add tags (comma separated)")

                tags_combined = normalize_str_list(tags_selected + split_list(tags_custom))
                save = st.form_submit_button(
                    "💾 Save to Neo4j and preview",
                    help="Upsert this supporter into Neo4j (email is required).",
                )

                if save:
                    row = {
                        "First Name": first_name,
                        "Last Name": last_name,
                        "Email": email,
                        "Phone": phone,
                        "Address": address,
                        "Latitude": latitude if latitude != 0.0 else None,
                        "Longitude": longitude if longitude != 0.0 else None,
                        "Gender": gender,
                        "Age": age if age else None,
                        "About You / Motivation": about,
                        "Time Availability": time_availability,
                        "Agrees with Manifesto": "Yes" if agrees else "No",
                        "Interested in Party Membership": "Yes"
                        if interested_membership
                        else "No",
                        "Facebook Group Member": "Yes" if facebook_member else "No",
                        "Supporter Type": supporter_type,
                        "Preferred Areas of Involvement": ", ".join(involvement),
                        "How You Can Help": ", ".join(skills_sel),
                        "Tags": ", ".join(tags_combined),
                        "Referred By Email": referrer_email,
                        "Effort Hours": effort_hours if effort_hours else None,
                        "Donation Total": donation_total if donation_total else None,
                    }
                    st.success("Preview new supporter")
                    st.dataframe(pd.DataFrame([row]))

                    if neo4j_db.driver is None:
                        st.error("Neo4j driver not available. Check connection settings.")
                    elif not email.strip():
                        st.error("Email is required to upsert the supporter.")
                    else:
                        lat_val = latitude if latitude not in [0.0, None] else None
                        lon_val = longitude if longitude not in [0.0, None] else None

                        ok = run_write(
                            """
                            MERGE (p:Person {email: $email})
                            ON CREATE SET
                              p.personId = randomUUID(),
                              p.createdAt = datetime(),
                              p.firstName = $firstName,
                              p.lastName = $lastName,
                              p.phone = $phone,
                              p.gender = $gender,
                              p.age = $age,
                              p.about = $about,
                              p.timeAvailability = $timeAvailability,
                              p.agreesWithManifesto = $agreesWithManifesto,
                              p.interestedInMembership = $interestedInMembership,
                              p.facebookGroupMember = $facebookGroupMember,
                              p.lat = $lat,
                              p.lon = $lon,
                              p.effortHours = $effortHours,
                              p.donationTotal = $donationTotal
                            ON MATCH SET
                              p.firstName = coalesce($firstName, p.firstName),
                              p.lastName = coalesce($lastName, p.lastName),
                              p.phone = coalesce($phone, p.phone),
                              p.gender = coalesce($gender, p.gender),
                              p.age = coalesce($age, p.age),
                              p.about = coalesce($about, p.about),
                              p.timeAvailability = coalesce($timeAvailability, p.timeAvailability),
                              p.agreesWithManifesto = coalesce($agreesWithManifesto, p.agreesWithManifesto),
                              p.interestedInMembership = coalesce($interestedInMembership, p.interestedInMembership),
                              p.facebookGroupMember = coalesce($facebookGroupMember, p.facebookGroupMember),
                              p.lat = coalesce($lat, p.lat),
                              p.lon = coalesce($lon, p.lon),
                              p.effortHours = coalesce($effortHours, p.effortHours),
                              p.donationTotal = coalesce($donationTotal, p.donationTotal)

                            WITH p
                            FOREACH (_ IN CASE WHEN $address IS NULL OR $address = '' THEN [] ELSE [1] END |
                              MERGE (a:Address {fullAddress: $address})
                              ON CREATE SET
                                a.latitude = $lat,
                                a.longitude = $lon
                              ON MATCH SET
                                a.latitude = coalesce($lat, a.latitude),
                                a.longitude = coalesce($lon, a.longitude)
                              MERGE (p)-[:LIVES_AT]->(a)
                            )

                            MERGE (st:SupporterType {name: $supporterType})
                            MERGE (p)-[:CLASSIFIED_AS]->(st)

                            FOREACH (area IN $involvementAreas |
                              MERGE (ia:InvolvementArea {name: area})
                              MERGE (p)-[:INTERESTED_IN]->(ia)
                            )

                            FOREACH (skill IN $skills |
                              MERGE (sk:Skill {name: skill})
                              MERGE (p)-[:CAN_CONTRIBUTE_WITH]->(sk)
                            )

                            FOREACH (tag IN $tags |
                              MERGE (t:Tag {name: tag})
                              MERGE (p)-[:HAS_TAG]->(t)
                            )

                            FOREACH (_ IN CASE
                              WHEN $referrerEmail IS NULL OR $referrerEmail = '' OR $referrerEmail = $email THEN []
                              ELSE [1]
                            END |
                              MERGE (ref:Person {email: $referrerEmail})
                              ON CREATE SET ref.personId = randomUUID()
                              MERGE (p)-[:REFERRED_BY]->(ref)
                            )
                            """,
                            {
                                "email": clean_text(email),
                                "firstName": clean_text(first_name),
                                "lastName": clean_text(last_name),
                                "phone": clean_text(phone),
                                "gender": clean_text(gender),
                                "age": age if age else None,
                                "about": clean_text(about),
                                "timeAvailability": clean_text(time_availability),
                                "agreesWithManifesto": agrees,
                                "interestedInMembership": interested_membership,
                                "facebookGroupMember": facebook_member,
                                "supporterType": clean_text(supporter_type) or "Supporter",
                                "lat": lat_val,
                                "lon": lon_val,
                                "effortHours": effort_hours if effort_hours else None,
                                "donationTotal": donation_total if donation_total else None,
                                "address": clean_text(address),
                                "involvementAreas": involvement,
                                "skills": skills_sel,
                                "tags": tags_combined,
                                "referrerEmail": clean_text(referrer_email),
                            },
                        )
                        if ok:
                            load_supporter_summary.clear()
                            load_map_data.clear()
                            st.success("Supporter saved.")

        with list_col:
            df_summary = load_supporter_summary()
            supporters = df_summary[df_summary["group"] == "Supporter"] if not df_summary.empty else df_summary
            sort_by = st.selectbox(
                "Sort supporters by",
                ["Effort score", "Effort hours", "Join count", "Rating", "Name (A-Z)"],
                key="supporter_sort",
            )
            supporters = sort_people(supporters, sort_by)
            if supporters.empty:
                st.info("No supporters found.")
            else:
                display_df = supporters[
                    [
                        "fullName",
                        "email",
                        "effortHours",
                        "eventAttendCount",
                        "referralCount",
                        "effortScore",
                        "joinCount",
                        "skillCount",
                        "educationLevel",
                        "ratingStars",
                        "gender",
                        "age",
                    ]
                ].rename(
                    columns={
                        "fullName": "Name",
                        "email": "Email",
                        "effortHours": "Effort Hours",
                        "eventAttendCount": "Events Attended",
                        "referralCount": "Referrals",
                        "effortScore": "Effort Score",
                        "joinCount": "Joined",
                        "skillCount": "Skills",
                        "educationLevel": "Education",
                        "ratingStars": "Rating",
                        "gender": "Gender",
                        "age": "Age",
                    }
                )
                st.caption(f"{len(display_df):,} people shown")
                st.dataframe(display_df, use_container_width=True)

        render_import_export_section_ui("supporters", "Supporter", "Supporter")

    else:
        st.subheader("Members")
        form_col, list_col = st.columns([1, 2])
        with form_col:
            st.markdown("**Search address**")
            search_query = st.text_input("Search address", key="member_address_search")
            if st.button(
                "Find address",
                key="member_address_button",
                help="Lookup address via OpenStreetMap and fill lat/lon.",
            ):
                results = nominatim_search(search_query)
                st.session_state["member_address_results"] = results
            if "member_address_results" not in st.session_state:
                st.session_state["member_address_results"] = []

            options = st.session_state["member_address_results"]
            labels = [item.get("display_name", "") for item in options]
            selected_label = st.selectbox(
                "Matches", [""] + labels, key="member_address_select"
            )
            if selected_label:
                idx = labels.index(selected_label)
                selected = options[idx]
                st.session_state["member_address_value"] = selected.get("display_name")
                st.session_state["member_lat_value"] = selected.get("lat")
                st.session_state["member_lon_value"] = selected.get("lon")

            st.markdown("**New member**")
            default_areas = [
                "Field Organizing",
                "Events",
                "Fundraising",
                "Communications",
                "Tech",
                "Policy",
            ]
            default_skills = [
                "Communication",
                "Fundraising",
                "Data",
                "Design",
                "Engineering",
                "Organizing",
            ]
            member_types = ["Member"]
            existing_tags = get_distinct_values("Tag")

            with st.form("member_form"):
                with st.expander("Contact", expanded=True):
                    col_a, col_b = st.columns(2)
                    with col_a:
                        first_name = st.text_input("First Name", key="member_first_name")
                        email = st.text_input("Email *", key="member_email")
                        phone = st.text_input("Phone", value="", key="member_phone")
                    with col_b:
                        last_name = st.text_input("Last Name", key="member_last_name")
                        address = st.text_input(
                            "Address",
                            value=st.session_state.get("member_address_value", ""),
                            key="member_address",
                        )
                        lat_col, lon_col = st.columns(2)
                        with lat_col:
                            latitude = st.number_input(
                                "Latitude",
                                value=float(
                                    st.session_state.get("member_lat_value", 0.0) or 0.0
                                ),
                                format="%.6f",
                                key="member_lat",
                            )
                        with lon_col:
                            longitude = st.number_input(
                                "Longitude",
                                value=float(
                                    st.session_state.get("member_lon_value", 0.0) or 0.0
                                ),
                                format="%.6f",
                                key="member_lon",
                            )

                with st.expander("Engagement", expanded=False):
                    col_a, col_b = st.columns(2)
                    with col_a:
                        effort_hours = st.number_input(
                            "Effort Hours",
                            min_value=0.0,
                            value=0.0,
                            step=1.0,
                            key="member_effort",
                        )
                        time_availability = st.selectbox(
                            "Time Availability",
                            ["", "Weekends", "Evenings", "Full-time", "Ad-hoc"],
                            key="member_time_availability",
                        )
                        member_type = st.selectbox(
                            "Member Type", member_types, index=0, key="member_type"
                        )
                        donation_total = st.number_input(
                            "Donation Total (optional)",
                            min_value=0.0,
                            value=0.0,
                            step=10.0,
                            key="member_donation",
                        )
                    with col_b:
                        gender = st.selectbox(
                            "Gender", ["", "Male", "Female", "Other"], key="member_gender"
                        )
                        age = st.number_input(
                            "Age",
                            min_value=0,
                            max_value=120,
                            value=0,
                            step=1,
                            key="member_age",
                        )
                        agrees = st.checkbox(
                            "Agrees with Manifesto", value=False, key="member_agrees"
                        )
                        interested_membership = st.checkbox(
                            "Interested in Party Membership",
                            value=False,
                            key="member_interested",
                        )
                        facebook_member = st.checkbox(
                            "Facebook Group Member", value=False, key="member_fb"
                        )
                        referrer_email = st.text_input(
                            "Referred By (email)", value="", key="member_referrer"
                        )
                    about = st.text_area("About / Motivation", value="", key="member_about")

                with st.expander("Skills & tags", expanded=False):
                    involvement = st.multiselect(
                        "Preferred Areas of Involvement",
                        default_areas,
                        default=[],
                        key="member_involvement",
                    )
                    skills_sel = st.multiselect(
                        "Skills", default_skills, default=[], key="member_skills"
                    )
                    tags_selected = st.multiselect(
                        "Tags (existing)", existing_tags, default=[], key="member_tags"
                    )
                    tags_custom = st.text_input(
                        "Add tags (comma separated)", key="member_tags_custom"
                    )

                tags_combined = normalize_str_list(tags_selected + split_list(tags_custom))
                save = st.form_submit_button(
                    "💾 Save to Neo4j and preview",
                    help="Upsert this member into Neo4j (email is required).",
                )

                if save:
                    row = {
                        "First Name": first_name,
                        "Last Name": last_name,
                        "Email": email,
                        "Phone": phone,
                        "Address": address,
                        "Latitude": latitude if latitude != 0.0 else None,
                        "Longitude": longitude if longitude != 0.0 else None,
                        "Gender": gender,
                        "Age": age if age else None,
                        "About You / Motivation": about,
                        "Time Availability": time_availability,
                        "Agrees with Manifesto": "Yes" if agrees else "No",
                        "Interested in Party Membership": "Yes"
                        if interested_membership
                        else "No",
                        "Facebook Group Member": "Yes" if facebook_member else "No",
                        "Member Type": member_type,
                        "Preferred Areas of Involvement": ", ".join(involvement),
                        "How You Can Help": ", ".join(skills_sel),
                        "Tags": ", ".join(tags_combined),
                        "Referred By Email": referrer_email,
                        "Effort Hours": effort_hours if effort_hours else None,
                        "Donation Total": donation_total if donation_total else None,
                    }
                    st.success("Preview new member")
                    st.dataframe(pd.DataFrame([row]))

                    if neo4j_db.driver is None:
                        st.error("Neo4j driver not available. Check connection settings.")
                    elif not email.strip():
                        st.error("Email is required to upsert the member.")
                    else:
                        lat_val = latitude if latitude not in [0.0, None] else None
                        lon_val = longitude if longitude not in [0.0, None] else None

                        ok = run_write(
                            """
                            MERGE (p:Person {email: $email})
                            ON CREATE SET
                              p.personId = randomUUID(),
                              p.createdAt = datetime(),
                              p.firstName = $firstName,
                              p.lastName = $lastName,
                              p.phone = $phone,
                              p.gender = $gender,
                              p.age = $age,
                              p.about = $about,
                              p.timeAvailability = $timeAvailability,
                              p.agreesWithManifesto = $agreesWithManifesto,
                              p.interestedInMembership = $interestedInMembership,
                              p.facebookGroupMember = $facebookGroupMember,
                              p.lat = $lat,
                              p.lon = $lon,
                              p.effortHours = $effortHours,
                              p.donationTotal = $donationTotal
                            ON MATCH SET
                              p.firstName = coalesce($firstName, p.firstName),
                              p.lastName = coalesce($lastName, p.lastName),
                              p.phone = coalesce($phone, p.phone),
                              p.gender = coalesce($gender, p.gender),
                              p.age = coalesce($age, p.age),
                              p.about = coalesce($about, p.about),
                              p.timeAvailability = coalesce($timeAvailability, p.timeAvailability),
                              p.agreesWithManifesto = coalesce($agreesWithManifesto, p.agreesWithManifesto),
                              p.interestedInMembership = coalesce($interestedInMembership, p.interestedInMembership),
                              p.facebookGroupMember = coalesce($facebookGroupMember, p.facebookGroupMember),
                              p.lat = coalesce($lat, p.lat),
                              p.lon = coalesce($lon, p.lon),
                              p.effortHours = coalesce($effortHours, p.effortHours),
                              p.donationTotal = coalesce($donationTotal, p.donationTotal)

                            WITH p
                            FOREACH (_ IN CASE WHEN $address IS NULL OR $address = '' THEN [] ELSE [1] END |
                              MERGE (a:Address {fullAddress: $address})
                              ON CREATE SET
                                a.latitude = $lat,
                                a.longitude = $lon
                              ON MATCH SET
                                a.latitude = coalesce($lat, a.latitude),
                                a.longitude = coalesce($lon, a.longitude)
                              MERGE (p)-[:LIVES_AT]->(a)
                            )

                            MERGE (st:SupporterType {name: $supporterType})
                            MERGE (p)-[:CLASSIFIED_AS]->(st)

                            FOREACH (area IN $involvementAreas |
                              MERGE (ia:InvolvementArea {name: area})
                              MERGE (p)-[:INTERESTED_IN]->(ia)
                            )

                            FOREACH (skill IN $skills |
                              MERGE (sk:Skill {name: skill})
                              MERGE (p)-[:CAN_CONTRIBUTE_WITH]->(sk)
                            )

                            FOREACH (tag IN $tags |
                              MERGE (t:Tag {name: tag})
                              MERGE (p)-[:HAS_TAG]->(t)
                            )

                            FOREACH (_ IN CASE
                              WHEN $referrerEmail IS NULL OR $referrerEmail = '' OR $referrerEmail = $email THEN []
                              ELSE [1]
                            END |
                              MERGE (ref:Person {email: $referrerEmail})
                              ON CREATE SET ref.personId = randomUUID()
                              MERGE (p)-[:REFERRED_BY]->(ref)
                            )
                            """,
                            {
                                "email": clean_text(email),
                                "firstName": clean_text(first_name),
                                "lastName": clean_text(last_name),
                                "phone": clean_text(phone),
                                "gender": clean_text(gender),
                                "age": age if age else None,
                                "about": clean_text(about),
                                "timeAvailability": clean_text(time_availability),
                                "agreesWithManifesto": agrees,
                                "interestedInMembership": interested_membership,
                                "facebookGroupMember": facebook_member,
                                "supporterType": clean_text(member_type) or "Member",
                                "lat": lat_val,
                                "lon": lon_val,
                                "effortHours": effort_hours if effort_hours else None,
                                "donationTotal": donation_total if donation_total else None,
                                "address": clean_text(address),
                                "involvementAreas": involvement,
                                "skills": skills_sel,
                                "tags": tags_combined,
                                "referrerEmail": clean_text(referrer_email),
                            },
                        )
                        if ok:
                            load_supporter_summary.clear()
                            load_map_data.clear()
                            st.success("Member saved.")

        with list_col:
            df_summary = load_supporter_summary()
            members = df_summary[df_summary["group"] == "Member"] if not df_summary.empty else df_summary
            sort_by = st.selectbox(
                "Sort members by",
                ["Effort score", "Effort hours", "Join count", "Rating", "Name (A-Z)"],
                key="member_sort",
            )
            members = sort_people(members, sort_by)
            if members.empty:
                st.info("No members found.")
            else:
                display_df = members[
                    [
                        "fullName",
                        "email",
                        "effortHours",
                        "eventAttendCount",
                        "referralCount",
                        "effortScore",
                        "joinCount",
                        "skillCount",
                        "educationLevel",
                        "ratingStars",
                        "gender",
                        "age",
                    ]
                ].rename(
                    columns={
                        "fullName": "Name",
                        "email": "Email",
                        "effortHours": "Effort Hours",
                        "eventAttendCount": "Events Attended",
                        "referralCount": "Referrals",
                        "effortScore": "Effort Score",
                        "joinCount": "Joined",
                        "skillCount": "Skills",
                        "educationLevel": "Education",
                        "ratingStars": "Rating",
                        "gender": "Gender",
                        "age": "Age",
                    }
                )
                st.caption(f"{len(display_df):,} people shown")
                st.dataframe(display_df, use_container_width=True)

        render_import_export_section_ui("members", "Member", "Member")


if nav_choice == "Map":
    st.subheader("Map")
    df_geo = load_map_data()
    if df_geo.empty:
        st.info("No supporters with latitude/longitude found.")
    else:
        sidebar_col, map_col = st.columns([1, 4])
        with sidebar_col:
            st.markdown("**Filters**")
            time_options = sorted(
                [
                    value
                    for value in df_geo["timeAvailability"].dropna().unique().tolist()
                    if str(value).strip() and str(value).lower() != "unspecified"
                ]
            )
            age_group_order = [
                "Under 18",
                "18-24",
                "25-34",
                "35-44",
                "45-54",
                "55-64",
                "65+",
                "Unspecified",
            ]
            age_group_options = [
                value
                for value in age_group_order
                if value in df_geo["ageGroup"].dropna().unique().tolist()
            ]
            skill_options = sorted(
                {
                    str(skill).strip()
                    for skills in df_geo["skills"]
                    for skill in (skills or [])
                    if str(skill).strip()
                }
            )
            gender_options = sorted(
                [
                    value
                    for value in df_geo["gender"].dropna().unique().tolist()
                    if str(value).strip() and str(value).lower() != "unspecified"
                ]
            )

            with st.form("map_filters_form"):
                with st.expander("People", expanded=True):
                    show_supporters = st.checkbox(
                        "Show Supporters",
                        value=True,
                        key="map_show_supporters",
                        help="Include supporters on the map and in the filtered table.",
                    )
                    show_members = st.checkbox(
                        "Show Members",
                        value=True,
                        key="map_show_members",
                        help="Include members on the map and in the filtered table.",
                    )
                    selected_gender = st.multiselect(
                        "Gender", gender_options, default=[], key="map_gender"
                    )
                    selected_age_groups = st.multiselect(
                        "Age Group", age_group_options, default=[], key="map_age_groups"
                    )

                with st.expander("Availability & skills", expanded=False):
                    selected_time = st.multiselect(
                        "Time Availability",
                        time_options,
                        default=[],
                        key="map_time",
                        help="Filter by people’s time availability field.",
                    )
                    selected_skills = st.multiselect(
                        "Skills", skill_options, default=[], key="map_skills"
                    )

                with st.expander("Engagement", expanded=False):
                    min_effort = st.number_input(
                        "Minimum Effort Hours",
                        min_value=0.0,
                        value=0.0,
                        step=1.0,
                        key="map_min_effort",
                    )
                    min_events = st.number_input(
                        "Minimum Events Attended",
                        min_value=0,
                        value=0,
                        step=1,
                        key="map_min_events",
                    )
                    min_referrals = st.number_input(
                        "Minimum Referrals",
                        min_value=0,
                        value=0,
                        step=1,
                        key="map_min_referrals",
                    )

                with st.expander("Text search", expanded=False):
                    address_query = st.text_input(
                        "Address / Location Contains", value="", key="map_address_query"
                    )
                    motivation_query = st.text_input(
                        "Motivation Contains", value="", key="map_motivation_query"
                    )

                action_cols = st.columns(2)
                with action_cols[0]:
                    apply_filters = st.form_submit_button("Apply Filters")
                with action_cols[1]:
                    reset_filters = st.form_submit_button("Reset Filters")

            if reset_filters:
                reset_values = {
                    "map_show_supporters": True,
                    "map_show_members": True,
                    "map_gender": [],
                    "map_age_groups": [],
                    "map_time": [],
                    "map_skills": [],
                    "map_min_effort": 0.0,
                    "map_min_events": 0,
                    "map_min_referrals": 0,
                    "map_address_query": "",
                    "map_motivation_query": "",
                }
                for key, value in reset_values.items():
                    st.session_state[key] = value
                st.rerun()

        df_filtered = df_geo.copy()
        if not show_supporters:
            df_filtered = df_filtered[df_filtered["group"] != "Supporter"]
        if not show_members:
            df_filtered = df_filtered[df_filtered["group"] != "Member"]
        if selected_time:
            df_filtered = df_filtered[df_filtered["timeAvailability"].isin(selected_time)]
        if selected_age_groups:
            df_filtered = df_filtered[df_filtered["ageGroup"].isin(selected_age_groups)]
        if selected_skills:
            df_filtered = df_filtered[
                df_filtered["skills"].apply(
                    lambda skills: any(skill in (skills or []) for skill in selected_skills)
                )
            ]
        if selected_gender:
            df_filtered = df_filtered[df_filtered["gender"].isin(selected_gender)]
        if address_query.strip():
            df_filtered = df_filtered[
                df_filtered["address"].str.contains(address_query, case=False, na=False)
            ]
        if motivation_query.strip():
            df_filtered = df_filtered[
                df_filtered["about"].str.contains(motivation_query, case=False, na=False)
            ]
        if min_effort > 0:
            df_filtered = df_filtered[df_filtered["effortHours"] >= min_effort]
        if min_events > 0:
            df_filtered = df_filtered[df_filtered["eventAttendCount"] >= min_events]
        if min_referrals > 0:
            df_filtered = df_filtered[df_filtered["referralCount"] >= min_referrals]

        with map_col:
            if df_filtered.empty:
                st.info("No map points for the selected filter.")
            else:
                st.caption(f"{len(df_filtered):,} people shown")
                st.caption("Hover points for details. Use the console to open a small profile.")
                legend_cols = st.columns(2)
                legend_cols[0].markdown(
                    "<div style='display:flex;align-items:center;gap:6px;'>"
                    "<span style='width:14px;height:14px;background:#118DC1;display:inline-block;border-radius:3px;'></span>"
                    "<span style='font-size:12px;'>Supporter</span></div>",
                    unsafe_allow_html=True,
                )
                legend_cols[1].markdown(
                    "<div style='display:flex;align-items:center;gap:6px;'>"
                    "<span style='width:14px;height:14px;background:#0B5E85;display:inline-block;border-radius:3px;'></span>"
                    "<span style='font-size:12px;'>Member</span></div>",
                    unsafe_allow_html=True,
                )

                scatter = pdk.Layer(
                    "ScatterplotLayer",
                    data=df_filtered,
                    get_position=["lon", "lat"],
                    get_fill_color="color",
                    get_radius="pointSize",
                    pickable=True,
                )

                view_state = pdk.ViewState(
                    latitude=df_filtered["lat"].mean(),
                    longitude=df_filtered["lon"].mean(),
                    zoom=11,
                    pitch=20,
                )

                layers = [scatter]

                deck = pdk.Deck(
                    layers=layers,
                    initial_view_state=view_state,
                    tooltip={
                        "text": "Name: {fullName}\nTime availability: {timeAvailability}\nRating: {ratingStars}\n{involvementTitle}: {involvementLabel}\nHow they can help: {skillsLabel}\nAddress: {addressLabel}"
                    },
                )
                st.pydeck_chart(deck, use_container_width=True)




                st.markdown("---")
                st.markdown("### Filtered People (Table View)")

                table_df = df_filtered[
                    [
                        "fullName",
                        "email",
                        "group",
                        "timeAvailability",
                        "ageGroup",
                        "gender",
                        "addressLabel",
                        "involvementLabel",
                        "skillsLabel",
                        "ratingStars",
                        "about",
                    ]
                ].rename(
                    columns={
                        "fullName": "Name",
                        "email": "Email",
                        "group": "Group",
                        "timeAvailability": "Time Availability",
                        "ageGroup": "Age Group",
                        "gender": "Gender",
                        "addressLabel": "Address",
                        "involvementLabel": "Involvement",
                        "skillsLabel": "How They Can Help",
                        "ratingStars": "Rating",
                        "about": "Motivation",
                    }
                )

                st.dataframe(table_df, use_container_width=True)


if nav_choice == "Tasks":
    render_tasks_tab_page()


if nav_choice == "Profiles":
    render_profiles_tab_page()


if nav_choice == "Segments":
    render_segments_tab_page()


if nav_choice == "Outreach":
    render_outreach_page()


if nav_choice == "Events":
    render_events_page()


if nav_choice == "Volunteers":
    render_volunteers_page()


if nav_choice == "Data":
    render_data_page()


if nav_choice == "Admin":
    render_admin_page()


if nav_choice == "Deliberation":
    render_deliberation_page(public_only=False)

if nav_choice == "Slides":
    render_slides_page()

