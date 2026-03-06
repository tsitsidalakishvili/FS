import base64
import hashlib
import json
import os
import threading
import time
from collections import defaultdict
from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, Header, HTTPException, Query

from .analytics import compute_cluster_insights, compute_metrics, run_clustering
from .db import NEO4J_DATABASE, get_driver
from .schemas import (
    CommentCreate,
    CommentOut,
    CommentStatusUpdate,
    ConversationCreate,
    ConversationOut,
    ConversationUpdate,
    MetricsOut,
    ParticipationDeckOut,
    ReportOut,
    SeedCommentsRequest,
    VoteCreate,
)

router = APIRouter()

ANON_SALT = os.getenv("ANON_SALT", "dev-salt")
INVITE_TOKENS = {
    token.strip()
    for token in os.getenv("PARTICIPATION_INVITE_TOKENS", "").split(",")
    if token.strip()
}
_RATE_LIMIT_WINDOW_SECONDS = 60
try:
    VOTE_RATE_LIMIT_PER_MINUTE = max(0, int(os.getenv("VOTE_RATE_LIMIT_PER_MINUTE", "0")))
except ValueError:
    VOTE_RATE_LIMIT_PER_MINUTE = 0
_vote_rate_limit_state = defaultdict(list)
_vote_rate_limit_lock = threading.Lock()


def _hash_participant(raw_id: str) -> str:
    digest = hashlib.sha256(f"{ANON_SALT}:{raw_id}".encode("utf-8")).hexdigest()
    return digest


def _enforce_invite_token(x_invite_token: Optional[str]) -> None:
    if INVITE_TOKENS and x_invite_token not in INVITE_TOKENS:
        raise HTTPException(status_code=401, detail="Valid invite token required")


def _enforce_vote_rate_limit(participant_id: str) -> None:
    if VOTE_RATE_LIMIT_PER_MINUTE <= 0:
        return
    now = time.time()
    threshold = now - _RATE_LIMIT_WINDOW_SECONDS
    with _vote_rate_limit_lock:
        recent = _vote_rate_limit_state[participant_id]
        while recent and recent[0] < threshold:
            recent.pop(0)
        if len(recent) >= VOTE_RATE_LIMIT_PER_MINUTE:
            raise HTTPException(status_code=429, detail="Vote rate limit exceeded")
        recent.append(now)


def _encode_cursor(created_at: str, comment_id: str) -> str:
    payload = json.dumps({"created_at": created_at, "comment_id": comment_id}, separators=(",", ":"))
    return base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii")


def _decode_cursor(cursor: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    if not cursor:
        return None, None
    try:
        raw = base64.urlsafe_b64decode(cursor.encode("ascii")).decode("utf-8")
        payload = json.loads(raw)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid pagination cursor") from exc
    created_at = payload.get("created_at")
    comment_id = payload.get("comment_id")
    if not created_at or not comment_id:
        raise HTTPException(status_code=400, detail="Invalid pagination cursor")
    return created_at, comment_id


def _node_to_dict(node):
    data = dict(node)
    for key, value in data.items():
        if hasattr(value, "to_native"):
            data[key] = value.to_native()
        elif hasattr(value, "isoformat"):
            data[key] = value.isoformat()
        else:
            data[key] = value
    return data


def _execute_read(session, query, params=None):
    if hasattr(session, "execute_read"):
        return session.execute_read(lambda tx: list(tx.run(query, params or {})))
    return session.read_transaction(lambda tx: list(tx.run(query, params or {})))


def _execute_write(session, query, params=None):
    def _run(tx):
        result = tx.run(query, params or {})
        return list(result)

    if hasattr(session, "execute_write"):
        return session.execute_write(_run)
    return session.write_transaction(_run)


def _get_conversation(conversation_id: str) -> dict:
    driver = get_driver()
    query = "MATCH (c:Conversation {id: $id}) RETURN c"
    with driver.session(database=NEO4J_DATABASE) as session:
        records = _execute_read(session, query, {"id": conversation_id})
    if not records:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return _node_to_dict(records[0]["c"])


def _conversation_out(convo: dict, comments=None, participants=None) -> dict:
    return {
        "id": convo["id"],
        "topic": convo["topic"],
        "description": convo.get("description"),
        "is_open": bool(convo.get("isOpen", True)),
        "allow_comment_submission": bool(convo.get("allowCommentSubmission", True)),
        "allow_viz": bool(convo.get("allowViz", True)),
        "moderation_required": bool(convo.get("moderationRequired", False)),
        "created_at": str(convo.get("createdAt")),
        "comments": comments,
        "participants": participants,
    }


@router.post("/conversations", response_model=ConversationOut)
def create_conversation(payload: ConversationCreate):
    convo_id = str(uuid4())
    driver = get_driver()
    query = """
    CREATE (c:Conversation {
        id: $id,
        topic: $topic,
        description: $description,
        isOpen: $is_open,
        allowCommentSubmission: $allow_comment_submission,
        allowViz: $allow_viz,
        moderationRequired: $moderation_required,
        createdAt: datetime()
    })
    RETURN c
    """
    with driver.session(database=NEO4J_DATABASE) as session:
        records = _execute_write(
            session,
            query,
            {
                "id": convo_id,
                "topic": payload.topic,
                "description": payload.description,
                "is_open": payload.is_open,
                "allow_comment_submission": payload.allow_comment_submission,
                "allow_viz": payload.allow_viz,
                "moderation_required": payload.moderation_required,
            },
        )
        record = records[0] if records else None
        if record is None:
            raise HTTPException(status_code=500, detail="Conversation creation failed")
        convo = _node_to_dict(record["c"])
    return _conversation_out(convo)


@router.patch("/conversations/{conversation_id}", response_model=ConversationOut)
def update_conversation(conversation_id: str, payload: ConversationUpdate):
    updates = {}
    if payload.topic is not None:
        updates["topic"] = payload.topic
    if payload.description is not None:
        updates["description"] = payload.description
    if payload.is_open is not None:
        updates["isOpen"] = payload.is_open
    if payload.allow_comment_submission is not None:
        updates["allowCommentSubmission"] = payload.allow_comment_submission
    if payload.allow_viz is not None:
        updates["allowViz"] = payload.allow_viz
    if payload.moderation_required is not None:
        updates["moderationRequired"] = payload.moderation_required

    driver = get_driver()
    query = """
    MATCH (c:Conversation {id: $id})
    SET c += $updates
    RETURN c
    """
    with driver.session(database=NEO4J_DATABASE) as session:
        records = _execute_write(session, query, {"id": conversation_id, "updates": updates})
        record = records[0] if records else None
    if record is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return _conversation_out(_node_to_dict(record["c"]))


@router.get("/conversations", response_model=List[ConversationOut])
def list_conversations():
    driver = get_driver()
    query = "MATCH (c:Conversation) RETURN c ORDER BY c.createdAt DESC"
    with driver.session(database=NEO4J_DATABASE) as session:
        records = _execute_read(session, query)
    conversations = []
    for record in records:
        convo = _node_to_dict(record["c"])
        conversations.append(_conversation_out(convo))
    return conversations


@router.get("/participation/conversations", response_model=List[ConversationOut])
def list_participation_conversations(x_invite_token: Optional[str] = Header(None)):
    _enforce_invite_token(x_invite_token)
    driver = get_driver()
    query = """
    MATCH (c:Conversation)
    WHERE coalesce(c.isOpen, true) = true
    RETURN c
    ORDER BY c.createdAt DESC
    """
    with driver.session(database=NEO4J_DATABASE) as session:
        records = _execute_read(session, query)
    conversations = []
    for record in records:
        convo = _node_to_dict(record["c"])
        conversations.append(_conversation_out(convo))
    return conversations


@router.get("/conversations/{conversation_id}", response_model=ConversationOut)
def get_conversation(conversation_id: str):
    driver = get_driver()
    query = """
    MATCH (c:Conversation {id: $id})
    OPTIONAL MATCH (c)-[:HAS_COMMENT]->(cm:Comment)
    WITH c, count(cm) AS comments
    OPTIONAL MATCH (p:Participant)-[:PARTICIPATED_IN]->(c)
    RETURN c, comments, count(DISTINCT p) AS participants
    """
    with driver.session(database=NEO4J_DATABASE) as session:
        record = _execute_read(session, query, {"id": conversation_id})
    if not record:
        raise HTTPException(status_code=404, detail="Conversation not found")
    row = record[0]
    convo = _node_to_dict(row["c"])
    return _conversation_out(convo, comments=row["comments"], participants=row["participants"])


@router.post("/conversations/{conversation_id}/seed-comments:bulk")
def seed_comments(conversation_id: str, payload: SeedCommentsRequest):
    if not payload.comments:
        raise HTTPException(status_code=400, detail="No comments provided")
    convo = _get_conversation(conversation_id)
    if not bool(convo.get("isOpen", True)):
        raise HTTPException(status_code=400, detail="Conversation is closed")

    seed_items = [{"id": str(uuid4()), "text": text} for text in payload.comments if text.strip()]
    if not seed_items:
        raise HTTPException(status_code=400, detail="No valid comment text provided")

    driver = get_driver()
    query = """
    MATCH (c:Conversation {id: $cid})
    UNWIND $items AS item
    CREATE (cm:Comment {
        id: item.id,
        text: item.text,
        createdAt: datetime(),
        status: "approved",
        isSeed: true,
        authorHash: "seed"
    })
    CREATE (c)-[:HAS_COMMENT]->(cm)
    RETURN count(cm) AS created
    """
    with driver.session(database=NEO4J_DATABASE) as session:
        records = _execute_write(session, query, {"cid": conversation_id, "items": seed_items})
        created = records[0]["created"] if records else 0
    return {"created": int(created)}


@router.post("/conversations/{conversation_id}/comments", response_model=CommentOut)
def create_comment(
    conversation_id: str,
    payload: CommentCreate,
    x_participant_id: Optional[str] = Header(None),
    x_invite_token: Optional[str] = Header(None),
):
    _enforce_invite_token(x_invite_token)
    convo = _get_conversation(conversation_id)
    if not bool(convo.get("isOpen", True)):
        raise HTTPException(status_code=400, detail="Conversation is closed")
    if not bool(convo.get("allowCommentSubmission", True)):
        raise HTTPException(status_code=400, detail="Comment submissions are disabled")

    raw_id = payload.author_id or x_participant_id or str(uuid4())
    author_hash = _hash_participant(raw_id)
    status = "pending" if bool(convo.get("moderationRequired", False)) else "approved"
    comment_id = str(uuid4())
    driver = get_driver()
    query = """
    MATCH (c:Conversation {id: $cid})
    CREATE (cm:Comment {
        id: $id,
        text: $text,
        createdAt: datetime(),
        status: $status,
        isSeed: false,
        authorHash: $authorHash
    })
    CREATE (c)-[:HAS_COMMENT]->(cm)
    RETURN cm
    """
    with driver.session(database=NEO4J_DATABASE) as session:
        records = _execute_write(
            session,
            query,
            {"cid": conversation_id, "id": comment_id, "text": payload.text, "status": status, "authorHash": author_hash},
        )
        record = records[0] if records else None
        if record is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
        comment = _node_to_dict(record["cm"])
    return {
        "id": comment["id"],
        "text": comment["text"],
        "status": comment.get("status", status),
        "is_seed": bool(comment.get("isSeed", False)),
        "created_at": str(comment.get("createdAt")),
        "author_hash": comment.get("authorHash"),
        "agree_count": 0,
        "disagree_count": 0,
        "pass_count": 0,
    }


@router.get("/conversations/{conversation_id}/comments", response_model=List[CommentOut])
def list_comments(
    conversation_id: str,
    status: Optional[str] = Query(None, pattern="^(pending|approved|rejected)$"),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    only_unvoted_for_participant: bool = Query(False),
    x_participant_id: Optional[str] = Header(None),
):
    participant_hash = _hash_participant(x_participant_id) if x_participant_id else None
    driver = get_driver()
    query = """
    MATCH (c:Conversation {id: $cid})-[:HAS_COMMENT]->(cm:Comment)
    WHERE ($status IS NULL OR cm.status = $status)
      AND (
        $only_unvoted_for_participant = false
        OR $participant_hash IS NULL
        OR NOT EXISTS {
            MATCH (:Participant {id: $participant_hash})-[:VOTED]->(cm)
        }
      )
    OPTIONAL MATCH (p:Participant)-[v:VOTED]->(cm)
    WITH cm,
        sum(CASE WHEN v.choice = 1 THEN 1 ELSE 0 END) AS agree_count,
        sum(CASE WHEN v.choice = -1 THEN 1 ELSE 0 END) AS disagree_count,
        sum(CASE WHEN v.choice = 0 THEN 1 ELSE 0 END) AS pass_count
    RETURN cm, agree_count, disagree_count, pass_count
    ORDER BY cm.createdAt
    SKIP $offset
    LIMIT $limit
    """
    with driver.session(database=NEO4J_DATABASE) as session:
        records = _execute_read(
            session,
            query,
            {
                "cid": conversation_id,
                "status": status,
                "offset": offset,
                "limit": limit,
                "only_unvoted_for_participant": only_unvoted_for_participant,
                "participant_hash": participant_hash,
            },
        )
    comments = []
    for record in records:
        comment = _node_to_dict(record["cm"])
        comments.append(
            {
                "id": comment["id"],
                "text": comment["text"],
                "status": comment.get("status", "approved"),
                "is_seed": bool(comment.get("isSeed", False)),
                "created_at": str(comment.get("createdAt")),
                "author_hash": comment.get("authorHash"),
                "agree_count": int(record["agree_count"] or 0),
                "disagree_count": int(record["disagree_count"] or 0),
                "pass_count": int(record["pass_count"] or 0),
            }
        )
    return comments


@router.get(
    "/participation/conversations/{conversation_id}/deck",
    response_model=ParticipationDeckOut,
)
def get_participation_deck(
    conversation_id: str,
    cursor: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    x_participant_id: Optional[str] = Header(None),
    x_invite_token: Optional[str] = Header(None),
):
    _enforce_invite_token(x_invite_token)
    conversation = _get_conversation(conversation_id)
    participant_hash = _hash_participant(x_participant_id) if x_participant_id else None
    cursor_created_at, cursor_comment_id = _decode_cursor(cursor)

    driver = get_driver()
    query = """
    MATCH (c:Conversation {id: $cid})-[:HAS_COMMENT]->(cm:Comment)
    WHERE cm.status = "approved"
      AND (
        $participant_hash IS NULL
        OR NOT EXISTS {
            MATCH (:Participant {id: $participant_hash})-[:VOTED]->(cm)
        }
      )
      AND (
        $cursor_created_at IS NULL
        OR cm.createdAt > datetime($cursor_created_at)
        OR (cm.createdAt = datetime($cursor_created_at) AND cm.id > $cursor_comment_id)
      )
    OPTIONAL MATCH (p:Participant)-[v:VOTED]->(cm)
    WITH cm,
        sum(CASE WHEN v.choice = 1 THEN 1 ELSE 0 END) AS agree_count,
        sum(CASE WHEN v.choice = -1 THEN 1 ELSE 0 END) AS disagree_count,
        sum(CASE WHEN v.choice = 0 THEN 1 ELSE 0 END) AS pass_count
    RETURN cm, agree_count, disagree_count, pass_count
    ORDER BY cm.createdAt, cm.id
    LIMIT $limit_plus_one
    """
    with driver.session(database=NEO4J_DATABASE) as session:
        records = _execute_read(
            session,
            query,
            {
                "cid": conversation_id,
                "participant_hash": participant_hash,
                "cursor_created_at": cursor_created_at,
                "cursor_comment_id": cursor_comment_id,
                "limit_plus_one": limit + 1,
            },
        )

    has_more = len(records) > limit
    records = records[:limit]
    comments = []
    next_cursor = None
    for record in records:
        comment = _node_to_dict(record["cm"])
        comments.append(
            {
                "id": comment["id"],
                "text": comment["text"],
                "status": comment.get("status", "approved"),
                "is_seed": bool(comment.get("isSeed", False)),
                "created_at": str(comment.get("createdAt")),
                "author_hash": comment.get("authorHash"),
                "agree_count": int(record["agree_count"] or 0),
                "disagree_count": int(record["disagree_count"] or 0),
                "pass_count": int(record["pass_count"] or 0),
            }
        )
        next_cursor = _encode_cursor(str(comment.get("createdAt")), comment["id"])
    return {
        "conversation_id": conversation["id"],
        "limit": limit,
        "has_more": has_more,
        "next_cursor": next_cursor if has_more else None,
        "comments": comments,
    }


@router.patch("/comments/{comment_id}", response_model=CommentOut)
def update_comment_status(comment_id: str, payload: CommentStatusUpdate):
    driver = get_driver()
    query = """
    MATCH (cm:Comment {id: $id})
    SET cm.status = $status
    RETURN cm
    """
    with driver.session(database=NEO4J_DATABASE) as session:
        records = _execute_write(session, query, {"id": comment_id, "status": payload.status})
        record = records[0] if records else None
    if record is None:
        raise HTTPException(status_code=404, detail="Comment not found")
    comment = _node_to_dict(record["cm"])
    return {
        "id": comment["id"],
        "text": comment["text"],
        "status": comment.get("status", payload.status),
        "is_seed": bool(comment.get("isSeed", False)),
        "created_at": str(comment.get("createdAt")),
        "author_hash": comment.get("authorHash"),
        "agree_count": 0,
        "disagree_count": 0,
        "pass_count": 0,
    }


@router.post("/vote")
def cast_vote(
    payload: VoteCreate,
    x_participant_id: Optional[str] = Header(None),
    x_invite_token: Optional[str] = Header(None),
):
    _enforce_invite_token(x_invite_token)
    if payload.choice not in (-1, 0, 1):
        raise HTTPException(status_code=400, detail="Vote choice must be -1, 0, or 1")
    convo = _get_conversation(payload.conversation_id)
    if not bool(convo.get("isOpen", True)):
        raise HTTPException(status_code=400, detail="Conversation is closed")

    raw_id = payload.participant_id or x_participant_id or str(uuid4())
    participant_id = _hash_participant(raw_id)
    _enforce_vote_rate_limit(participant_id)
    driver = get_driver()
    query = """
    MATCH (c:Conversation {id: $cid})-[:HAS_COMMENT]->(cm:Comment {id: $comment_id})
    WHERE cm.status = "approved"
    MERGE (p:Participant {id: $pid})
    ON CREATE SET p.createdAt = datetime()
    MERGE (p)-[:PARTICIPATED_IN]->(c)
    MERGE (p)-[v:VOTED]->(cm)
    SET v.choice = $choice,
        v.votedAt = datetime()
    RETURN v
    """
    with driver.session(database=NEO4J_DATABASE) as session:
        records = _execute_write(
            session,
            query,
            {
                "cid": payload.conversation_id,
                "comment_id": payload.comment_id,
                "pid": participant_id,
                "choice": payload.choice,
            },
        )
        record = records[0] if records else None
    if record is None:
        raise HTTPException(status_code=404, detail="Conversation or comment not found")
    return {"participant_id": participant_id, "comment_id": payload.comment_id, "choice": payload.choice}


def _collect_comments_and_votes(conversation_id: str):
    driver = get_driver()
    comments_query = """
    MATCH (c:Conversation {id: $cid})-[:HAS_COMMENT]->(cm:Comment)
    RETURN cm
    ORDER BY cm.createdAt
    """
    votes_query = """
    MATCH (c:Conversation {id: $cid})-[:HAS_COMMENT]->(cm:Comment)
    MATCH (p:Participant)-[v:VOTED]->(cm)
    RETURN p.id AS participant_id, cm.id AS comment_id, v.choice AS choice
    """
    with driver.session(database=NEO4J_DATABASE) as session:
        comment_records = _execute_read(session, comments_query, {"cid": conversation_id})
        vote_records = _execute_read(session, votes_query, {"cid": conversation_id})
    comments = [_node_to_dict(record["cm"]) for record in comment_records]
    votes = [record.data() for record in vote_records]
    return comments, votes


def _build_metrics(conversation_id: str) -> MetricsOut:
    comments, votes = _collect_comments_and_votes(conversation_id)
    points, label_map = run_clustering(votes)
    consensus, polarizing = compute_metrics(comments, votes, label_map)
    cluster_summaries, cluster_similarity = compute_cluster_insights(
        comments, votes, label_map
    )
    potential_agreements = [item["text"] for item in consensus][:10]
    total_votes = len(votes)
    participants = len({vote["participant_id"] for vote in votes})
    return (
        MetricsOut(
            total_comments=len(comments),
            total_participants=participants,
            total_votes=total_votes,
            consensus=consensus,
            polarizing=polarizing,
        ),
        points,
        label_map,
        cluster_summaries,
        cluster_similarity,
        potential_agreements,
    )


@router.post("/conversations/{conversation_id}/analyze", response_model=ReportOut)
def analyze_conversation(conversation_id: str):
    metrics, points, label_map, cluster_summaries, cluster_similarity, potential_agreements = _build_metrics(
        conversation_id
    )
    run_id = str(uuid4())
    clusters = sorted({point["cluster_id"] for point in points})

    cluster_sizes = {}
    for point in points:
        cluster_sizes[point["cluster_id"]] = cluster_sizes.get(point["cluster_id"], 0) + 1

    cluster_payload = [
        {"id": f"{run_id}-{cluster_id}", "label": cluster_id, "size": size}
        for cluster_id, size in cluster_sizes.items()
    ]
    assignments = [
        {"participant_id": point["participant_id"], "cluster_id": f"{run_id}-{point['cluster_id']}"}
        for point in points
    ]

    driver = get_driver()
    with driver.session(database=NEO4J_DATABASE) as session:
        _execute_write(
            session,
            """
            MATCH (c:Conversation {id: $cid})
            CREATE (ar:AnalysisRun {
                id: $rid,
                createdAt: datetime(),
                method: "pca+kmeans"
            })
            MERGE (ar)-[:FOR_CONVERSATION]->(c)
            """,
            {"cid": conversation_id, "rid": run_id},
        )
        _execute_write(
            session,
            """
            MATCH (c:Conversation {id: $cid})<-[:OF_CONVERSATION]-(cl:Cluster)
            DETACH DELETE cl
            """,
            {"cid": conversation_id},
        )
        if cluster_payload:
            _execute_write(
                session,
                """
                UNWIND $clusters AS cdata
                MATCH (c:Conversation {id: $cid})
                CREATE (cl:Cluster {id: cdata.id})
                SET cl.label = cdata.label,
                    cl.size = cdata.size,
                    cl.updatedAt = datetime(),
                    cl.runId = $rid
                MERGE (cl)-[:OF_CONVERSATION]->(c)
                """,
                {"cid": conversation_id, "clusters": cluster_payload, "rid": run_id},
            )
        if assignments:
            _execute_write(
                session,
                """
                UNWIND $assignments AS a
                MATCH (p:Participant {id: a.participant_id})
                MATCH (cl:Cluster {id: a.cluster_id})
                MERGE (p)-[:IN_CLUSTER {runId: $rid}]->(cl)
                """,
                {"assignments": assignments, "rid": run_id},
            )
        results_payload = [item.dict() for item in (metrics.consensus + metrics.polarizing)]
        _execute_write(
            session,
            """
            UNWIND $results AS r
            MATCH (cm:Comment {id: r.id})
            MATCH (ar:AnalysisRun {id: $rid})
            MERGE (ar)-[res:HAS_RESULT]->(cm)
            SET res.consensusScore = r.consensus_score,
                res.polarityScore = r.polarity_score,
                res.participation = r.participation,
                res.agreementRatio = r.agreement_ratio,
                res.agreeCount = r.agree_count,
                res.disagreeCount = r.disagree_count,
                res.passCount = r.pass_count,
                res.status = r.status
            """,
            {"rid": run_id, "results": results_payload},
        )

    return ReportOut(
        metrics=metrics,
        clusters=clusters,
        points=points,
        cluster_summaries=cluster_summaries,
        cluster_similarity=cluster_similarity,
        potential_agreements=potential_agreements,
    )


@router.get("/conversations/{conversation_id}/report", response_model=ReportOut)
def get_report(conversation_id: str):
    metrics, points, _, cluster_summaries, cluster_similarity, potential_agreements = _build_metrics(
        conversation_id
    )
    clusters = sorted({point["cluster_id"] for point in points})
    return ReportOut(
        metrics=metrics,
        clusters=clusters,
        points=points,
        cluster_summaries=cluster_summaries,
        cluster_similarity=cluster_similarity,
        potential_agreements=potential_agreements,
    )
