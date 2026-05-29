"use client";

/**
 * Global handler for "client actions" emitted by the chat.
 *
 * Today there's only one: `open_add_expense_form` — a chat-driven request to
 * open the "add expense" modal with whatever fields the model managed to
 * extract. After the user confirms, we create the expense and broadcast an
 * `expense-created` window event so any page-level list refreshes itself.
 */

import {
  createContext,
  useCallback,
  useContext,
  useState,
  type ReactNode,
} from "react";

import { AddExpenseModal } from "@/components/expenses/AddExpenseModal";
import type { ExpenseFormInitialValues } from "@/components/expenses/ExpenseForm";
import { useCategories } from "@/hooks/useCategories";
import * as api from "@/lib/api";
import type { ExpenseCreatePayload, ExpenseUpdatePayload } from "@/types/api";

export const EXPENSE_CREATED_EVENT = "expense-created";

interface ChatActionsState {
  openAddExpense: (prefill?: ExpenseFormInitialValues) => void;
}

const ChatActionsContext = createContext<ChatActionsState | null>(null);

export function ChatActionsProvider({ children }: { children: ReactNode }) {
  const { categories } = useCategories();
  const [open, setOpen] = useState(false);
  const [prefill, setPrefill] = useState<ExpenseFormInitialValues | undefined>();

  const openAddExpense = useCallback((values?: ExpenseFormInitialValues) => {
    setPrefill(values);
    setOpen(true);
  }, []);

  const handleSubmit = useCallback(
    async (data: ExpenseCreatePayload | ExpenseUpdatePayload) => {
      await api.createExpense(data as ExpenseCreatePayload);
      if (typeof window !== "undefined") {
        window.dispatchEvent(new CustomEvent(EXPENSE_CREATED_EVENT));
      }
    },
    [],
  );

  return (
    <ChatActionsContext.Provider value={{ openAddExpense }}>
      {children}
      {open && (
        <AddExpenseModal
          categories={categories}
          initialValues={prefill}
          onSubmit={handleSubmit}
          onClose={() => setOpen(false)}
        />
      )}
    </ChatActionsContext.Provider>
  );
}

export function useChatActions(): ChatActionsState {
  const ctx = useContext(ChatActionsContext);
  if (!ctx) throw new Error("useChatActions must be used inside <ChatActionsProvider>");
  return ctx;
}
