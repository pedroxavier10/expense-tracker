"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { useCallback, useMemo, useState } from "react";
import { AddExpenseModal } from "@/components/expenses/AddExpenseModal";
import { SummaryCard } from "@/components/reports/SummaryCard";
import { useLocale } from "@/components/LocaleProvider";
import { useCategories } from "@/hooks/useCategories";
import { useExpenses } from "@/hooks/useExpenses";
import * as api from "@/lib/api";
import { currentMonthIso } from "@/lib/format";
import { toIntlLocale } from "@/lib/i18n";
import { useFormat } from "@/lib/useFormat";
import type { ExpenseCreatePayload, ExpenseUpdatePayload } from "@/types/api";

export default function DashboardPage() {
  const { categories } = useCategories();
  const query = useMemo(() => ({ month: currentMonthIso(), limit: 500 }), []);
  const { expenses, loading, refresh } = useExpenses(query);
  const [showModal, setShowModal] = useState(false);
  const t = useTranslations("dashboard");
  const tCommon = useTranslations("common");
  const { formatCurrency, formatDate } = useFormat();
  const { locale } = useLocale();

  const monthlyTotal = useMemo(
    () => expenses.reduce((sum, e) => sum + Number(e.amount), 0),
    [expenses]
  );

  const topCategory = useMemo(() => {
    const totals: Record<string, { name: string; icon: string | null; amount: number }> = {};
    for (const e of expenses) {
      const key = e.category.slug;
      if (!totals[key]) totals[key] = { name: e.category.name, icon: e.category.icon, amount: 0 };
      totals[key].amount += Number(e.amount);
    }
    const entries = Object.values(totals).sort((a, b) => b.amount - a.amount);
    return entries[0] ?? null;
  }, [expenses]);

  const recent = useMemo(() => expenses.slice(0, 5), [expenses]);

  const handleCreate = useCallback(
    async (data: ExpenseCreatePayload | ExpenseUpdatePayload) => {
      await api.createExpense(data as ExpenseCreatePayload);
      await refresh();
    },
    [refresh]
  );

  const now = new Date();
  const monthLabel = now.toLocaleString(toIntlLocale(locale), { month: "long", year: "numeric" });

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl text-ink">{t("title")}</h1>
          <p className="text-sm text-ink-muted mt-1 capitalize">{monthLabel}</p>
        </div>
        <button className="btn-primary shrink-0" onClick={() => setShowModal(true)}>
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <path d="M7 1v12M1 7h12" />
          </svg>
          {t("addExpense")}
        </button>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <SummaryCard
          title={t("spentThisMonth")}
          value={loading ? "—" : formatCurrency(monthlyTotal)}
          subtext={loading ? undefined : t("expenseCount", { count: expenses.length })}
        />
        <SummaryCard
          title={t("topCategory")}
          value={loading || !topCategory ? "—" : `${topCategory.icon ?? ""} ${topCategory.name}`.trim()}
          subtext={topCategory ? formatCurrency(topCategory.amount) : undefined}
        />
      </div>

      {/* Recent expenses */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-display text-xl text-ink">{t("recent")}</h2>
          <Link href="/expenses" className="text-sm text-ink-muted hover:text-ink transition-colors">
            {t("viewAll")}
          </Link>
        </div>

        <div className="bg-paper-card border border-paper-line rounded shadow-card divide-y divide-paper-line">
          {loading ? (
            <p className="px-4 py-3 text-sm text-ink-muted">{tCommon("loading")}</p>
          ) : recent.length === 0 ? (
            <p className="px-4 py-5 text-sm text-ink-muted text-center">
              {t("noExpensesThisMonth")}{" "}
              <button onClick={() => setShowModal(true)} className="underline hover:text-ink">
                {t("addOne")}
              </button>
            </p>
          ) : (
            recent.map((e) => (
              <div key={e.id} className="px-4 py-3 flex items-center justify-between gap-4">
                <div className="min-w-0">
                  <p className="text-sm text-ink truncate">{e.description}</p>
                  <p className="text-xs text-ink-muted mt-0.5">
                    {e.category.icon ? `${e.category.icon} ` : ""}
                    {e.category.name} · {formatDate(e.expense_date)}
                  </p>
                </div>
                <span className="text-amount text-sm text-ink flex-shrink-0">
                  {formatCurrency(e.amount)}
                </span>
              </div>
            ))
          )}
        </div>
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
