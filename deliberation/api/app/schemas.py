from typing import List, Optional
from pydantic import BaseModel, Field


class ConversationCreate(BaseModel):
    topic: str = Field(..., min_length=3)
    description: Optional[str] = None
    is_open: bool = True
    allow_comment_submission: bool = True
    allow_viz: bool = True
    moderation_required: bool = False


class ConversationUpdate(BaseModel):
    topic: Optional[str] = None
    description: Optional[str] = None
    is_open: Optional[bool] = None
    allow_comment_submission: Optional[bool] = None
    allow_viz: Optional[bool] = None
    moderation_required: Optional[bool] = None


class ConversationOut(BaseModel):
    id: str
    topic: str
    description: Optional[str] = None
    is_open: bool
    allow_comment_submission: bool
    allow_viz: bool
    moderation_required: bool
    created_at: Optional[str] = None
    comments: Optional[int] = None
    participants: Optional[int] = None


class CommentCreate(BaseModel):
    text: str = Field(..., min_length=3)
    author_id: Optional[str] = None


class CommentOut(BaseModel):
    id: str
    text: str
    status: str
    is_seed: bool
    created_at: Optional[str] = None
    author_hash: Optional[str] = None
    agree_count: int = 0
    disagree_count: int = 0
    pass_count: int = 0


class CommentStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(pending|approved|rejected)$")


class SeedCommentsRequest(BaseModel):
    comments: List[str]


class VoteCreate(BaseModel):
    conversation_id: str
    comment_id: str
    choice: int = Field(..., ge=-1, le=1)
    participant_id: Optional[str] = None


class ParticipationDeckOut(BaseModel):
    conversation_id: str
    limit: int
    has_more: bool
    next_cursor: Optional[str] = None
    comments: List[CommentOut]


class CommentMetric(BaseModel):
    id: str
    text: str
    participation: int
    agreement_ratio: float
    consensus_score: float
    polarity_score: float
    agree_count: int
    disagree_count: int
    pass_count: int
    status: str


class MetricsOut(BaseModel):
    total_comments: int
    total_participants: int
    total_votes: int
    consensus: List[CommentMetric]
    polarizing: List[CommentMetric]


class ClusterPoint(BaseModel):
    participant_id: str
    x: float
    y: float
    cluster_id: str


class ClusterSummary(BaseModel):
    cluster_id: str
    size: int
    top_agree: List[str]
    top_disagree: List[str]


class ClusterSimilarity(BaseModel):
    cluster_a: str
    cluster_b: str
    similarity: float


class ReportOut(BaseModel):
    metrics: MetricsOut
    clusters: List[str]
    points: List[ClusterPoint]
    cluster_summaries: List[ClusterSummary]
    cluster_similarity: List[ClusterSimilarity]
    potential_agreements: List[str]
