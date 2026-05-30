"use client";

import { useTranslations } from "next-intl";
import { useEffect, useMemo, useState } from "react";
import { ReportsCharts } from "@/components/reports/ReportsCharts";
import { SummaryCard } from "@/components/reports/SummaryCard";
import { useLocale } from "@/components/LocaleProvider";
import { useFormat } from "@/lib/useFormat";
import * as api from "@/lib/api";
import { toIntlLocale } from "@/lib/i18n";
import type { AnnualSummaryResponse, MonthlySummaryResponse } from "@/types/api";

function monthsAgo(n: number): string {
  const d = new Date();
  d.setDate(1);
  d.setMonth(d.getMonth() - n);
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  return `${y}-${m}`;
}

function monthLabel(isoMonth: string, intlLocale: string): string {
  const [y, m] = isoMonth.split("-");
  return new Date(Number(y), Number(m) - 1, 1).toLocaleString(intlLocale, {
    month: "long",
    year: "numeric",
  });
}


export default function ReportsPage() {
  const currentYear = new Date().getFullYear();

  const [viewMode, setViewMode] = useState<"monthly" | "annual">("monthly");
  const [monthOffset, setMonthOffset] = useState(0);
  const [selectedYear, setSelectedYear] = useState(currentYear);

  const selectedMonthKey = useMemo(() => monthsAgo(monthOffset), [monthOffset]);

  const [monthlySummary, setMonthlySummary] = useState<MonthlySummaryResponse | null>(null);
  const [annualSummary, setAnnualSummary] = useState<AnnualSummaryResponse | null>(null);
  const [loading, setLoading] = useState(true);

  const t = useTranslations("reports");
  const { locale } = useLocale();
  const intlLocale = toIntlLocale(locale);
  const { formatCurrency } = useFormat();

  // Monthly fetch — selected month
  useEffect(() => {
    if (viewMode !== "monthly") return;
    setLoading(true);
    api
      .getMonthSummary(selectedMonthKey)
      .then(setMonthlySummary)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [viewMode, selectedMonthKey]);

  // Annual fetch — single request, DB aggregates by month and category
  useEffect(() => {
    if (viewMode !== "annual") return;
    setLoading(true);
    api
      .getAnnualSummary(selectedYear)
      .then(setAnnualSummary)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [viewMode, selectedYear]);

  const annualMonthlyData = useMemo(() => {
    if (!annualSummary) return Array.from({ length: 12 }, (_, i) => ({
      month: new Date(selectedYear, i, 1).toLocaleString(intlLocale, { month: "short" }),
      total: 0,
    }));
    return annualSummary.by_month.map((m, i) => ({
      month: new Date(selectedYear, i, 1).toLocaleString(intlLocale, { month: "short" }),
      total: Number(m.total),
    }));
  }, [annualSummary, selectedYear, intlLocale]);

  const categoryData = useMemo(() => {
    if (viewMode === "annual") {
      return (annualSummary?.by_category ?? []).map((c) => ({
        name: `${c.icon ? c.icon + " " : ""}${c.name}`,
        value: Number(c.total),
      }));
    }
    return (monthlySummary?.by_category ?? []).map((c) => ({
      name: `${c.icon ? c.icon + " " : ""}${c.name}`,
      value: Number(c.total),
    }));
  }, [viewMode, annualSummary, monthlySummary]);

  const categoryTitle =
    viewMode === "annual"
      ? t("byCategoryThisYear")
      : t("byCategoryFor", { period: monthLabel(selectedMonthKey, intlLocale) });

  const isAtPresent =
    viewMode === "annual" ? selectedYear >= currentYear : monthOffset === 0;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-3xl text-ink">{t("title")}</h1>
        <p className="text-sm text-ink-muted mt-1">{t("subtitle")}</p>
      </div>

      <div className="flex items-center justify-between gap-4">
        {/* Mode toggle */}
        <div className="flex items-center gap-1 bg-paper-card border border-paper-line rounded p-1">
          {(["monthly", "annual"] as const).map((mode) => (
            <button
              key={mode}
              onClick={() => setViewMode(mode)}
              className={`px-3 py-1.5 rounded text-sm font-medium transition-colors ${
                viewMode === mode
                  ? "bg-ink text-paper"
                  : "text-ink-muted hover:text-ink hover:bg-paper-line/40"
              }`}
            >
              {t(mode === "monthly" ? "viewMonthly" : "viewAnnual")}
            </button>
          ))}
        </div>

        {/* Period navigator */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => viewMode === "annual" ? setSelectedYear((y) => y - 1) : setMonthOffset((o) => o + 1)}
            className="btn-ghost px-2 py-1"
          >
            ‹
          </button>
          <span className="text-sm font-medium w-44 text-center">
            {viewMode === "annual" ? selectedYear : monthLabel(selectedMonthKey, intlLocale)}
          </span>
          <button
            onClick={() => viewMode === "annual" ? setSelectedYear((y) => Math.min(y + 1, currentYear)) : setMonthOffset((o) => Math.max(o - 1, 0))}
            disabled={isAtPresent}
            className="btn-ghost px-2 py-1 disabled:opacity-40"
          >
            ›
          </button>
        </div>
      </div>

      {/* Monthly: current month total card */}
      {viewMode === "monthly" && !loading && (
        <SummaryCard
          title={t("monthlyTotal")}
          value={formatCurrency(Number(monthlySummary?.total ?? 0))}
          subtext={monthLabel(selectedMonthKey, intlLocale)}
        />
      )}

      {/* Annual: year total card */}
      {viewMode === "annual" && !loading && annualSummary && (
        <SummaryCard
          title={t("annualTotal")}
          value={formatCurrency(Number(annualSummary.total))}
          subtext={String(selectedYear)}
        />
      )}

      <ReportsCharts
        monthlyData={annualMonthlyData}
        categoryData={categoryData}
        categoryTitle={categoryTitle}
        loading={loading}
        mode={viewMode}
      />
    </div>
  );
}
