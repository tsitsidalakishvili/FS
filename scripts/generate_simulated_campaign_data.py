import csv
import random
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path


SEED = 20260306
PEOPLE_COUNT = 420
ALIAS_COUNT = 260
COMMENTS_COUNT = 120
PARTICIPANT_RATE = 0.72
CONVERSATION_ID = "simulated-conversation-2026-03-06"


FIRST_NAMES = [
    "Nino",
    "Ana",
    "Levan",
    "Mariam",
    "Giorgi",
    "Salome",
    "Davit",
    "Irakli",
    "Tekla",
    "Zura",
    "Tako",
    "Luka",
]

LAST_NAMES = [
    "Beridze",
    "Gelashvili",
    "Tsiklauri",
    "Kiknadze",
    "Mchedlishvili",
    "Kapanadze",
    "Japaridze",
    "Lomidze",
    "Ashordia",
    "Chikovani",
]

ADDRESS_BASES = [
    ("Rustaveli Ave", 41.6985, 44.8010),
    ("Chavchavadze Ave", 41.7100, 44.7546),
    ("Pekini Ave", 41.7261, 44.7781),
    ("Guramishvili Ave", 41.7404, 44.7824),
    ("Kazbegi Ave", 41.7247, 44.7640),
    ("Marjanishvili St", 41.7158, 44.8020),
    ("Agmashenebeli Ave", 41.7212, 44.8052),
    ("Abashidze St", 41.7092, 44.7553),
    ("Freedom Square", 41.6934, 44.8017),
    ("Vake Park Area", 41.7089, 44.7427),
]

SKILLS = [
    "Organizing",
    "Data",
    "Fundraising",
    "Canvassing",
    "Logistics",
    "Digital",
    "Training",
    "Operations",
]

EDUCATION_LEVELS = ["High School", "Bachelor", "Master", "PhD"]
GENDERS = ["Male", "Female", "Other"]

COMMENT_TOPICS = [
    "Public transport reliability",
    "Volunteer onboarding speed",
    "Neighborhood safety improvements",
    "Healthcare appointment waiting times",
    "Digital government services",
    "Affordable housing policies",
    "Road safety near schools",
    "Air quality monitoring",
    "Water infrastructure upgrades",
    "Small business licensing process",
    "Youth employment opportunities",
    "Waste management standards",
    "Public procurement transparency",
    "Local budget participation",
    "Access for people with disabilities",
    "Regional internet access",
    "Teacher training support",
    "Emergency response readiness",
    "Community mediation programs",
    "Public park maintenance",
]


def weighted_choice(rng, options, weights):
    return rng.choices(options, weights=weights, k=1)[0]


def stable_participant_id(email: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"participant::{email.lower()}"))


def build_people(rng):
    rows = []
    for idx in range(PEOPLE_COUNT):
        first = rng.choice(FIRST_NAMES)
        last = rng.choice(LAST_NAMES)
        email = f"{first.lower()}.{last.lower()}{idx}@gmail.com"
        gender = weighted_choice(rng, GENDERS, [0.45, 0.45, 0.10])
        age = rng.randint(18, 70)
        phone = f"9955{rng.randint(10000000, 99999999)}"
        base_name, base_lat, base_lon = rng.choice(ADDRESS_BASES)
        street_no = rng.randint(1, 120)
        address = f"{base_name} {street_no}, Tbilisi, Georgia"
        lat = round(base_lat + rng.uniform(-0.0018, 0.0018), 12)
        lon = round(base_lon + rng.uniform(-0.0018, 0.0018), 12)
        supporter_type = weighted_choice(rng, ["Supporter", "Member"], [0.62, 0.38])
        effort_hours = int(max(0, min(260, rng.triangular(0, 260, 92))))
        events_attended = int(max(0, min(40, round(effort_hours / 8 + rng.gauss(0, 3.5)))))
        referral_count = int(max(0, min(25, round(effort_hours / 14 + rng.gauss(0, 2.2)))))
        education = weighted_choice(rng, EDUCATION_LEVELS, [0.25, 0.35, 0.28, 0.12])
        skill_count = weighted_choice(rng, [1, 2, 3], [0.25, 0.45, 0.30])
        person_skills = ", ".join(sorted(rng.sample(SKILLS, k=skill_count)))
        rows.append(
            {
                "email": email,
                "first_name": first,
                "last_name": last,
                "gender": gender,
                "age": age,
                "phone": phone,
                "address": address,
                "lat": lat,
                "lon": lon,
                "supporter_type": supporter_type,
                "effort_hours": effort_hours,
                "events_attended": events_attended,
                "referral_count": referral_count,
                "education": education,
                "skills": person_skills,
            }
        )
    return rows


def build_alias_rows(people_rows):
    alias_rows = []
    for row in people_rows[:ALIAS_COUNT]:
        alias_rows.append(
            {
                "primary_email": row["email"],
                "first": row["first_name"],
                "last": row["last_name"],
                "sex": row["gender"],
                "age": row["age"],
                "mobile": row["phone"],
                "full_address": row["address"],
                "latitude": row["lat"],
                "longitude": row["lon"],
                "type": row["supporter_type"],
                "volunteer_hours": row["effort_hours"],
                "events_attended_count": row["events_attended"],
                "recruits": row["referral_count"],
                "education_level": row["education"],
                "skill_list": row["skills"],
            }
        )
    return alias_rows


def build_comments(rng):
    now = datetime.now(timezone.utc)
    comments = []
    for idx in range(COMMENTS_COUNT):
        topic = COMMENT_TOPICS[idx % len(COMMENT_TOPICS)]
        angle = idx % 6
        if angle == 0:
            text = f"{topic} should be tracked with monthly public dashboards."
        elif angle == 1:
            text = f"We need clearer service-level targets for {topic.lower()}."
        elif angle == 2:
            text = f"Funding for {topic.lower()} should prioritize high-need districts."
        elif angle == 3:
            text = f"Teams should publish implementation milestones for {topic.lower()}."
        elif angle == 4:
            text = f"Residents should be consulted before major changes in {topic.lower()}."
        else:
            text = f"Independent audits would improve trust in {topic.lower()} decisions."

        is_seed = idx < 70
        if is_seed:
            moderation = "approved"
        else:
            moderation = weighted_choice(rng, ["pending", "approved", "rejected"], [0.55, 0.25, 0.20])
        created_at = (now - timedelta(days=rng.randint(0, 20), minutes=rng.randint(0, 1440))).isoformat()
        comments.append(
            {
                "comment_text": text,
                "external_id": str(uuid.uuid4()),
                "is_seed": str(is_seed),
                "created_at": created_at,
                "moderation_status": moderation,
            }
        )
    return comments


def build_delib_import_comments(comment_rows):
    return [
        {
            "external_id": row["external_id"],
            "comment_text": row["comment_text"],
            "status": row["moderation_status"],
            "is_seed": row["is_seed"].lower(),
        }
        for row in comment_rows
    ]


def build_participant_bridge(rng, people_rows):
    bridge = []
    for row in people_rows:
        if rng.random() > PARTICIPANT_RATE:
            continue
        skills = [item.strip() for item in row["skills"].split(",") if item.strip()]
        primary_skill = skills[0] if skills else "Organizing"
        time_availability = weighted_choice(
            rng,
            ["Weekends", "Evenings", "Full-time", "Ad-hoc"],
            [0.30, 0.35, 0.10, 0.25],
        )
        if primary_skill in {"Canvassing", "Organizing", "Operations"}:
            cluster_hint = "ground_game"
        elif primary_skill in {"Data", "Digital"}:
            cluster_hint = "digital_strategy"
        else:
            cluster_hint = "community_outreach"
        bridge.append(
            {
                "email": row["email"],
                "participant_id": stable_participant_id(row["email"]),
                "supporter_type": row["supporter_type"],
                "primary_skill": primary_skill,
                "time_availability": time_availability,
                "cluster_hint": cluster_hint,
                "seed_weight": round(rng.uniform(0.65, 1.45), 3),
            }
        )
    return bridge


def pick_vote_choice(rng, participant_group, bucket):
    roll = rng.random()
    if participant_group == 0:
        if bucket == 0:
            return 1 if roll < 0.72 else -1
        if bucket == 1:
            return -1 if roll < 0.68 else 1
        return 0 if roll < 0.58 else 1
    if participant_group == 1:
        if bucket == 0:
            return -1 if roll < 0.69 else 1
        if bucket == 1:
            return 1 if roll < 0.73 else -1
        return 0 if roll < 0.60 else -1
    if roll < 0.38:
        return 1
    if roll < 0.78:
        return -1
    return 0


def build_votes(rng, bridge_rows, comment_rows):
    approved = [row for row in comment_rows if row["moderation_status"] == "approved"]
    comment_ids = [row["external_id"] for row in approved]
    if not comment_ids:
        return []
    votes = []
    for idx, participant in enumerate(bridge_rows):
        participant_group = idx % 3
        votes_per = rng.randint(18, min(34, len(comment_ids)))
        selected = rng.sample(comment_ids, k=votes_per)
        for comment_id in selected:
            bucket = comment_ids.index(comment_id) % 3
            votes.append(
                {
                    "conversation_id": CONVERSATION_ID,
                    "participant_id": participant["participant_id"],
                    "comment_id": comment_id,
                    "choice": pick_vote_choice(rng, participant_group, bucket),
                }
            )
    return votes


def write_csv(path: Path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main():
    root = Path(__file__).resolve().parents[1]
    data_dir = root / "data"
    deliberation_data_dir = root / "deliberation" / "data"
    rng = random.Random(SEED)

    people_rows = build_people(rng)
    alias_rows = build_alias_rows(people_rows)
    comment_rows = build_comments(rng)
    delib_comments = build_delib_import_comments(comment_rows)
    bridge_rows = build_participant_bridge(rng, people_rows)
    vote_rows = build_votes(rng, bridge_rows, comment_rows)

    write_csv(
        data_dir / "tbilisi_supporters_members_simulated.csv",
        people_rows,
        [
            "email",
            "first_name",
            "last_name",
            "gender",
            "age",
            "phone",
            "address",
            "lat",
            "lon",
            "supporter_type",
            "effort_hours",
            "events_attended",
            "referral_count",
            "education",
            "skills",
        ],
    )
    write_csv(
        data_dir / "tbilisi_supporters_members_alias_import_simulated.csv",
        alias_rows,
        [
            "primary_email",
            "first",
            "last",
            "sex",
            "age",
            "mobile",
            "full_address",
            "latitude",
            "longitude",
            "type",
            "volunteer_hours",
            "events_attended_count",
            "recruits",
            "education_level",
            "skill_list",
        ],
    )
    write_csv(
        data_dir / "polis_seed_comments_simulated.csv",
        comment_rows,
        ["comment_text", "external_id", "is_seed", "created_at", "moderation_status"],
    )
    write_csv(
        data_dir / "supporter_deliberation_bridge_simulated.csv",
        bridge_rows,
        [
            "email",
            "participant_id",
            "supporter_type",
            "primary_skill",
            "time_availability",
            "cluster_hint",
            "seed_weight",
        ],
    )
    write_csv(
        deliberation_data_dir / "georgian_politics_comments_simulated.csv",
        delib_comments,
        ["external_id", "comment_text", "status", "is_seed"],
    )
    write_csv(
        deliberation_data_dir / "georgian_politics_votes_simulated.csv",
        vote_rows,
        ["conversation_id", "participant_id", "comment_id", "choice"],
    )

    print("Generated simulated files:")
    print("- data/tbilisi_supporters_members_simulated.csv")
    print("- data/tbilisi_supporters_members_alias_import_simulated.csv")
    print("- data/polis_seed_comments_simulated.csv")
    print("- data/supporter_deliberation_bridge_simulated.csv")
    print("- deliberation/data/georgian_politics_comments_simulated.csv")
    print("- deliberation/data/georgian_politics_votes_simulated.csv")
    print(f"Rows: people={len(people_rows)}, comments={len(comment_rows)}, bridge={len(bridge_rows)}, votes={len(vote_rows)}")


if __name__ == "__main__":
    main()
