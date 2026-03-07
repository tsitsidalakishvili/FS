"use client";

import { useParams } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/states";
import { useCommentsQuery, useUpdateCommentStatusMutation } from "@/lib/api/hooks";

export default function ModeratePage() {
  const params = useParams<{ conversationId: string }>();
  const conversationId = params.conversationId;
  const pendingQuery = useCommentsQuery(conversationId, "pending");
  const updateStatus = useUpdateCommentStatusMutation(conversationId);

  if (pendingQuery.isLoading) {
    return <LoadingState label="Loading pending comments..." />;
  }
  if (pendingQuery.isError) {
    return (
      <ErrorState
        title="Could not load moderation queue"
        detail={pendingQuery.error.message}
      />
    );
  }

  const pendingComments = pendingQuery.data ?? [];
  if (pendingComments.length === 0) {
    return (
      <EmptyState
        title="No pending comments"
        detail="All submitted comments are already moderated."
      />
    );
  }

  return (
    <section className="space-y-4">
      <header>
        <h2 className="text-2xl font-semibold text-slate-900">Moderation queue</h2>
        <p className="text-sm text-slate-600">Approve or reject pending participant comments.</p>
      </header>

      <ul className="space-y-3">
        {pendingComments.map((comment) => (
          <li key={comment.id}>
            <Card className="space-y-3">
              <p className="text-slate-900">{comment.text}</p>
              <div className="flex flex-wrap gap-2">
                <Button
                  type="button"
                  variant="secondary"
                  disabled={updateStatus.isPending}
                  onClick={() =>
                    updateStatus.mutate({
                      commentId: comment.id,
                      input: { status: "approved" },
                    })
                  }
                >
                  Approve
                </Button>
                <Button
                  type="button"
                  variant="danger"
                  disabled={updateStatus.isPending}
                  onClick={() =>
                    updateStatus.mutate({
                      commentId: comment.id,
                      input: { status: "rejected" },
                    })
                  }
                >
                  Reject
                </Button>
              </div>
            </Card>
          </li>
        ))}
      </ul>

      {updateStatus.isError ? (
        <ErrorState title="Moderation action failed" detail={updateStatus.error.message} />
      ) : null}
    </section>
  );
}
