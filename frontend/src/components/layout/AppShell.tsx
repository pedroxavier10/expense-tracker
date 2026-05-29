"use client";

import { ChatActionsProvider } from "@/components/chat/ChatActionsProvider";
import { ChatFAB } from "@/components/chat/ChatFAB";
import { Sidebar } from "@/components/layout/Sidebar";

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <ChatActionsProvider>
      <div className="flex min-h-screen">
        <Sidebar />
        <main className="flex-1 overflow-auto">
          <div className="max-w-4xl mx-auto px-6 py-8">{children}</div>
        </main>
        <ChatFAB />
      </div>
    </ChatActionsProvider>
  );
}
