"use client";

import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { RecurringExpenseForm } from "@/components/recurring/RecurringExpenseForm";
import { MaterializeConfirmStep } from "@/components/recurring/MaterializeConfirmStep";
import * as api from "@/lib/api";
import type {
  Category,
  RecurringExpenseCreatePayload,
  RecurringExpenseUpdatePayload,
} from "@/types/api";

interface Props {
  categories: Category[];
  onCreated: () => void;
  onClose: () => void;
}

type Step = "form" | "confirm-materialize";

export function AddRecurringExpenseModal({ categories, onCreated, onClose }: Props) {
  const t = useTranslations("recurring");
  const tCommon = useTranslations("common");
  const [step, setStep] = useState<Step>("form");
  const [createdId, setCreatedId] = useState<string | null>(null);
  const [materializeBusy, setMaterializeBusy] = useState(false);

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

  async function handleCreate(data: RecurringExpenseCreatePayload | RecurringExpenseUpdatePayload) {
    const rule = await api.createRecurringExpense(data as RecurringExpenseCreatePayload);
    setCreatedId(rule.id);
    onCreated();
    setStep("confirm-materialize");
  }

  async function handleMaterialize() {
    if (!createdId) return;
    setMaterializeBusy(true);
    try {
      await api.materializeRecurringExpenseCurrentMonth(createdId);
    } catch {
      // 409 means already exists — silently ignore
    } finally {
      setMaterializeBusy(false);
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
        {step === "form" && (
          <>
            <div className="flex items-center justify-between mb-5">
              <h2 id="recurring-modal-title" className="font-display text-2xl text-ink">
                {t("addRule")}
              </h2>
              <button onClick={onClose} className="btn-ghost" aria-label={tCommon("close")}>
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
                  <path d="M2 2l12 12M14 2 2 14" />
                </svg>
              </button>
            </div>
            <RecurringExpenseForm
              categories={categories}
              onSubmit={handleCreate}
              submitLabel={t("addRuleAction")}
              onCancel={onClose}
            />
          </>
        )}

        {step === "confirm-materialize" && (
          <MaterializeConfirmStep
            currentMonthLabel={currentMonthLabel}
            busy={materializeBusy}
            onConfirm={handleMaterialize}
            onSkip={onClose}
          />
        )}
      </div>
    </div>
  );
}
