import { redirect } from "next/navigation";

export default async function ConversationDefaultPage({
  params,
}: Readonly<{ params: Promise<{ conversationId: string }> }>) {
  const { conversationId } = await params;
  redirect(`/conversations/${conversationId}/participate`);
}
