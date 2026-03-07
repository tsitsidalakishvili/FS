"use client";

import { useParams } from "next/navigation";
import { useState } from "react";

import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { VoteButtonGroup } from "@/components/vote-button-group";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/states";
import {
  useCastVoteMutation,
  useCommentsQuery,
  useConversationQuery,
  useCreateCommentMutation,
} from "@/lib/api/hooks";
import { useParticipantId } from "@/lib/use-participant-id";

export default function ParticipatePage() {
  const params = useParams<{ conversationId: string }>();
  const conversationId = params.conversationId;
  const participantId = useParticipantId();
  const conversationQuery = useConversationQuery(conversationId);
  const commentsQuery = useCommentsQuery(conversationId, "approved");
  const voteMutation = useCastVoteMutation(conversationId, participantId);
  const createCommentMutation = useCreateCommentMutation(conversationId, participantId);
  const [newComment, setNewComment] = useState("");
  const [commentNotice, setCommentNotice] = useState<"pending" | "approved" | null>(null);

  if (conversationQuery.isLoading || commentsQuery.isLoading) {
    return <LoadingState label="Loading participation feed..." />;
  }
  if (conversationQuery.isError) {
    return (
      <ErrorState
        title="Could not load conversation"
        detail={conversationQuery.error.message}
      />
    );
  }
  if (commentsQuery.isError) {
    return <ErrorState title="Could not load comments" detail={commentsQuery.error.message} />;
  }

  const conversation = conversationQuery.data;
  const comments = commentsQuery.data ?? [];
  if (!conversation) {
    return (
      <EmptyState
        title="Conversation not found"
        detail="Select another conversation from the main list."
      />
    );
  }

  return (
    <section className="space-y-4">
      <header className="space-y-1">
        <h2 className="text-2xl font-semibold text-slate-900">{conversation.topic}</h2>
        <p className="text-sm text-slate-600">{conversation.description || "No description."}</p>
        {!conversation.is_open ? (
          <p className="text-sm font-medium text-amber-700">This conversation is closed.</p>
        ) : null}
      </header>

      {comments.length === 0 ? (
        <EmptyState
          title="No approved comments yet"
          detail="Seed comments from Configure or wait for moderation approval."
        />
      ) : (
        <ul className="space-y-3">
          {comments.map((comment) => (
            <li key={comment.id}>
              <Card className="space-y-3">
                <p className="text-base text-slate-900">{comment.text}</p>
                <p className="text-sm text-slate-600">
                  Agree: {comment.agree_count} · Disagree: {comment.disagree_count} · Pass:{" "}
                  {comment.pass_count}
                </p>
                <VoteButtonGroup
                  disabled={!conversation.is_open || voteMutation.isPending}
                  onVote={(choice) =>
                    voteMutation.mutate({
                      conversation_id: conversationId,
                      comment_id: comment.id,
                      choice,
                    })
                  }
                />
              </Card>
            </li>
          ))}
        </ul>
      )}

      {voteMutation.isError ? (
        <ErrorState title="Vote failed" detail={voteMutation.error.message} />
      ) : null}

      {conversation.allow_comment_submission ? (
        <Card>
          <h3 className="mb-2 text-lg font-semibold text-slate-900">Submit comment</h3>
          <form
            className="space-y-3"
            onSubmit={async (event) => {
              event.preventDefault();
              const created = await createCommentMutation.mutateAsync({
                text: newComment.trim(),
              });
              setCommentNotice(created.status === "pending" ? "pending" : "approved");
              setNewComment("");
            }}
          >
            <label className="block text-sm">
              <span className="mb-1 block font-medium text-slate-800">Your comment</span>
              <Textarea
                required
                minLength={2}
                value={newComment}
                rows={4}
                onChange={(event) => setNewComment(event.target.value)}
                placeholder="Share your perspective..."
              />
            </label>
            <Button
              type="submit"
              disabled={
                createCommentMutation.isPending ||
                !conversation.is_open ||
                newComment.trim().length < 2
              }
            >
              {createCommentMutation.isPending ? "Submitting..." : "Submit comment"}
            </Button>
          </form>

          {createCommentMutation.isError ? (
            <p className="mt-2 text-sm text-red-700" role="alert">
              {createCommentMutation.error.message}
            </p>
          ) : null}
          {commentNotice === "pending" ? (
            <p className="mt-2 text-sm text-blue-700">
              Comment submitted. Awaiting moderation before it appears.
            </p>
          ) : null}
          {commentNotice === "approved" ? (
            <p className="mt-2 text-sm text-emerald-700">Comment submitted and added.</p>
          ) : null}
        </Card>
      ) : (
        <Card>
          <p className="text-sm text-slate-600">Comment submission is disabled for this conversation.</p>
        </Card>
      )}
    </section>
  );
}
