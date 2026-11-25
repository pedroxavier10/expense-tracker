"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";
import { RecurringExpenseForm } from "@/components/recurring/RecurringExpenseForm";
import { useFormat } from "@/lib/useFormat";
import type {
  Category,
  RecurringExpense,
  RecurringExpenseUpdatePayload,
} from "@/types/api";

interface Props {
  rules: RecurringExpense[];
  categories: Category[];
  onUpdate: (id: string, payload: RecurringExpenseUpdatePayload) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
}

export function RecurringExpenseList({ rules, categories, onUpdate, onDelete }: Props) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
  const t = useTranslations("recurring");
  const tCommon = useTranslations("common");
  const { formatCurrency } = useFormat();

  if (rules.length === 0) {
    return (
      <div className="bg-paper-card border border-paper-line rounded p-12 text-center shadow-card">
        <p className="text-ink-muted">{t("noRules")}</p>
      </div>
    );
  }

  return (
    <div className="bg-paper-card border border-paper-line rounded shadow-card overflow-hidden">
      <ul className="divide-y divide-paper-line">
        {rules.map((rule) => {
          const isEditing = editingId === rule.id;
          const isConfirming = confirmDeleteId === rule.id;

          return (
            <li key={rule.id} className="px-4 py-3">
              {isEditing ? (
                <div className="py-2">
                  <RecurringExpenseForm
                    categories={categories}
                    initial={rule}
                    submitLabel={t("update")}
                    onCancel={() => setEditingId(null)}
                    onSubmit={async (data) => {
                      await onUpdate(rule.id, data);
                      setEditingId(null);
                    }}
                  />
                </div>
              ) : (
                // Mobile: line 1 = description + amount, line 2 = category, status, actions.
                // From md up every `order` is reset, restoring the single-row layout.
                <div className="flex flex-wrap items-center gap-x-3 gap-y-1 md:flex-nowrap md:gap-4">
                  <div className="order-2 shrink-0 md:order-none md:w-28">
                    <span className="inline-flex items-center gap-1.5 text-xs px-2 py-0.5 rounded border border-paper-line text-ink-muted">
                      {rule.category.icon && <span>{rule.category.icon}</span>}
                      <span>{rule.category.name}</span>
                    </span>
                  </div>

                  <div className="order-1 flex-1 min-w-0 md:order-none">
                    <div className="text-ink truncate">{rule.description}</div>
                    <div className="text-xs text-ink-muted mt-0.5">
                      {t("everyDay", { day: rule.day_of_month })}
                      {rule.end_date && (
                        <span className="ml-2">· until {rule.end_date}</span>
                      )}
                    </div>
                  </div>

                  <div className="order-1 text-amount text-ink shrink-0 md:order-none">
                    {formatCurrency(rule.amount)}
                  </div>

                  {/* Forces the line break after the amount on mobile only. */}
                  <div className="order-1 basis-full md:hidden" aria-hidden="true" />

                  <div className="order-2 shrink-0 md:order-none">
                    {rule.is_active ? (
                      <span className="inline-flex items-center text-xs px-2 py-0.5 rounded bg-paper-line/60 text-ink-muted">
                        {t("active")}
                      </span>
                    ) : (
                      <span className="inline-flex items-center text-xs px-2 py-0.5 rounded bg-paper-line/60 text-ink-muted opacity-60">
                        {t("paused")}
                      </span>
                    )}
                  </div>

                  <div className="order-2 ml-auto flex items-center gap-1 shrink-0 md:order-none md:ml-0">
                    {isConfirming ? (
                      <>
                        <span className="text-xs text-ink-muted mr-2">
                          {tCommon("sure")}
                        </span>
                        <button
                          className="btn-danger"
                          onClick={async () => {
                            await onDelete(rule.id);
                            setConfirmDeleteId(null);
                          }}
                        >
                          {tCommon("delete")}
                        </button>
                        <button
                          className="btn-ghost"
                          onClick={() => setConfirmDeleteId(null)}
                        >
                          {tCommon("no")}
                        </button>
                      </>
                    ) : (
                      <>
                        <button
                          className="btn-ghost"
                          onClick={() => setEditingId(rule.id)}
                        >
                          {tCommon("edit")}
                        </button>
                        <button
                          className="btn-danger"
                          onClick={() => setConfirmDeleteId(rule.id)}
                        >
                          {tCommon("delete")}
                        </button>
                      </>
                    )}
                  </div>
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
