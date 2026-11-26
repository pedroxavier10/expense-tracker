"use client";

import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { MaterializeConfirmStep } from "@/components/recurring/MaterializeConfirmStep";
import { RecurringExpenseForm } from "@/components/recurring/RecurringExpenseForm";
import * as api from "@/lib/api";
import type {
  Category,
  RecurringExpenseCreatePayload,
  RecurringExpenseUpdatePayload,
  RecurringSuggestion,
} from "@/types/api";

interface Props {
  suggestion: RecurringSuggestion;
  categories: Category[];
  /** A rule was created and past expenses were linked to it. */
  onAccepted: () => void;
  onClose: () => void;
}

type Step = "suggest" | "confirm-materialize";

/**
 * "You registered X in N months — make it recurring?" Shown right after an
 * expense that completes a monthly pattern is saved (form or chat).
 *
 * - Create → creates the rule with the (editable) prefilled fields and links
 *   the past occurrences to it.
 * - No → the suggestion is dismissed; the count starts again from zero.
 * - Not now → just closes; it is suggested again on the next occurrence.
 */
export function RecurringSuggestionModal({ suggestion, categories, onAccepted, onClose }: Props) {
  const t = useTranslations("recurring.suggestion");
  const tRecurring = useTranslations("recurring");
  const tCommon = useTranslations("common");
  const [step, setStep] = useState<Step>("suggest");
  const [ruleId, setRuleId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const currentMonthLabel = new Date().toLocaleDateString(undefined, {
    month: "long",
    year: "numeric",
  });

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [onClose]);

  async function handleAccept(data: RecurringExpenseCreatePayload | RecurringExpenseUpdatePayload) {
    // Errors propagate to RecurringExpenseForm, which shows them inline.
    const result = await api.acceptRecurringSuggestion({
      pattern_key: suggestion.pattern_key,
      rule: data as RecurringExpenseCreatePayload,
    });
    onAccepted();
    if (result.current_month_covered) {
      onClose();
      return;
    }
    setRuleId(result.rule.id);
    setStep("confirm-materialize");
  }

  async function handleDismiss() {
    setBusy(true);
    setError(null);
    try {
      await api.dismissRecurringSuggestion(suggestion.pattern_key);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : tRecurring("saveFailed"));
    } finally {
      setBusy(false);
    }
  }

  async function handleMaterialize() {
    if (!ruleId) return;
    setBusy(true);
    try {
      await api.materializeRecurringExpenseCurrentMonth(ruleId);
      onAccepted();
    } catch {
      // 409 means it already exists — nothing to do.
    } finally {
      setBusy(false);
      onClose();
    }
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="recurring-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center"
    >
      <div className="absolute inset-0 bg-ink/40" onClick={onClose} />
      <div className="relative bg-paper-card border border-paper-line rounded shadow-card w-full max-w-lg mx-4 p-6 max-h-[90dvh] overflow-y-auto">
        {step === "suggest" && (
          <div className="space-y-5">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 id="recurring-modal-title" className="font-display text-2xl text-ink">
                  {t("title")}
                </h2>
                <p className="text-sm text-ink-muted mt-1">
                  {t("body", { description: suggestion.description, months: suggestion.months })}
                </p>
              </div>
              <button onClick={onClose} className="btn-ghost" aria-label={tCommon("close")}>
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
                  <path d="M2 2l12 12M14 2 2 14" />
                </svg>
              </button>
            </div>

            <RecurringExpenseForm
              categories={categories}
              initialValues={{
                amount: suggestion.amount,
                description: suggestion.description,
                day_of_month: suggestion.day_of_month,
                category_id: suggestion.category.id,
              }}
              onSubmit={handleAccept}
              submitLabel={t("accept")}
              onCancel={onClose}
              cancelLabel={t("notNow")}
            />

            <div className="border-t border-paper-line pt-4 space-y-2">
              <button
                type="button"
                className="btn-ghost"
                onClick={handleDismiss}
                disabled={busy}
              >
                {t("dismiss")}
              </button>
              <p className="text-xs text-ink-muted">{t("dismissHelp")}</p>
              {error && (
                <p className="text-sm text-accent" role="alert">
                  {error}
                </p>
              )}
            </div>
          </div>
        )}

        {step === "confirm-materialize" && (
          <MaterializeConfirmStep
            currentMonthLabel={currentMonthLabel}
            busy={busy}
            onConfirm={handleMaterialize}
            onSkip={onClose}
          />
        )}
      </div>
    </div>
  );
}
