"use client";

import { ChatActionsProvider } from "@/components/chat/ChatActionsProvider";
import { ChatFAB } from "@/components/chat/ChatFAB";
import { RecurringSuggestionProvider } from "@/components/recurring/RecurringSuggestionProvider";
import { BottomNav } from "@/components/layout/BottomNav";
import { Sidebar } from "@/components/layout/Sidebar";
import { InstallPrompt } from "@/components/pwa/InstallPrompt";

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <RecurringSuggestionProvider>
      <ChatActionsProvider>
        <div className="flex min-h-[100dvh]">
          <Sidebar />
          {/* Mobile: bottom padding clears the fixed BottomNav (56px + safe area). */}
          <main className="min-w-0 flex-1 overflow-auto pb-[calc(56px+env(safe-area-inset-bottom))] md:pb-0">
            <div className="mx-auto max-w-4xl px-4 py-6 pt-[max(1.5rem,env(safe-area-inset-top))] md:px-6 md:py-8">
              <InstallPrompt />
              {children}
            </div>
          </main>
          <BottomNav />
          <ChatFAB />
        </div>
      </ChatActionsProvider>
    </RecurringSuggestionProvider>
  );
}
