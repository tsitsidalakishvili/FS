import { StatusBar } from "expo-status-bar";
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Pressable,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { GestureHandlerRootView } from "react-native-gesture-handler";
import { useNetInfo } from "@react-native-community/netinfo";
import { QueryClient, QueryClientProvider, useQuery } from "@tanstack/react-query";
import axios from "axios";

import { fetchConversation, fetchDeck, fetchParticipationConversations, postComment, postVote } from "./src/api";
import { SwipeCard } from "./src/components/SwipeCard";
import { enqueueVote, getOrCreateParticipantId, initVoteQueue, listQueuedVotes, removeQueuedVote } from "./src/storage";
import type { Comment, VoteChoice, VotePayload } from "./src/types";
import { API_BASE_URL } from "./src/config";

const queryClient = new QueryClient();

function toErrorText(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") {
      return detail;
    }
    if (error.message) {
      return error.message;
    }
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Unknown error";
}

function ParticipateScreen() {
  const netInfo = useNetInfo();
  const isOnline = !!netInfo.isConnected && netInfo.isInternetReachable !== false;

  const [participantId, setParticipantId] = useState<string>("");
  const [inviteToken, setInviteToken] = useState<string>("");
  const [selectedConversationId, setSelectedConversationId] = useState<string>("");
  const [started, setStarted] = useState<boolean>(false);

  const [deckComments, setDeckComments] = useState<Comment[]>([]);
  const [deckCursor, setDeckCursor] = useState<string | null>(null);
  const [deckHasMore, setDeckHasMore] = useState<boolean>(true);
  const [deckLoading, setDeckLoading] = useState<boolean>(false);
  const [deckError, setDeckError] = useState<string>("");

  const [queuedCount, setQueuedCount] = useState<number>(0);
  const [commentDraft, setCommentDraft] = useState<string>("");
  const [commentSubmitting, setCommentSubmitting] = useState<boolean>(false);

  const votedInSessionRef = useRef<Set<string>>(new Set());

  const authInput = useMemo(
    () => ({
      participantId,
      inviteToken: inviteToken.trim() || undefined,
    }),
    [inviteToken, participantId]
  );

  const conversationsQuery = useQuery({
    queryKey: ["participation-conversations", authInput.participantId, authInput.inviteToken],
    queryFn: () => fetchParticipationConversations(authInput),
    enabled: !!participantId,
  });

  const conversationQuery = useQuery({
    queryKey: ["conversation-details", selectedConversationId],
    queryFn: () => fetchConversation(selectedConversationId),
    enabled: started && !!selectedConversationId,
  });

  const refreshQueuedCount = useCallback(async () => {
    const queued = await listQueuedVotes();
    setQueuedCount(queued.length);
  }, []);

  const flushVoteQueue = useCallback(async () => {
    if (!isOnline || !participantId) {
      await refreshQueuedCount();
      return;
    }
    const queued = await listQueuedVotes();
    for (let i = 0; i < queued.length; i += 1) {
      const item = queued[i];
      try {
        await postVote({
          participantId,
          inviteToken: authInput.inviteToken,
          conversation_id: item.conversation_id,
          comment_id: item.comment_id,
          choice: item.choice,
        });
        await removeQueuedVote(item.queue_key);
      } catch {
        break;
      }
    }
    await refreshQueuedCount();
  }, [authInput.inviteToken, isOnline, participantId, refreshQueuedCount]);

  const fetchNextDeckPage = useCallback(
    async (options?: { force?: boolean; cursorOverride?: string | null }) => {
      const force = options?.force ?? false;
      const effectiveCursor = options?.cursorOverride ?? deckCursor;
      if (!selectedConversationId || !participantId || deckLoading || (!deckHasMore && !force)) {
        return;
      }
      if (!isOnline) {
        setDeckError("You are offline. Queued votes will sync when you reconnect.");
        return;
      }
      setDeckLoading(true);
      setDeckError("");
      try {
        const payload = await fetchDeck({
          participantId,
          inviteToken: authInput.inviteToken,
          conversationId: selectedConversationId,
          cursor: effectiveCursor,
          limit: 20,
        });
        const fresh = payload.comments.filter((comment) => !votedInSessionRef.current.has(comment.id));
        setDeckComments((prev) => [...prev, ...fresh]);
        setDeckCursor(payload.next_cursor ?? null);
        setDeckHasMore(payload.has_more);
      } catch (error) {
        setDeckError(toErrorText(error));
      } finally {
        setDeckLoading(false);
      }
    },
    [
      authInput.inviteToken,
      deckCursor,
      deckHasMore,
      deckLoading,
      isOnline,
      participantId,
      selectedConversationId,
    ]
  );

  useEffect(() => {
    (async () => {
      await initVoteQueue();
      const id = await getOrCreateParticipantId();
      setParticipantId(id);
      await refreshQueuedCount();
    })();
  }, [refreshQueuedCount]);

  useEffect(() => {
    const timer = setInterval(() => {
      flushVoteQueue().catch(() => null);
    }, 10000);
    return () => clearInterval(timer);
  }, [flushVoteQueue]);

  useEffect(() => {
    if (isOnline) {
      flushVoteQueue().catch(() => null);
    }
  }, [flushVoteQueue, isOnline]);

  useEffect(() => {
    if (!started || !selectedConversationId) {
      return;
    }
    if (deckComments.length < 6 && deckHasMore && !deckLoading) {
      fetchNextDeckPage().catch(() => null);
    }
  }, [deckComments.length, deckHasMore, deckLoading, fetchNextDeckPage, selectedConversationId, started]);

  const currentComment = deckComments[0] ?? null;

  const startDeck = async () => {
    if (!selectedConversationId) {
      return;
    }
    votedInSessionRef.current = new Set();
    setDeckComments([]);
    setDeckCursor(null);
    setDeckHasMore(true);
    setDeckError("");
    setStarted(true);
    await fetchNextDeckPage({ force: true, cursorOverride: null });
  };

  const handleVote = async (choice: VoteChoice) => {
    if (!currentComment || !selectedConversationId) {
      return;
    }
    const payload: VotePayload = {
      conversation_id: selectedConversationId,
      comment_id: currentComment.id,
      choice,
    };
    votedInSessionRef.current.add(currentComment.id);
    setDeckComments((prev) => prev.slice(1));
    await enqueueVote(payload);
    await refreshQueuedCount();
    flushVoteQueue().catch(() => null);
  };

  const submitComment = async () => {
    if (!selectedConversationId || !participantId) {
      return;
    }
    const text = commentDraft.trim();
    if (text.length < 3) {
      Alert.alert("Comment too short", "Please enter at least 3 characters.");
      return;
    }
    setCommentSubmitting(true);
    try {
      await postComment({
        participantId,
        inviteToken: authInput.inviteToken,
        conversationId: selectedConversationId,
        text,
      });
      setCommentDraft("");
      Alert.alert("Comment submitted", "Thank you for contributing.");
    } catch (error) {
      Alert.alert("Could not submit comment", toErrorText(error));
    } finally {
      setCommentSubmitting(false);
    }
  };

  if (!participantId) {
    return (
      <SafeAreaView style={styles.screen}>
        <View style={styles.centered}>
          <ActivityIndicator color="#38bdf8" />
          <Text style={styles.muted}>Preparing your anonymous session…</Text>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.screen}>
      <StatusBar style="light" />
      <ScrollView contentContainerStyle={styles.content}>
        <Text style={styles.title}>Deliberation Participate</Text>
        <Text style={styles.subtitle}>Swipe right = Agree, left = Disagree, up/tap = Pass</Text>
        <Text style={styles.meta}>API: {API_BASE_URL}</Text>
        <Text style={styles.meta}>
          Status: {isOnline ? "Online" : "Offline"} • queued votes: {queuedCount}
        </Text>

        <View style={styles.panel}>
          <Text style={styles.label}>Invite token (optional)</Text>
          <TextInput
            style={styles.input}
            value={inviteToken}
            onChangeText={setInviteToken}
            autoCapitalize="none"
            autoCorrect={false}
            placeholder="Paste invite token when required"
            placeholderTextColor="#64748b"
          />
          <Pressable
            style={styles.refreshButton}
            onPress={() => {
              setStarted(false);
              setSelectedConversationId("");
              conversationsQuery.refetch().catch(() => null);
            }}
          >
            <Text style={styles.refreshButtonText}>Reload conversations</Text>
          </Pressable>
        </View>

        <View style={styles.panel}>
          <Text style={styles.sectionTitle}>1) Pick conversation</Text>
          {conversationsQuery.isLoading ? (
            <ActivityIndicator color="#38bdf8" />
          ) : conversationsQuery.isError ? (
            <Text style={styles.errorText}>{toErrorText(conversationsQuery.error)}</Text>
          ) : (
            <View style={styles.list}>
              {(conversationsQuery.data ?? []).map((conversation) => {
                const isSelected = conversation.id === selectedConversationId;
                return (
                  <Pressable
                    key={conversation.id}
                    style={[styles.listItem, isSelected && styles.listItemSelected]}
                    onPress={() => {
                      setStarted(false);
                      setSelectedConversationId(conversation.id);
                    }}
                  >
                    <Text style={[styles.listTitle, isSelected && styles.listTitleSelected]}>
                      {conversation.topic}
                    </Text>
                    {!!conversation.description && (
                      <Text style={styles.listDescription}>{conversation.description}</Text>
                    )}
                  </Pressable>
                );
              })}
            </View>
          )}
          <Pressable
            style={[styles.primaryButton, !selectedConversationId && styles.disabledButton]}
            disabled={!selectedConversationId}
            onPress={() => {
              startDeck().catch((error) => Alert.alert("Could not start deck", toErrorText(error)));
            }}
          >
            <Text style={styles.primaryButtonText}>Start swiping</Text>
          </Pressable>
        </View>

        {started && (
          <View style={styles.panel}>
            <Text style={styles.sectionTitle}>2) Vote deck</Text>
            <Text style={styles.deckMeta}>
              {conversationQuery.data?.topic ?? "Selected conversation"}
            </Text>
            {!!conversationQuery.data?.description && (
              <Text style={styles.deckMetaMuted}>{conversationQuery.data.description}</Text>
            )}
            {!!deckError && <Text style={styles.errorText}>{deckError}</Text>}

            {currentComment ? (
              <>
                <SwipeCard comment={currentComment} onVote={handleVote} />
                <View style={styles.voteButtons}>
                  <Pressable style={[styles.voteButton, styles.disagree]} onPress={() => handleVote(-1)}>
                    <Text style={styles.voteButtonText}>Disagree</Text>
                  </Pressable>
                  <Pressable style={[styles.voteButton, styles.pass]} onPress={() => handleVote(0)}>
                    <Text style={styles.voteButtonText}>Pass</Text>
                  </Pressable>
                  <Pressable style={[styles.voteButton, styles.agree]} onPress={() => handleVote(1)}>
                    <Text style={styles.voteButtonText}>Agree</Text>
                  </Pressable>
                </View>
              </>
            ) : deckLoading ? (
              <View style={styles.centered}>
                <ActivityIndicator color="#38bdf8" />
                <Text style={styles.muted}>Loading next comments…</Text>
              </View>
            ) : (
              <Text style={styles.muted}>No more comments currently available.</Text>
            )}
          </View>
        )}

        {started && conversationQuery.data?.allow_comment_submission && (
          <View style={styles.panel}>
            <Text style={styles.sectionTitle}>3) Optional comment</Text>
            <TextInput
              style={[styles.input, styles.commentInput]}
              multiline
              value={commentDraft}
              onChangeText={setCommentDraft}
              placeholder="Share your perspective (anonymous)"
              placeholderTextColor="#64748b"
            />
            <Pressable
              style={[styles.primaryButton, commentSubmitting && styles.disabledButton]}
              disabled={commentSubmitting}
              onPress={() => {
                submitComment().catch(() => null);
              }}
            >
              <Text style={styles.primaryButtonText}>
                {commentSubmitting ? "Submitting..." : "Submit comment"}
              </Text>
            </Pressable>
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

export default function App() {
  return (
    <GestureHandlerRootView style={styles.root}>
      <QueryClientProvider client={queryClient}>
        <ParticipateScreen />
      </QueryClientProvider>
    </GestureHandlerRootView>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
  },
  screen: {
    flex: 1,
    backgroundColor: "#0b1220",
  },
  content: {
    padding: 16,
    paddingBottom: 28,
    gap: 12,
  },
  title: {
    color: "#f8fafc",
    fontSize: 28,
    fontWeight: "800",
  },
  subtitle: {
    color: "#94a3b8",
    marginTop: 4,
  },
  meta: {
    color: "#64748b",
    fontSize: 12,
  },
  panel: {
    borderColor: "#1f2937",
    borderWidth: 1,
    borderRadius: 14,
    backgroundColor: "#111827",
    padding: 12,
    gap: 10,
  },
  sectionTitle: {
    color: "#e5e7eb",
    fontSize: 18,
    fontWeight: "700",
  },
  label: {
    color: "#e2e8f0",
    fontSize: 14,
  },
  input: {
    borderColor: "#334155",
    borderWidth: 1,
    borderRadius: 10,
    backgroundColor: "#0f172a",
    color: "#e2e8f0",
    paddingHorizontal: 12,
    paddingVertical: 10,
  },
  commentInput: {
    minHeight: 110,
    textAlignVertical: "top",
  },
  refreshButton: {
    alignSelf: "flex-start",
    backgroundColor: "#1e293b",
    borderRadius: 8,
    paddingHorizontal: 10,
    paddingVertical: 8,
  },
  refreshButtonText: {
    color: "#cbd5e1",
    fontWeight: "600",
  },
  list: {
    gap: 8,
  },
  listItem: {
    borderRadius: 10,
    borderWidth: 1,
    borderColor: "#334155",
    backgroundColor: "#0f172a",
    padding: 10,
    gap: 4,
  },
  listItemSelected: {
    borderColor: "#38bdf8",
    backgroundColor: "#082f49",
  },
  listTitle: {
    color: "#e2e8f0",
    fontWeight: "700",
  },
  listTitleSelected: {
    color: "#e0f2fe",
  },
  listDescription: {
    color: "#94a3b8",
    fontSize: 12,
  },
  primaryButton: {
    borderRadius: 10,
    backgroundColor: "#2563eb",
    paddingVertical: 12,
    alignItems: "center",
  },
  primaryButtonText: {
    color: "#ffffff",
    fontWeight: "700",
    fontSize: 16,
  },
  disabledButton: {
    opacity: 0.6,
  },
  centered: {
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    paddingVertical: 20,
  },
  muted: {
    color: "#94a3b8",
  },
  deckMeta: {
    color: "#f1f5f9",
    fontWeight: "700",
  },
  deckMetaMuted: {
    color: "#94a3b8",
    fontSize: 12,
  },
  errorText: {
    color: "#fca5a5",
  },
  voteButtons: {
    flexDirection: "row",
    gap: 8,
    marginTop: 10,
  },
  voteButton: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 10,
    paddingVertical: 11,
  },
  voteButtonText: {
    color: "#f8fafc",
    fontWeight: "700",
  },
  disagree: {
    backgroundColor: "#b91c1c",
  },
  pass: {
    backgroundColor: "#475569",
  },
  agree: {
    backgroundColor: "#059669",
  },
});
