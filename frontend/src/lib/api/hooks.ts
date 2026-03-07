"use client";

import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseMutationOptions,
} from "@tanstack/react-query";

import { apiClient } from "@/lib/api/client";
import { queryKeys } from "@/lib/api/query-keys";
import type {
  CastVoteInput,
  CreateCommentInput,
  CreateConversationInput,
  SeedCommentsBulkInput,
  SimulateVotesInput,
  UpdateCommentStatusInput,
  UpdateConversationInput,
} from "@/lib/api/contracts";

export function useConversationsQuery() {
  return useQuery({
    queryKey: queryKeys.conversations,
    queryFn: () => apiClient.listConversations(),
  });
}

export function useConversationQuery(conversationId?: string) {
  return useQuery({
    queryKey: queryKeys.conversation(conversationId ?? ""),
    queryFn: () => apiClient.getConversation(conversationId ?? ""),
    enabled: Boolean(conversationId),
  });
}

export function useCommentsQuery(
  conversationId?: string,
  status?: "pending" | "approved" | "rejected",
) {
  return useQuery({
    queryKey: queryKeys.comments(conversationId ?? "", status),
    queryFn: () => apiClient.listConversationComments(conversationId ?? "", status),
    enabled: Boolean(conversationId),
  });
}

export function useReportQuery(conversationId?: string) {
  return useQuery({
    queryKey: queryKeys.report(conversationId ?? ""),
    queryFn: () => apiClient.getReport(conversationId ?? ""),
    enabled: Boolean(conversationId),
  });
}

export function useCreateConversationMutation(
  options?: UseMutationOptions<
    Awaited<ReturnType<typeof apiClient.createConversation>>,
    Error,
    CreateConversationInput
  >,
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input) => apiClient.createConversation(input),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.conversations });
    },
    ...options,
  });
}

export function useUpdateConversationMutation(conversationId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: UpdateConversationInput) =>
      apiClient.updateConversation(conversationId, input),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.conversation(conversationId) }),
        queryClient.invalidateQueries({ queryKey: queryKeys.conversations }),
      ]);
    },
  });
}

export function useDeleteConversationMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (conversationId: string) => apiClient.deleteConversation(conversationId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.conversations });
    },
  });
}

export function useCreateCommentMutation(conversationId: string, participantId?: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateCommentInput) =>
      apiClient.createComment(conversationId, input, participantId),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: queryKeys.comments(conversationId, "approved"),
        }),
        queryClient.invalidateQueries({
          queryKey: queryKeys.comments(conversationId, "pending"),
        }),
      ]);
    },
  });
}

export function useUpdateCommentStatusMutation(conversationId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ commentId, input }: { commentId: string; input: UpdateCommentStatusInput }) =>
      apiClient.updateCommentStatus(commentId, input),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: queryKeys.comments(conversationId, "approved"),
        }),
        queryClient.invalidateQueries({
          queryKey: queryKeys.comments(conversationId, "pending"),
        }),
      ]);
    },
  });
}

export function useCastVoteMutation(conversationId: string, participantId?: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: CastVoteInput) => apiClient.castVote(input, participantId),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: queryKeys.comments(conversationId, "approved"),
        }),
        queryClient.invalidateQueries({ queryKey: queryKeys.report(conversationId) }),
      ]);
    },
  });
}

export function useSeedCommentsMutation(conversationId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: SeedCommentsBulkInput) =>
      apiClient.seedComments(conversationId, input),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: queryKeys.comments(conversationId, "approved"),
        }),
        queryClient.invalidateQueries({
          queryKey: queryKeys.conversation(conversationId),
        }),
      ]);
    },
  });
}

export function useSimulateVotesMutation(conversationId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: SimulateVotesInput) =>
      apiClient.simulateVotes(conversationId, input),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: queryKeys.comments(conversationId, "approved"),
        }),
        queryClient.invalidateQueries({
          queryKey: queryKeys.report(conversationId),
        }),
      ]);
    },
  });
}

export function useRunAnalysisMutation(conversationId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => apiClient.runAnalysis(conversationId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.report(conversationId) });
    },
  });
}
