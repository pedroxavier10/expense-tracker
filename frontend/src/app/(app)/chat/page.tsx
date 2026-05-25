"use client";

import { ChatPanel } from "@/components/ChatPanel";

export default function ChatPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl text-ink">Assistente</h1>
        <p className="text-sm text-ink-muted mt-1">
          Conversa com o assistente para registar despesas e consultar resumos.
        </p>
      </div>
      <div className="bg-paper-card border border-paper-line rounded shadow-card overflow-hidden">
        <ChatPanel variant="page" />
      </div>
    </div>
  );
}
