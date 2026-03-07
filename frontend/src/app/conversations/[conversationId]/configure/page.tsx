"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/states";
import {
  useConversationQuery,
  useDeleteConversationMutation,
  useSeedCommentsMutation,
  useSimulateVotesMutation,
  useUpdateConversationMutation,
} from "@/lib/api/hooks";

export default function ConfigureConversationPage() {
  const params = useParams<{ conversationId: string }>();
  const conversationId = params.conversationId;
  const router = useRouter();

  const conversationQuery = useConversationQuery(conversationId);
  const updateConversation = useUpdateConversationMutation(conversationId);
  const seedComments = useSeedCommentsMutation(conversationId);
  const simulateVotes = useSimulateVotesMutation(conversationId);
  const deleteConversation = useDeleteConversationMutation();

  const [seedText, setSeedText] = useState("");
  const [participants, setParticipants] = useState(120);
  const [votesPerParticipant, setVotesPerParticipant] = useState(20);
  const [seed, setSeed] = useState(42);

  const seedItems = useMemo(
    () =>
      seedText
        .split("\n")
        .map((line) => line.trim())
        .filter(Boolean),
    [seedText],
  );

  if (conversationQuery.isLoading) {
    return <LoadingState label="Loading conversation settings..." />;
  }
  if (conversationQuery.isError) {
    return (
      <ErrorState
        title="Could not load conversation"
        detail={conversationQuery.error.message}
      />
    );
  }
  if (!conversationQuery.data) {
    return (
      <EmptyState
        title="Conversation not found"
        detail="Return to the conversation list and choose a valid conversation."
      />
    );
  }

  return (
    <section className="space-y-4">
      <header>
        <h2 className="text-2xl font-semibold text-slate-900">Configure conversation</h2>
        <p className="text-sm text-slate-600">
          Manage conversation settings, seed comments, and generate demo votes.
        </p>
      </header>

      <Card>
        <form
          className="space-y-4"
          onSubmit={(event) => {
            event.preventDefault();
            const formData = new FormData(event.currentTarget);
            updateConversation.mutate({
              topic: String(formData.get("topic") ?? "").trim(),
              description: String(formData.get("description") ?? "").trim(),
              is_open: formData.get("is_open") === "on",
              allow_comment_submission:
                formData.get("allow_comment_submission") === "on",
              allow_viz: formData.get("allow_viz") === "on",
              moderation_required: formData.get("moderation_required") === "on",
            });
          }}
        >
          <label className="block text-sm">
            <span className="mb-1 block font-medium text-slate-800">Topic</span>
            <Input name="topic" defaultValue={conversationQuery.data.topic} minLength={3} />
          </label>
          <label className="block text-sm">
            <span className="mb-1 block font-medium text-slate-800">Description</span>
            <Textarea
              name="description"
              defaultValue={conversationQuery.data.description ?? ""}
              rows={4}
            />
          </label>

          <div className="grid gap-3 sm:grid-cols-2">
            <label className="flex items-center gap-2 text-sm text-slate-800">
              <input
                type="checkbox"
                name="is_open"
                defaultChecked={conversationQuery.data.is_open}
              />
              Open for participation
            </label>
            <label className="flex items-center gap-2 text-sm text-slate-800">
              <input
                type="checkbox"
                name="allow_comment_submission"
                defaultChecked={conversationQuery.data.allow_comment_submission}
              />
              Allow participant comments
            </label>
            <label className="flex items-center gap-2 text-sm text-slate-800">
              <input
                type="checkbox"
                name="allow_viz"
                defaultChecked={conversationQuery.data.allow_viz}
              />
              Allow visualization
            </label>
            <label className="flex items-center gap-2 text-sm text-slate-800">
              <input
                type="checkbox"
                name="moderation_required"
                defaultChecked={conversationQuery.data.moderation_required}
              />
              Moderation required
            </label>
          </div>

          <Button type="submit" disabled={updateConversation.isPending}>
            {updateConversation.isPending ? "Saving..." : "Save settings"}
          </Button>
          {updateConversation.isError ? (
            <p className="text-sm text-red-700" role="alert">
              {updateConversation.error.message}
            </p>
          ) : null}
          {updateConversation.isSuccess ? (
            <p className="text-sm text-emerald-700">Conversation updated.</p>
          ) : null}
        </form>
      </Card>

      <Card>
        <h3 className="text-lg font-semibold text-slate-900">Seed comments (bulk)</h3>
        <p className="mb-3 text-sm text-slate-600">One comment per line.</p>
        <Textarea
          value={seedText}
          onChange={(event) => setSeedText(event.target.value)}
          rows={5}
          placeholder={"First statement\nSecond statement"}
        />
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <Button
            type="button"
            variant="secondary"
            disabled={seedComments.isPending || seedItems.length === 0}
            onClick={() => seedComments.mutate({ comments: seedItems })}
          >
            {seedComments.isPending ? "Adding..." : "Add seed comments"}
          </Button>
          {seedComments.isSuccess ? (
            <p className="text-sm text-emerald-700">
              Added {seedComments.data.created} comments.
            </p>
          ) : null}
          {seedComments.isError ? (
            <p className="text-sm text-red-700" role="alert">
              {seedComments.error.message}
            </p>
          ) : null}
        </div>
      </Card>

      <Card>
        <h3 className="text-lg font-semibold text-slate-900">Generate demo votes</h3>
        <p className="mb-3 text-sm text-slate-600">
          Fill reports quickly when participation is still low.
        </p>
        <div className="grid gap-3 sm:grid-cols-3">
          <label className="text-sm">
            <span className="mb-1 block font-medium text-slate-800">Participants</span>
            <Input
              type="number"
              min={1}
              max={1000}
              value={participants}
              onChange={(event) => setParticipants(Number(event.target.value))}
            />
          </label>
          <label className="text-sm">
            <span className="mb-1 block font-medium text-slate-800">Votes per participant</span>
            <Input
              type="number"
              min={1}
              max={200}
              value={votesPerParticipant}
              onChange={(event) => setVotesPerParticipant(Number(event.target.value))}
            />
          </label>
          <label className="text-sm">
            <span className="mb-1 block font-medium text-slate-800">Seed</span>
            <Input
              type="number"
              value={seed}
              onChange={(event) => setSeed(Number(event.target.value))}
            />
          </label>
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <Button
            type="button"
            variant="secondary"
            disabled={simulateVotes.isPending}
            onClick={() =>
              simulateVotes.mutate({
                participants,
                votes_per_participant: votesPerParticipant,
                seed,
              })
            }
          >
            {simulateVotes.isPending ? "Generating..." : "Generate demo votes"}
          </Button>
          {simulateVotes.isSuccess ? (
            <p className="text-sm text-emerald-700">
              Generated {simulateVotes.data.generated_votes} votes.
            </p>
          ) : null}
          {simulateVotes.isError ? (
            <p className="text-sm text-red-700" role="alert">
              {simulateVotes.error.message}
            </p>
          ) : null}
        </div>
      </Card>

      <Card className="border-red-200">
        <h3 className="text-lg font-semibold text-red-800">Danger zone</h3>
        <p className="mb-3 text-sm text-slate-600">
          Delete this conversation and all associated comments, analyses, and clusters.
        </p>
        <div className="flex flex-wrap gap-3">
          <Button
            type="button"
            variant="danger"
            disabled={deleteConversation.isPending}
            onClick={async () => {
              const confirmed = window.confirm(
                "Delete this conversation permanently? This cannot be undone.",
              );
              if (!confirmed) {
                return;
              }
              await deleteConversation.mutateAsync(conversationId);
              router.push("/");
            }}
          >
            {deleteConversation.isPending ? "Deleting..." : "Delete conversation"}
          </Button>
          <Link href={`/conversations/${conversationId}/participate`}>
            <Button type="button" variant="ghost">
              Back to participation
            </Button>
          </Link>
        </div>
      </Card>
    </section>
  );
}
