"use client";

import { useTranslations } from "next-intl";
import { useCallback, useMemo, useState } from "react";
import { AddExpenseModal } from "@/components/expenses/AddExpenseModal";
import { ExpenseList } from "@/components/expenses/ExpenseList";
import { FilterBar, type FilterValues } from "@/components/expenses/FilterBar";
import { useCategories } from "@/hooks/useCategories";
import { useExpenses } from "@/hooks/useExpenses";
import * as api from "@/lib/api";
import { currentMonthIso } from "@/lib/format";
import type { ExpenseCreatePayload, ExpenseFilters, ExpenseUpdatePayload } from "@/types/api";

const EMPTY_FILTERS: FilterValues = {
  categoryId: "",
  month: currentMonthIso(),
  dateFrom: "",
  dateTo: "",
  q: "",
  dateMode: "month",
};

function filtersToQuery(f: FilterValues): ExpenseFilters {
  const out: ExpenseFilters = { limit: 500 };
  if (f.categoryId) out.category_id = f.categoryId;
  if (f.q) out.description_contains = f.q;
  if (f.dateMode === "month") {
    if (f.month) out.month = f.month;
  } else {
    if (f.dateFrom) out.date_from = f.dateFrom;
    if (f.dateTo) out.date_to = f.dateTo;
  }
  return out;
}

export default function ExpensesPage() {
  const { categories } = useCategories();
  const [filters, setFilters] = useState<FilterValues>(EMPTY_FILTERS);
  const [showModal, setShowModal] = useState(false);
  const query = useMemo(() => filtersToQuery(filters), [filters]);
  const { expenses, total, loading, error, refresh } = useExpenses(query);
  const t = useTranslations("expenses");
  const tCommon = useTranslations("common");

  const handleCreate = useCallback(
    async (data: ExpenseCreatePayload | ExpenseUpdatePayload) => {
      await api.createExpense(data as ExpenseCreatePayload);
      await refresh();
    },
    [refresh]
  );

  const handleUpdate = useCallback(
    async (id: string, data: ExpenseUpdatePayload) => {
      await api.updateExpense(id, data);
      await refresh();
    },
    [refresh]
  );

  const handleDelete = useCallback(
    async (id: string) => {
      await api.deleteExpense(id);
      await refresh();
    },
    [refresh]
  );

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl text-ink">{t("title")}</h1>
          <p className="text-sm text-ink-muted mt-1">{t("subtitle")}</p>
        </div>
        <button className="btn-primary shrink-0" onClick={() => setShowModal(true)}>
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <path d="M7 1v12M1 7h12" />
          </svg>
          {t("addExpense")}
        </button>
      </div>

      <section className="space-y-4">
        <FilterBar
          categories={categories}
          value={filters}
          onChange={setFilters}
          onReset={() => setFilters(EMPTY_FILTERS)}
        />

        {error && (
          <p className="text-sm text-accent" role="alert">
            {error}
          </p>
        )}

        {loading ? (
          <p className="text-ink-muted text-sm">{tCommon("loading")}</p>
        ) : (
          <ExpenseList
            expenses={expenses}
            categories={categories}
            total={total}
            onUpdate={handleUpdate}
            onDelete={handleDelete}
          />
        )}
      </section>

      {showModal && (
        <AddExpenseModal
          categories={categories}
          onSubmit={handleCreate}
          onClose={() => setShowModal(false)}
        />
      )}
    </div>
  );
}
