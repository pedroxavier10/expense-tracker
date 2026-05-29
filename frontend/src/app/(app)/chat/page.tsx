"use client";

import { useTranslations } from "next-intl";

import { ChatPanel } from "@/components/chat/ChatPanel";

export default function ChatPage() {
  const t = useTranslations("chat");
  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl text-ink">{t("title")}</h1>
        <p className="text-sm text-ink-muted mt-1">{t("pageSubtitle")}</p>
      </div>
      <div className="bg-paper-card border border-paper-line rounded shadow-card overflow-hidden">
        <ChatPanel variant="page" />
      </div>
    </div>
  );
}
