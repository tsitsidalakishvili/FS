import { z } from "zod";

export const conversationStatusSchema = z.object({
  id: z.string(),
  topic: z.string(),
  description: z.string().nullable().optional(),
  is_open: z.boolean(),
  allow_comment_submission: z.boolean(),
  allow_viz: z.boolean(),
  moderation_required: z.boolean(),
  created_at: z.string().nullable().optional(),
  comments: z.number().int().nullable().optional(),
  participants: z.number().int().nullable().optional(),
});

export const createConversationSchema = z.object({
  topic: z.string().min(3),
  description: z.string().optional(),
  is_open: z.boolean().default(true),
  allow_comment_submission: z.boolean().default(true),
  allow_viz: z.boolean().default(true),
  moderation_required: z.boolean().default(false),
});

export const updateConversationSchema = z.object({
  topic: z.string().optional(),
  description: z.string().optional(),
  is_open: z.boolean().optional(),
  allow_comment_submission: z.boolean().optional(),
  allow_viz: z.boolean().optional(),
  moderation_required: z.boolean().optional(),
});

export const commentStatusEnum = z.enum(["pending", "approved", "rejected"]);

export const commentSchema = z.object({
  id: z.string(),
  text: z.string(),
  status: commentStatusEnum,
  is_seed: z.boolean(),
  created_at: z.string().nullable().optional(),
  author_hash: z.string().nullable().optional(),
  agree_count: z.number().int(),
  disagree_count: z.number().int(),
  pass_count: z.number().int(),
});

export const createCommentSchema = z.object({
  text: z.string().min(2),
  author_id: z.string().optional(),
});

export const updateCommentStatusSchema = z.object({
  status: commentStatusEnum,
});

export const castVoteSchema = z.object({
  conversation_id: z.string(),
  comment_id: z.string(),
  choice: z.union([z.literal(-1), z.literal(0), z.literal(1)]),
  participant_id: z.string().optional(),
});

export const castVoteResponseSchema = z.object({
  participant_id: z.string(),
  comment_id: z.string(),
  choice: z.union([z.literal(-1), z.literal(0), z.literal(1)]),
});

export const seedCommentsBulkSchema = z.object({
  comments: z.array(z.string()),
});

export const seedCommentsBulkResponseSchema = z.object({
  created: z.number().int(),
});

export const simulateVotesSchema = z.object({
  participants: z.number().int().min(1).max(1000),
  votes_per_participant: z.number().int().min(1).max(200),
  seed: z.number().int().optional(),
});

export const simulateVotesResponseSchema = z.object({
  participants: z.number().int(),
  votes_per_participant: z.number().int(),
  generated_votes: z.number().int(),
});

export const commentMetricSchema = z.object({
  id: z.string(),
  text: z.string(),
  participation: z.number().int(),
  agreement_ratio: z.number(),
  consensus_score: z.number(),
  polarity_score: z.number(),
  agree_count: z.number().int(),
  disagree_count: z.number().int(),
  pass_count: z.number().int(),
  status: z.string(),
});

export const metricsSchema = z.object({
  total_comments: z.number().int(),
  total_participants: z.number().int(),
  total_votes: z.number().int(),
  consensus: z.array(commentMetricSchema),
  polarizing: z.array(commentMetricSchema),
});

export const clusterPointSchema = z.object({
  participant_id: z.string(),
  x: z.number(),
  y: z.number(),
  cluster_id: z.string(),
});

export const clusterSummarySchema = z.object({
  cluster_id: z.string(),
  size: z.number().int(),
  top_agree: z.array(z.string()),
  top_disagree: z.array(z.string()),
});

export const clusterSimilaritySchema = z.object({
  cluster_a: z.string(),
  cluster_b: z.string(),
  similarity: z.number(),
});

export const reportSchema = z.object({
  metrics: metricsSchema,
  clusters: z.array(z.string()),
  points: z.array(clusterPointSchema),
  cluster_summaries: z.array(clusterSummarySchema),
  cluster_similarity: z.array(clusterSimilaritySchema),
  potential_agreements: z.array(z.string()),
});

export const deleteConversationResponseSchema = z.object({
  deleted: z.boolean(),
  conversation_id: z.string(),
});

export type Conversation = z.infer<typeof conversationStatusSchema>;
export type CreateConversationInput = z.infer<typeof createConversationSchema>;
export type UpdateConversationInput = z.infer<typeof updateConversationSchema>;
export type Comment = z.infer<typeof commentSchema>;
export type CreateCommentInput = z.infer<typeof createCommentSchema>;
export type UpdateCommentStatusInput = z.infer<typeof updateCommentStatusSchema>;
export type CastVoteInput = z.infer<typeof castVoteSchema>;
export type CastVoteResponse = z.infer<typeof castVoteResponseSchema>;
export type SeedCommentsBulkInput = z.infer<typeof seedCommentsBulkSchema>;
export type SeedCommentsBulkResponse = z.infer<typeof seedCommentsBulkResponseSchema>;
export type SimulateVotesInput = z.infer<typeof simulateVotesSchema>;
export type SimulateVotesResponse = z.infer<typeof simulateVotesResponseSchema>;
export type Report = z.infer<typeof reportSchema>;
