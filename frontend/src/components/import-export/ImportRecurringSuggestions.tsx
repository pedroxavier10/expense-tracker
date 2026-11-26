"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";

import { useRecurringSuggestion } from "@/components/recurring/RecurringSuggestionProvider";
import * as api from "@/lib/api";
import { useFormat } from "@/lib/useFormat";
import type { RecurringSuggestion } from "@/types/api";

interface Props {
  suggestions: RecurringSuggestion[];
}

/**
 * After a CSV import: expenses from the file that now repeat every month.
 * One list (instead of a modal per row); each item opens the same
 * "make it recurring?" modal used by the form and the chat, or is ignored.
 */
export function ImportRecurringSuggestions({ suggestions }: Props) {
  const t = useTranslations("importExport.recurringSuggestions");
  const tRecurring = useTranslations("recurring");
  const { formatCurrency } = useFormat();
  const { showRecurringSuggestion } = useRecurringSuggestion();
  const [resolved, setResolved] = useState<Set<string>>(new Set());
  const [busyKey, setBusyKey] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const pending = suggestions.filter((s) => !resolved.has(s.pattern_key));
  if (pending.length === 0) return null;

  function markResolved(key: string) {
    setResolved((prev) => new Set(prev).add(key));
  }

  async function handleIgnore(suggestion: RecurringSuggestion) {
    setBusyKey(suggestion.pattern_key);
    setError(null);
    try {
      await api.dismissRecurringSuggestion(suggestion.pattern_key);
      markResolved(suggestion.pattern_key);
    } catch (err) {
      setError(err instanceof Error ? err.message : tRecurring("saveFailed"));
    } finally {
      setBusyKey(null);
    }
  }

  return (
    <section className="border-t border-paper-line pt-4 space-y-3" aria-labelledby="import-recurring-title">
      <div>
        <h4 id="import-recurring-title" className="text-sm text-ink font-medium">
          {t("title")}
        </h4>
        <p className="text-xs text-ink-muted mt-0.5">{t("subtitle")}</p>
      </div>

      {error && (
        <p className="text-sm text-accent" role="alert">
          {error}
        </p>
      )}

      <ul className="border border-paper-line rounded divide-y divide-paper-line">
        {pending.map((s) => {
          const busy = busyKey === s.pattern_key;
          return (
            <li
              key={s.pattern_key}
              className="px-3 py-2 flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4"
            >
              <div className="min-w-0 flex-1">
                <p className="text-sm text-ink break-words">
                  {s.category.icon ? `${s.category.icon} ` : ""}
                  {s.description}
                  <span className="text-amount text-ink-muted"> · {formatCurrency(s.amount)}</span>
                </p>
                <p className="text-xs text-ink-muted">
                  {t("meta", { months: s.months, day: s.day_of_month })}
                </p>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <button
                  type="button"
                  className="btn-primary"
                  disabled={busy}
                  onClick={() =>
                    showRecurringSuggestion(s, (outcome) => {
                      if (outcome !== "closed") markResolved(s.pattern_key);
                    })
                  }
                >
                  {t("create")}
                </button>
                <button
                  type="button"
                  className="btn-ghost"
                  disabled={busy}
                  onClick={() => void handleIgnore(s)}
                >
                  {t("ignore")}
                </button>
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
