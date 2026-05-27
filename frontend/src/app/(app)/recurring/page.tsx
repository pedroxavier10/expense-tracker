"use client";

import { useTranslations } from "next-intl";
import { useCallback, useState } from "react";
import { AddRecurringExpenseModal } from "@/components/AddRecurringExpenseModal";
import { RecurringExpenseList } from "@/components/RecurringExpenseList";
import { useCategories } from "@/hooks/useCategories";
import { useRecurringExpenses } from "@/hooks/useRecurringExpenses";
import * as api from "@/lib/api";
import type { RecurringExpenseUpdatePayload } from "@/types/api";

export default function RecurringPage() {
  const { categories } = useCategories();
  const { rules, loading, error, refresh } = useRecurringExpenses();
  const [showModal, setShowModal] = useState(false);
  const t = useTranslations("recurring");
  const tCommon = useTranslations("common");

  const handleUpdate = useCallback(
    async (id: string, data: RecurringExpenseUpdatePayload) => {
      await api.updateRecurringExpense(id, data);
      await refresh();
    },
    [refresh]
  );

  const handleDelete = useCallback(
    async (id: string) => {
      await api.deleteRecurringExpense(id);
      await refresh();
    },
    [refresh]
  );

  return (
    <div className="space-y-8">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="font-display text-3xl text-ink">{t("title")}</h1>
          <p className="text-sm text-ink-muted mt-1">{t("subtitle")}</p>
        </div>
        <button className="btn-primary" onClick={() => setShowModal(true)}>
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <path d="M7 1v12M1 7h12" />
          </svg>
          {t("addRule")}
        </button>
      </div>

      {error && (
        <p className="text-sm text-accent" role="alert">
          {error}
        </p>
      )}

      {loading ? (
        <p className="text-ink-muted text-sm">{tCommon("loading")}</p>
      ) : (
        <RecurringExpenseList
          rules={rules}
          categories={categories}
          onUpdate={handleUpdate}
          onDelete={handleDelete}
        />
      )}

      {showModal && (
        <AddRecurringExpenseModal
          categories={categories}
          onCreated={refresh}
          onClose={() => setShowModal(false)}
        />
      )}
    </div>
  );
}
