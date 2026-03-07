import { ConversationTabs } from "@/components/conversation-tabs";

export default async function ConversationLayout({
  children,
  params,
}: Readonly<{
  children: React.ReactNode;
  params: Promise<{ conversationId: string }>;
}>) {
  const { conversationId } = await params;

  return (
    <section>
      <ConversationTabs conversationId={conversationId} />
      {children}
    </section>
  );
}
