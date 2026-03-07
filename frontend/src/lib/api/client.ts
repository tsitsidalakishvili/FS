import { z } from "zod";

import {
  castVoteResponseSchema,
  commentSchema,
  conversationStatusSchema,
  createCommentSchema,
  createConversationSchema,
  deleteConversationResponseSchema,
  reportSchema,
  seedCommentsBulkResponseSchema,
  seedCommentsBulkSchema,
  simulateVotesResponseSchema,
  simulateVotesSchema,
  updateCommentStatusSchema,
  updateConversationSchema,
  type CastVoteInput,
  type CreateCommentInput,
  type CreateConversationInput,
  type SeedCommentsBulkInput,
  type SimulateVotesInput,
  type UpdateCommentStatusInput,
  type UpdateConversationInput,
} from "@/lib/api/contracts";

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

type RequestOptions = {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: unknown;
  headers?: HeadersInit;
};

const API_BASE_URL =
  process.env.NEXT_PUBLIC_DELIBERATION_API_URL?.replace(/\/+$/, "") ??
  "http://localhost:8010";

function toPath(path: string) {
  if (path.startsWith("/")) {
    return path;
  }
  return `/${path}`;
}

async function request<T>(
  path: string,
  schema: z.ZodType<T>,
  options: RequestOptions = {},
): Promise<T> {
  const url = `${API_BASE_URL}${toPath(path)}`;
  const response = await fetch(url, {
    method: options.method ?? "GET",
    headers: {
      "Content-Type": "application/json",
      ...(options.headers ?? {}),
    },
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  });

  const isJson = response.headers.get("content-type")?.includes("application/json");
  const payload = isJson ? await response.json() : null;

  if (!response.ok) {
    const detail =
      payload && typeof payload === "object" && "detail" in payload
        ? String(payload.detail)
        : response.statusText;
    throw new ApiError(detail || "API request failed", response.status);
  }

  const parsed = schema.safeParse(payload ?? {});
  if (!parsed.success) {
    throw new ApiError("Backend response does not match contract", 500);
  }
  return parsed.data;
}

export const apiClient = {
  listConversations() {
    return request("/conversations", z.array(conversationStatusSchema));
  },
  getConversation(conversationId: string) {
    return request(`/conversations/${conversationId}`, conversationStatusSchema);
  },
  createConversation(input: CreateConversationInput) {
    const payload = createConversationSchema.parse(input);
    return request("/conversations", conversationStatusSchema, {
      method: "POST",
      body: payload,
    });
  },
  updateConversation(conversationId: string, input: UpdateConversationInput) {
    const payload = updateConversationSchema.parse(input);
    return request(`/conversations/${conversationId}`, conversationStatusSchema, {
      method: "PATCH",
      body: payload,
    });
  },
  deleteConversation(conversationId: string) {
    return request(
      `/conversations/${conversationId}`,
      deleteConversationResponseSchema,
      { method: "DELETE" },
    );
  },
  listConversationComments(conversationId: string, status?: "pending" | "approved" | "rejected") {
    const query = status ? `?status=${status}` : "";
    return request(
      `/conversations/${conversationId}/comments${query}`,
      z.array(commentSchema),
    );
  },
  createComment(conversationId: string, input: CreateCommentInput, participantId?: string) {
    const payload = createCommentSchema.parse(input);
    return request(`/conversations/${conversationId}/comments`, commentSchema, {
      method: "POST",
      body: payload,
      headers: participantId ? { "X-Participant-Id": participantId } : undefined,
    });
  },
  updateCommentStatus(commentId: string, input: UpdateCommentStatusInput) {
    const payload = updateCommentStatusSchema.parse(input);
    return request(`/comments/${commentId}`, commentSchema, {
      method: "PATCH",
      body: payload,
    });
  },
  castVote(input: CastVoteInput, participantId?: string) {
    return request("/vote", castVoteResponseSchema, {
      method: "POST",
      body: input,
      headers: participantId ? { "X-Participant-Id": participantId } : undefined,
    });
  },
  seedComments(conversationId: string, input: SeedCommentsBulkInput) {
    const payload = seedCommentsBulkSchema.parse(input);
    return request(
      `/conversations/${conversationId}/seed-comments:bulk`,
      seedCommentsBulkResponseSchema,
      { method: "POST", body: payload },
    );
  },
  simulateVotes(conversationId: string, input: SimulateVotesInput) {
    const payload = simulateVotesSchema.parse(input);
    return request(
      `/conversations/${conversationId}/simulate-votes`,
      simulateVotesResponseSchema,
      { method: "POST", body: payload },
    );
  },
  runAnalysis(conversationId: string) {
    return request(`/conversations/${conversationId}/analyze`, reportSchema, {
      method: "POST",
      body: {},
    });
  },
  getReport(conversationId: string) {
    return request(`/conversations/${conversationId}/report`, reportSchema);
  },
};
