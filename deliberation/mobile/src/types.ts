export type VoteChoice = -1 | 0 | 1;

export type Conversation = {
  id: string;
  topic: string;
  description?: string | null;
  is_open: boolean;
  allow_comment_submission: boolean;
  allow_viz: boolean;
  moderation_required: boolean;
  created_at?: string | null;
};

export type Comment = {
  id: string;
  text: string;
  status: string;
  is_seed: boolean;
  created_at?: string | null;
  author_hash?: string | null;
  agree_count: number;
  disagree_count: number;
  pass_count: number;
};

export type ParticipationDeck = {
  conversation_id: string;
  limit: number;
  has_more: boolean;
  next_cursor?: string | null;
  comments: Comment[];
};

export type VotePayload = {
  conversation_id: string;
  comment_id: string;
  choice: VoteChoice;
};
