"use client";

/**
 * Global handler for "client actions" emitted by the chat.
 *
 * `open_add_expense_form` — a chat-driven request to open the "add expense"
 * modal with whatever fields the model managed to extract. After the user
 * confirms, we create the expense and broadcast an `expense-created` window
 * event so any page-level list refreshes itself. If the new expense completes
 * a monthly pattern, the recurring-expense suggestion is shown.
 */

import {
  createContext,
  useCallback,
  useContext,
  useState,
  type ReactNode,
} from "react";

import { AddExpenseModal } from "@/components/expenses/AddExpenseModal";
import { useRecurringSuggestion } from "@/components/recurring/RecurringSuggestionProvider";
import type { ExpenseFormInitialValues } from "@/components/expenses/ExpenseForm";
import { useCategories } from "@/hooks/useCategories";
import * as api from "@/lib/api";
import { EXPENSE_CREATED_EVENT } from "@/lib/events";
import type { ExpenseCreatePayload, ExpenseUpdatePayload } from "@/types/api";

// Kept as a re-export: existing imports read it from here.
export { EXPENSE_CREATED_EVENT };

interface ChatActionsState {
  openAddExpense: (prefill?: ExpenseFormInitialValues) => void;
}

const ChatActionsContext = createContext<ChatActionsState | null>(null);

export function ChatActionsProvider({ children }: { children: ReactNode }) {
  // This provider lives in AppShell and stays mounted across navigation, so the
  // list fetched on mount goes stale once categories are created/reactivated
  // elsewhere. Refetch every time the modal opens.
  const { categories, refetch: refetchCategories } = useCategories();
  const [open, setOpen] = useState(false);
  const [prefill, setPrefill] = useState<ExpenseFormInitialValues | undefined>();
  const { showRecurringSuggestion } = useRecurringSuggestion();

  const openAddExpense = useCallback(
    (values?: ExpenseFormInitialValues) => {
      setPrefill(values);
      setOpen(true);
      void refetchCategories();
    },
    [refetchCategories],
  );

  const handleSubmit = useCallback(
    async (data: ExpenseCreatePayload | ExpenseUpdatePayload) => {
      const created = await api.createExpense(data as ExpenseCreatePayload);
      if (typeof window !== "undefined") {
        window.dispatchEvent(new CustomEvent(EXPENSE_CREATED_EVENT));
      }
      showRecurringSuggestion(created.recurring_suggestion);
    },
    [showRecurringSuggestion],
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
