import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import type { Conversation } from "@/lib/api/contracts";

export function ConversationCard({ conversation }: { conversation: Conversation }) {
  return (
    <Card className="flex flex-col gap-3">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <h2 className="text-lg font-semibold text-slate-900">{conversation.topic}</h2>
        <div className="flex flex-wrap gap-2">
          <Badge variant={conversation.is_open ? "success" : "warning"}>
            {conversation.is_open ? "Open" : "Closed"}
          </Badge>
          <Badge variant={conversation.moderation_required ? "info" : "muted"}>
            {conversation.moderation_required ? "Moderated" : "No moderation"}
          </Badge>
        </div>
      </div>
      <p className="text-sm text-slate-600">
        {conversation.description || "No description provided."}
      </p>
      <dl className="grid grid-cols-2 gap-2 text-sm text-slate-700 sm:grid-cols-4">
        <div>
          <dt className="font-medium">Comments</dt>
          <dd>{conversation.comments ?? "-"}</dd>
        </div>
        <div>
          <dt className="font-medium">Participants</dt>
          <dd>{conversation.participants ?? "-"}</dd>
        </div>
        <div>
          <dt className="font-medium">Viz</dt>
          <dd>{conversation.allow_viz ? "Enabled" : "Disabled"}</dd>
        </div>
        <div>
          <dt className="font-medium">Submissions</dt>
          <dd>{conversation.allow_comment_submission ? "Enabled" : "Disabled"}</dd>
        </div>
      </dl>
      <div className="flex flex-wrap gap-2">
        <Link href={`/conversations/${conversation.id}/participate`}>
          <Button type="button">Participate</Button>
        </Link>
        <Link href={`/conversations/${conversation.id}/configure`}>
          <Button type="button" variant="secondary">
            Configure
          </Button>
        </Link>
        <Link href={`/conversations/${conversation.id}/moderate`}>
          <Button type="button" variant="secondary">
            Moderate
          </Button>
        </Link>
        <Link href={`/conversations/${conversation.id}/reports`}>
          <Button type="button" variant="secondary">
            Reports
          </Button>
        </Link>
      </div>
    </Card>
  );
}
