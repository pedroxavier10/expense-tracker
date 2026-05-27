"use client";

/**
 * Reusable chat panel. Used by both the FAB popover and the full /chat page.
 *
 * - Message history lives in component state (no persistence).
 * - Streams tokens from the backend SSE endpoint and appends them to the last
 *   assistant message in real time.
 * - When the model emits a `client_action` event (e.g. `open_add_expense_form`),
 *   dispatches it via `ChatActionsContext` so the rest of the app reacts.
 */

import { useTranslations } from "next-intl";
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type FormEvent,
} from "react";

import { useChatActions, EXPENSE_CREATED_EVENT } from "@/components/ChatActionsProvider";
import * as api from "@/lib/api";
import type { ChatMessage, ChatStreamEvent } from "@/types/api";
import type { ExpenseFormInitialValues } from "@/components/ExpenseForm";

interface Props {
  variant: "page" | "dialog";
}

function isExpenseFormInitialValues(
  value: Record<string, unknown>,
): ExpenseFormInitialValues {
  return {
    amount: typeof value.amount === "string" ? value.amount : undefined,
    expense_date:
      typeof value.expense_date === "string" ? value.expense_date : undefined,
    description:
      typeof value.description === "string" ? value.description : undefined,
    category_id:
      typeof value.category_id === "string" ? value.category_id : undefined,
  };
}

export function ChatPanel({ variant }: Props) {
  const { openAddExpense } = useChatActions();
  const t = useTranslations("chat");
  const greeting = useMemo<ChatMessage>(
    () => ({ role: "assistant", content: t("greeting") }),
    [t],
  );
  const [messages, setMessages] = useState<ChatMessage[]>([greeting]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [activeTool, setActiveTool] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const scrollRef = useRef<HTMLDivElement | null>(null);

  // Auto-scroll on new content.
  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages, activeTool]);

  // Abort the request if the component unmounts mid-stream.
  useEffect(() => {
    return () => abortRef.current?.abort();
  }, []);

  const send = useCallback(
    async (raw: string) => {
      const text = raw.trim();
      if (!text || busy) return;
      setError(null);
      setBusy(true);
      setActiveTool(null);

      const userMessage: ChatMessage = { role: "user", content: text };
      const placeholder: ChatMessage = { role: "assistant", content: "" };
      const history = [...messages, userMessage];
      setMessages([...history, placeholder]);
      setInput("");

      const controller = new AbortController();
      abortRef.current = controller;

      const handleEvent = (event: ChatStreamEvent) => {
        if (event.type === "text") {
          setMessages((prev) => {
            const copy = [...prev];
            const last = copy[copy.length - 1];
            if (last && last.role === "assistant") {
              copy[copy.length - 1] = {
                ...last,
                content: last.content + event.delta,
              };
            }
            return copy;
          });
        } else if (event.type === "tool_use") {
          setActiveTool(event.name);
        } else if (event.type === "tool_result") {
          setActiveTool(null);
          if (event.name === "add_expense" && event.ok) {
            window.dispatchEvent(new CustomEvent(EXPENSE_CREATED_EVENT));
          }
        } else if (event.type === "client_action") {
          if (event.action === "open_add_expense_form") {
            openAddExpense(isExpenseFormInitialValues(event.payload.prefill as Record<string, unknown> ?? {}));
          }
        } else if (event.type === "error") {
          setError(event.message);
        }
      };

      try {
        await api.streamChat(history, handleEvent, controller.signal);
      } catch (err) {
        if ((err as { name?: string }).name === "AbortError") return;
        setError(err instanceof Error ? err.message : t("chatFailed"));
      } finally {
        setBusy(false);
        setActiveTool(null);
        abortRef.current = null;
        // Trim trailing empty assistant message if the request errored.
        setMessages((prev) => {
          const last = prev[prev.length - 1];
          if (last && last.role === "assistant" && last.content.length === 0) {
            return prev.slice(0, -1);
          }
          return prev;
        });
      }
    },
    [busy, messages, openAddExpense, t],
  );

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    void send(input);
  };

  const containerHeight =
    variant === "page" ? "h-[calc(100vh-10rem)]" : "h-[480px]";

  return (
    <div className={`flex flex-col ${containerHeight} min-h-0`}>
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto px-4 py-4 space-y-3"
      >
        {messages.map((m, i) => (
          <MessageBubble key={i} message={m} />
        ))}
        {activeTool && (
          <div className="text-xs text-ink-muted px-2 italic">
            {t("usingTool", { tool: humanizeTool(t, activeTool) })}
          </div>
        )}
        {error && (
          <div className="text-xs text-accent px-2" role="alert">
            {error}
          </div>
        )}
      </div>

      <form
        onSubmit={handleSubmit}
        className="border-t border-paper-line p-3 bg-paper-card flex gap-2"
      >
        <input
          type="text"
          className="field flex-1"
          placeholder={t("placeholder")}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={busy}
          autoFocus
        />
        <button
          type="submit"
          className="btn-primary"
          disabled={busy || input.trim().length === 0}
        >
          {busy ? t("sending") : t("send")}
        </button>
      </form>
    </div>
  );
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[85%] rounded px-3 py-2 text-sm whitespace-pre-wrap ${
          isUser
            ? "bg-ink text-paper"
            : "bg-paper-line/40 text-ink border border-paper-line"
        }`}
      >
        {message.content || (isUser ? "" : "…")}
      </div>
    </div>
  );
}

const TOOL_KEYS = new Set([
  "list_categories",
  "search_expenses",
  "monthly_summary",
  "top_categories",
  "add_expense",
  "open_add_expense_form",
]);

function humanizeTool(
  t: ReturnType<typeof useTranslations<"chat">>,
  name: string,
): string {
  if (TOOL_KEYS.has(name)) return t(`tools.${name}` as never);
  return name;
}

