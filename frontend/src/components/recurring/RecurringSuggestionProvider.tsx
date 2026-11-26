"use client";

/**
 * Global host for the "make this expense recurring?" modal.
 *
 * Whoever registers an expense (dashboard/expenses pages, the chat's form or
 * the chat's `add_expense` tool) calls `showRecurringSuggestion` with the
 * suggestion returned by the backend. Lives in AppShell so the modal survives
 * the "add expense" modal closing and page navigation.
 */

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

import { RecurringSuggestionModal } from "@/components/recurring/RecurringSuggestionModal";
import { useCategories } from "@/hooks/useCategories";
import { EXPENSE_CREATED_EVENT } from "@/lib/events";
import type { RecurringSuggestion } from "@/types/api";

export type RecurringSuggestionOutcome = "accepted" | "dismissed" | "closed";

interface RecurringSuggestionState {
  /**
   * No-op for `null`/`undefined`, so callers can pass the API field directly.
   * `onResolved` reports how the modal ended ("closed" = "Not now").
   */
  showRecurringSuggestion: (
    suggestion: RecurringSuggestion | null | undefined,
    onResolved?: (outcome: RecurringSuggestionOutcome) => void,
  ) => void;
}

const RecurringSuggestionContext = createContext<RecurringSuggestionState | null>(null);

export function RecurringSuggestionProvider({ children }: { children: ReactNode }) {
  const { categories, refetch: refetchCategories } = useCategories();
  const [suggestion, setSuggestion] = useState<RecurringSuggestion | null>(null);
  const outcomeRef = useRef<RecurringSuggestionOutcome>("closed");
  const onResolvedRef = useRef<((outcome: RecurringSuggestionOutcome) => void) | undefined>(
    undefined,
  );

  const showRecurringSuggestion = useCallback(
    (
      value: RecurringSuggestion | null | undefined,
      onResolved?: (outcome: RecurringSuggestionOutcome) => void,
    ) => {
      if (!value) return;
      outcomeRef.current = "closed";
      onResolvedRef.current = onResolved;
      setSuggestion(value);
      void refetchCategories();
    },
    [refetchCategories],
  );

  // The suggested category is always selectable, even before the list refreshes.
  const options = useMemo(() => {
    if (!suggestion || categories.some((c) => c.id === suggestion.category.id)) {
      return categories;
    }
    return [suggestion.category, ...categories];
  }, [categories, suggestion]);

  const handleAccepted = useCallback(() => {
    outcomeRef.current = "accepted";
    // Linked expenses now carry the recurring badge: let lists refresh.
    window.dispatchEvent(new CustomEvent(EXPENSE_CREATED_EVENT));
  }, []);

  const handleDismissed = useCallback(() => {
    outcomeRef.current = "dismissed";
  }, []);

  const handleClose = useCallback(() => {
    setSuggestion(null);
    onResolvedRef.current?.(outcomeRef.current);
    onResolvedRef.current = undefined;
  }, []);

  const value = useMemo(() => ({ showRecurringSuggestion }), [showRecurringSuggestion]);

  return (
    <RecurringSuggestionContext.Provider value={value}>
      {children}
      {suggestion && (
        <RecurringSuggestionModal
          key={suggestion.pattern_key}
          suggestion={suggestion}
          categories={options}
          onAccepted={handleAccepted}
          onDismissed={handleDismissed}
          onClose={handleClose}
        />
      )}
    </RecurringSuggestionContext.Provider>
  );
}

export function useRecurringSuggestion(): RecurringSuggestionState {
  const ctx = useContext(RecurringSuggestionContext);
  if (!ctx) {
    throw new Error("useRecurringSuggestion must be used inside <RecurringSuggestionProvider>");
  }
  return ctx;
}
