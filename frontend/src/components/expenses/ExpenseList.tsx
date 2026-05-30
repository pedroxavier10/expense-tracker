"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";

import { ExpenseForm } from "@/components/expenses/ExpenseForm";
import { useFormat } from "@/lib/useFormat";
import type {
  Category,
  Expense,
  ExpenseUpdatePayload,
} from "@/types/api";

interface Props {
  expenses: Expense[];
  categories: Category[];
  total: number;
  onUpdate: (id: string, payload: ExpenseUpdatePayload) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
}

export function ExpenseList({
  expenses,
  categories,
  total,
  onUpdate,
  onDelete,
}: Props) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
  const t = useTranslations("expenses");
  const tCommon = useTranslations("common");
  const { formatCurrency, formatDate } = useFormat();

  const totalAmount = expenses.reduce((sum, e) => sum + Number(e.amount), 0);

  if (expenses.length === 0) {
    return (
      <div className="bg-paper-card border border-paper-line rounded p-12 text-center shadow-card">
        <p className="text-ink-muted">{t("noMatchingExpenses")}</p>
      </div>
    );
  }

  return (
    <div className="bg-paper-card border border-paper-line rounded shadow-card overflow-hidden">
      <div className="px-4 py-3 border-b border-paper-line flex items-baseline justify-between">
        <div className="text-xs uppercase tracking-[0.12em] text-ink-muted font-medium">
          {t("expenseCount", { count: total })}
        </div>
        <div className="text-amount text-lg text-ink">
          {formatCurrency(totalAmount)}
          <span className="text-xs text-ink-muted ml-2">{t("shown")}</span>
        </div>
      </div>

      <ul className="divide-y divide-paper-line">
        {expenses.map((e) => {
          const isEditing = editingId === e.id;
          const isConfirming = confirmDeleteId === e.id;

          return (
            <li key={e.id} className="px-4 py-3">
              {isEditing ? (
                <div className="py-2">
                  <ExpenseForm
                    categories={categories}
                    initial={e}
                    submitLabel={t("update")}
                    onCancel={() => setEditingId(null)}
                    onSubmit={async (data) => {
                      await onUpdate(e.id, data);
                      setEditingId(null);
                    }}
                  />
                </div>
              ) : (
                <div className="flex items-center gap-4">
                  <div className="w-20 shrink-0 text-xs text-ink-muted">
                    {formatDate(e.expense_date)}
                  </div>

                  <div className="w-28 shrink-0">
                    <span className="inline-flex items-center gap-1.5 text-xs px-2 py-0.5 rounded border border-paper-line text-ink-muted">
                      {e.category.icon && <span>{e.category.icon}</span>}
                      <span>{e.category.name}</span>
                    </span>
                  </div>

                  <div className="flex-1 min-w-0 flex items-center gap-2">
                    <span className="text-ink truncate">{e.description}</span>
                    {e.is_recurring && (
                      <span className="shrink-0 inline-flex items-center text-xs px-1.5 py-0.5 rounded border border-paper-line text-ink-muted bg-paper-line/30">
                        {t("recurringBadge")}
                      </span>
                    )}
                  </div>

                  <div className="text-amount text-ink">
                    {formatCurrency(e.amount)}
                  </div>

                  <div className="flex items-center gap-1 shrink-0">
                    {isConfirming ? (
                      <>
                        <span className="text-xs text-ink-muted mr-2">
                          {tCommon("sure")}
                        </span>
                        <button
                          className="btn-danger"
                          onClick={async () => {
                            await onDelete(e.id);
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
                          onClick={() => setEditingId(e.id)}
                        >
                          {tCommon("edit")}
                        </button>
                        <button
                          className="btn-danger"
                          onClick={() => setConfirmDeleteId(e.id)}
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
