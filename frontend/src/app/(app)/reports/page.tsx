"use client";

import { useTranslations } from "next-intl";
import { useEffect, useMemo, useState } from "react";
import { ReportsCharts } from "@/components/ReportsCharts";
import { useLocale } from "@/components/LocaleProvider";
import * as api from "@/lib/api";
import { toIntlLocale } from "@/lib/i18n";
import type { Expense } from "@/types/api";

function monthsAgo(n: number): string {
  const d = new Date();
  d.setMonth(d.getMonth() - n);
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  return `${y}-${m}`;
}

function monthLabel(isoMonth: string, intlLocale: string): string {
  const [y, m] = isoMonth.split("-");
  return new Date(Number(y), Number(m) - 1, 1).toLocaleString(intlLocale, {
    month: "short",
    year: "2-digit",
  });
}

export default function ReportsPage() {
  const [allExpenses, setAllExpenses] = useState<Record<string, Expense[]>>({});
  const [loading, setLoading] = useState(true);
  const t = useTranslations("reports");
  const { locale } = useLocale();
  const intlLocale = toIntlLocale(locale);

  const months = useMemo(() => Array.from({ length: 6 }, (_, i) => monthsAgo(5 - i)), []);

  useEffect(() => {
    Promise.all(
      months.map((month) =>
        api.listExpenses({ month, limit: 500 }).then((res) => ({ month, items: res.items }))
      )
    )
      .then((results) => {
        const map: Record<string, Expense[]> = {};
        for (const r of results) map[r.month] = r.items;
        setAllExpenses(map);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [months]);

  const monthlyData = useMemo(
    () =>
      months.map((m) => ({
        month: monthLabel(m, intlLocale),
        total: (allExpenses[m] ?? []).reduce((sum, e) => sum + Number(e.amount), 0),
      })),
    [months, allExpenses, intlLocale]
  );

  const categoryData = useMemo(() => {
    const currentMonth = monthsAgo(0);
    const expenses = allExpenses[currentMonth] ?? [];
    const totals: Record<string, { name: string; value: number }> = {};
    for (const e of expenses) {
      const key = e.category.slug;
      if (!totals[key]) {
        totals[key] = {
          name: `${e.category.icon ? e.category.icon + " " : ""}${e.category.name}`,
          value: 0,
        };
      }
      totals[key].value += Number(e.amount);
    }
    return Object.values(totals).sort((a, b) => b.value - a.value);
  }, [allExpenses]);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-3xl text-ink">{t("title")}</h1>
        <p className="text-sm text-ink-muted mt-1">{t("subtitle")}</p>
      </div>

      <ReportsCharts
        monthlyData={monthlyData}
        categoryData={categoryData}
        loading={loading}
      />
    </div>
  );
}
