"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { useCreateConversationMutation } from "@/lib/api/hooks";

export default function NewConversationPage() {
  const router = useRouter();
  const [topic, setTopic] = useState("");
  const [description, setDescription] = useState("");
  const [isOpen, setIsOpen] = useState(true);
  const [allowCommentSubmission, setAllowCommentSubmission] = useState(true);
  const [allowViz, setAllowViz] = useState(true);
  const [moderationRequired, setModerationRequired] = useState(false);
  const createConversation = useCreateConversationMutation({
    onSuccess: (conversation) => {
      router.push(`/conversations/${conversation.id}/configure`);
    },
  });

  function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    createConversation.mutate({
      topic: topic.trim(),
      description: description.trim(),
      is_open: isOpen,
      allow_comment_submission: allowCommentSubmission,
      allow_viz: allowViz,
      moderation_required: moderationRequired,
    });
  }

  return (
    <section className="space-y-4">
      <header>
        <h2 className="text-2xl font-semibold text-slate-900">Create conversation</h2>
        <p className="text-sm text-slate-600">
          Contract-backed creation flow for the FastAPI `/conversations` endpoint.
        </p>
      </header>

      <Card>
        <form className="space-y-4" onSubmit={onSubmit}>
          <label className="block text-sm">
            <span className="mb-1 block font-medium text-slate-800">Topic</span>
            <Input
              required
              minLength={3}
              value={topic}
              onChange={(event) => setTopic(event.target.value)}
              placeholder="Conversation title"
            />
          </label>

          <label className="block text-sm">
            <span className="mb-1 block font-medium text-slate-800">Description</span>
            <Textarea
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              rows={4}
              placeholder="Context for participants"
            />
          </label>

          <div className="grid gap-3 sm:grid-cols-2">
            <label className="flex items-center gap-2 text-sm text-slate-800">
              <input
                type="checkbox"
                checked={isOpen}
                onChange={(event) => setIsOpen(event.target.checked)}
              />
              Open for participation
            </label>
            <label className="flex items-center gap-2 text-sm text-slate-800">
              <input
                type="checkbox"
                checked={allowCommentSubmission}
                onChange={(event) => setAllowCommentSubmission(event.target.checked)}
              />
              Allow participant comments
            </label>
            <label className="flex items-center gap-2 text-sm text-slate-800">
              <input
                type="checkbox"
                checked={allowViz}
                onChange={(event) => setAllowViz(event.target.checked)}
              />
              Allow visualization
            </label>
            <label className="flex items-center gap-2 text-sm text-slate-800">
              <input
                type="checkbox"
                checked={moderationRequired}
                onChange={(event) => setModerationRequired(event.target.checked)}
              />
              Moderation required
            </label>
          </div>

          <Button type="submit" disabled={createConversation.isPending}>
            {createConversation.isPending ? "Creating..." : "Create conversation"}
          </Button>

          {createConversation.isError ? (
            <p className="text-sm text-red-700" role="alert">
              {createConversation.error.message}
            </p>
          ) : null}
        </form>
      </Card>
    </section>
  );
}
