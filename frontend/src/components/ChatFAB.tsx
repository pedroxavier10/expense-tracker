"use client";

/**
 * Floating action button + anchored chat panel.
 *
 * Visible from every protected route. Click toggles a small chat panel
 * docked above the button. ESC closes it.
 */

import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { ChatPanel } from "@/components/ChatPanel";

export function ChatFAB() {
  const [open, setOpen] = useState(false);
  const t = useTranslations("chat");

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open]);

  return (
    <>
      {open && (
        <div
          className="fixed bottom-24 right-6 z-40 w-[380px] max-w-[calc(100vw-3rem)] bg-paper-card border border-paper-line rounded shadow-card overflow-hidden"
          role="dialog"
          aria-label="Chatbot"
        >
          <div className="flex items-center justify-between border-b border-paper-line px-4 py-3">
            <div>
              <h2 className="font-display text-lg text-ink leading-tight">
                {t("fabTitle")}
              </h2>
              <p className="text-xs text-ink-muted">{t("fabSubtitle")}</p>
            </div>
            <button
              onClick={() => setOpen(false)}
              className="btn-ghost"
              aria-label={t("closeChat")}
            >
              <svg
                width="16"
                height="16"
                viewBox="0 0 16 16"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
              >
                <path d="M2 2l12 12M14 2 2 14" />
              </svg>
            </button>
          </div>
          <ChatPanel variant="dialog" />
        </div>
      )}

      <button
        onClick={() => setOpen((v) => !v)}
        title={open ? t("closeChat") : t("openChat")}
        aria-label={open ? t("closeChat") : t("openChat")}
        className="fixed bottom-6 right-6 z-40 w-14 h-14 rounded-full bg-ink text-paper shadow-card hover:bg-ink-soft transition-colors flex items-center justify-center"
      >
        {open ? (
          <svg
            width="20"
            height="20"
            viewBox="0 0 20 20"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
          >
            <path d="M4 4l12 12M16 4 4 16" />
          </svg>
        ) : (
          <svg
            width="22"
            height="22"
            viewBox="0 0 22 22"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M3 5.5A2.5 2.5 0 0 1 5.5 3h11A2.5 2.5 0 0 1 19 5.5v8A2.5 2.5 0 0 1 16.5 16H8l-4 3v-3.5A2.5 2.5 0 0 1 3 13V5.5z" />
            <circle cx="8" cy="9.5" r="0.8" fill="currentColor" />
            <circle cx="11" cy="9.5" r="0.8" fill="currentColor" />
            <circle cx="14" cy="9.5" r="0.8" fill="currentColor" />
          </svg>
        )}
      </button>
    </>
  );
}
