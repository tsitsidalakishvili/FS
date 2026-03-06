import axios from "axios";

import { API_BASE_URL } from "./config";
import type { Conversation, ParticipationDeck, VotePayload } from "./types";

const client = axios.create({
  baseURL: API_BASE_URL,
  timeout: 20000,
});

type AuthInput = {
  participantId: string;
  inviteToken?: string;
};

function headers(input: AuthInput) {
  const result: Record<string, string> = {
    "X-Participant-Id": input.participantId,
  };
  if (input.inviteToken) {
    result["X-Invite-Token"] = input.inviteToken;
  }
  return result;
}

export async function fetchParticipationConversations(input: AuthInput): Promise<Conversation[]> {
  const response = await client.get<Conversation[]>("/participation/conversations", {
    headers: headers(input),
  });
  return response.data;
}

export async function fetchConversation(conversationId: string): Promise<Conversation> {
  const response = await client.get<Conversation>(`/conversations/${conversationId}`);
  return response.data;
}

export async function fetchDeck(
  input: AuthInput & { conversationId: string; cursor?: string | null; limit?: number }
): Promise<ParticipationDeck> {
  const params = new URLSearchParams();
  params.set("limit", String(input.limit ?? 20));
  if (input.cursor) {
    params.set("cursor", input.cursor);
  }
  const response = await client.get<ParticipationDeck>(
    `/participation/conversations/${input.conversationId}/deck?${params.toString()}`,
    {
      headers: headers(input),
    }
  );
  return response.data;
}

export async function postVote(input: AuthInput & VotePayload): Promise<void> {
  await client.post(
    "/vote",
    {
      conversation_id: input.conversation_id,
      comment_id: input.comment_id,
      choice: input.choice,
    },
    {
      headers: headers(input),
    }
  );
}

export async function postComment(
  input: AuthInput & {
    conversationId: string;
    text: string;
  }
): Promise<void> {
  await client.post(
    `/conversations/${input.conversationId}/comments`,
    {
      text: input.text,
    },
    {
      headers: headers(input),
    }
  );
}
