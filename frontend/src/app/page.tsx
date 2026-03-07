"use client";

import Link from "next/link";

import { ConversationCard } from "@/components/conversation-card";
import { Button } from "@/components/ui/button";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/states";
import { useConversationsQuery } from "@/lib/api/hooks";

export default function Home() {
  const conversationsQuery = useConversationsQuery();

  return (
    <section className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-slate-900">Deliberation conversations</h2>
          <p className="text-sm text-slate-600">
            Browse conversations and continue core journeys from Streamlit parity.
          </p>
        </div>
        <Link href="/conversations/new">
          <Button type="button">Create conversation</Button>
        </Link>
      </div>

      {conversationsQuery.isLoading ? <LoadingState label="Loading conversations..." /> : null}
      {conversationsQuery.isError ? (
        <ErrorState
          title="Unable to load conversations"
          detail={conversationsQuery.error.message}
        />
      ) : null}
      {conversationsQuery.data && conversationsQuery.data.length === 0 ? (
        <EmptyState
          title="No conversations yet"
          detail="Create a conversation to start participation, moderation, and reporting."
        />
      ) : null}

      <div className="grid gap-4">
        {conversationsQuery.data?.map((conversation) => (
          <ConversationCard key={conversation.id} conversation={conversation} />
        ))}
      </div>
    </section>
  );
}
