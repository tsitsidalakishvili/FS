export const queryKeys = {
  conversations: ["conversations"] as const,
  conversation: (conversationId: string) =>
    ["conversations", conversationId] as const,
  comments: (conversationId: string, status?: string) =>
    ["comments", conversationId, status ?? "all"] as const,
  pendingComments: (conversationId: string) =>
    ["comments", conversationId, "pending"] as const,
  report: (conversationId: string) => ["report", conversationId] as const,
};
