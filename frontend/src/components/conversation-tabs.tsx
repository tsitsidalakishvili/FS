"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

const tabItems = [
  { slug: "participate", label: "Participate" },
  { slug: "configure", label: "Configure" },
  { slug: "moderate", label: "Moderate" },
  { slug: "reports", label: "Reports" },
];

export function ConversationTabs({ conversationId }: { conversationId: string }) {
  const pathname = usePathname();

  return (
    <nav
      aria-label="Conversation sections"
      className="mb-4 flex flex-wrap gap-2 rounded-lg border border-slate-200 bg-white p-2"
    >
      {tabItems.map((item) => {
        const href = `/conversations/${conversationId}/${item.slug}`;
        const isActive = pathname === href;
        return (
          <Link
            key={item.slug}
            href={href}
            className={cn(
              "rounded-md px-3 py-2 text-sm font-medium",
              isActive
                ? "bg-blue-600 text-white"
                : "text-slate-700 hover:bg-slate-100",
            )}
          >
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
