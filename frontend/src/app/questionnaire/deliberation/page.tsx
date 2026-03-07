"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/states";
import {
  useCastVoteMutation,
  useCommentsQuery,
  useConversationQuery,
  useCreateCommentMutation,
} from "@/lib/api/hooks";
import { useParticipantId } from "@/lib/use-participant-id";

function DeliberationQuestionnaireContent() {
  const searchParams = useSearchParams();
  const conversationId =
    searchParams.get("conversation_id") ??
    searchParams.get("conversation") ??
    searchParams.get("id") ??
    "";
  const participantId = useParticipantId();
  const conversationQuery = useConversationQuery(conversationId);
  const commentsQuery = useCommentsQuery(conversationId, "approved");
  const voteMutation = useCastVoteMutation(conversationId, participantId);
  const createCommentMutation = useCreateCommentMutation(conversationId, participantId);
  const [progressByConversation, setProgressByConversation] = useState<Record<string, number>>(
    {},
  );
  const [commentDraft, setCommentDraft] = useState("");
  const [commentNotice, setCommentNotice] = useState<"pending" | "approved" | null>(null);

  const comments = commentsQuery.data ?? [];
  const index = Math.min(
    progressByConversation[conversationId] ?? 0,
    Math.max(comments.length - 1, 0),
  );
  const currentComment = comments[index];

  if (!conversationId) {
    return (
      <EmptyState
        title="Missing conversation id"
        detail="Use ?conversation_id=<id> in the questionnaire link."
      />
    );
  }
  if (conversationQuery.isLoading || commentsQuery.isLoading) {
    return <LoadingState label="Loading questionnaire..." />;
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
    return (
      <ErrorState title="Could not load questions" detail={commentsQuery.error.message} />
    );
  }
  if (!conversationQuery.data) {
    return <EmptyState title="Conversation not found" detail="Check the questionnaire URL." />;
  }
  if (comments.length === 0) {
    return (
      <EmptyState
        title="No approved statements yet"
        detail="Ask an admin to seed or approve comments first."
      />
    );
  }

  async function voteAndAdvance(choice: -1 | 0 | 1) {
    if (!currentComment) {
      return;
    }
    await voteMutation.mutateAsync({
      conversation_id: conversationId,
      comment_id: currentComment.id,
      choice,
    });
    setProgressByConversation((current) => ({
      ...current,
      [conversationId]: Math.min((current[conversationId] ?? 0) + 1, comments.length - 1),
    }));
  }

  const completed = index >= comments.length - 1;

  return (
    <section className="mx-auto max-w-xl space-y-4">
      <header className="space-y-1 text-center">
        <h2 className="text-xl font-semibold text-slate-900">
          {conversationQuery.data.topic}
        </h2>
        <p className="text-sm text-slate-600">
          Question {Math.min(index + 1, comments.length)} of {comments.length}
        </p>
      </header>

      <Card className="space-y-4">
        <p className="text-lg text-slate-900">{currentComment?.text}</p>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
          <Button
            type="button"
            variant="secondary"
            disabled={voteMutation.isPending || !conversationQuery.data.is_open}
            onClick={() => voteAndAdvance(1)}
          >
            Agree
          </Button>
          <Button
            type="button"
            variant="secondary"
            disabled={voteMutation.isPending || !conversationQuery.data.is_open}
            onClick={() => voteAndAdvance(-1)}
          >
            Disagree
          </Button>
          <Button
            type="button"
            variant="secondary"
            disabled={voteMutation.isPending || !conversationQuery.data.is_open}
            onClick={() => voteAndAdvance(0)}
          >
            Pass
          </Button>
        </div>
        {voteMutation.isError ? (
          <p className="text-sm text-red-700">{voteMutation.error.message}</p>
        ) : null}
        {completed ? (
          <p className="text-sm text-emerald-700">
            You reached the final statement. You can still review and vote again.
          </p>
        ) : null}
      </Card>

      {conversationQuery.data.allow_comment_submission ? (
        <Card>
          <h3 className="mb-2 text-base font-semibold text-slate-900">Add anonymous comment</h3>
          <form
            className="space-y-3"
            onSubmit={async (event) => {
              event.preventDefault();
              const created = await createCommentMutation.mutateAsync({
                text: commentDraft.trim(),
              });
              setCommentNotice(created.status === "pending" ? "pending" : "approved");
              setCommentDraft("");
            }}
          >
            <Textarea
              minLength={2}
              required
              value={commentDraft}
              onChange={(event) => setCommentDraft(event.target.value)}
              rows={3}
            />
            <Button
              type="submit"
              disabled={
                createCommentMutation.isPending || commentDraft.trim().length < 2
              }
            >
              Submit anonymous comment
            </Button>
          </form>
          {createCommentMutation.isError ? (
            <p className="mt-2 text-sm text-red-700">{createCommentMutation.error.message}</p>
          ) : null}
          {commentNotice === "pending" ? (
            <p className="mt-2 text-sm text-blue-700">
              Comment submitted and waiting for moderation.
            </p>
          ) : null}
          {commentNotice === "approved" ? (
            <p className="mt-2 text-sm text-emerald-700">
              Comment submitted and visible in the feed.
            </p>
          ) : null}
        </Card>
      ) : null}
    </section>
  );
}

export default function DeliberationQuestionnairePage() {
  return (
    <Suspense fallback={<LoadingState label="Loading questionnaire..." />}>
      <DeliberationQuestionnaireContent />
    </Suspense>
  );
}
