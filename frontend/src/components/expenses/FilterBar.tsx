"use client";

import { useTranslations } from "next-intl";

import type { Category } from "@/types/api";

export interface FilterValues {
  categoryId: string;
  month: string;
  dateFrom: string;
  dateTo: string;
  q: string;
  /** "month" or "range" — controls which date inputs are shown */
  dateMode: "month" | "range";
}

interface Props {
  categories: Category[];
  value: FilterValues;
  onChange: (next: FilterValues) => void;
  onReset: () => void;
}

export function FilterBar({ categories, value, onChange, onReset }: Props) {
  const t = useTranslations("filters");

  function set<K extends keyof FilterValues>(key: K, v: FilterValues[K]) {
    onChange({ ...value, [key]: v });
  }

  return (
    <div className="bg-paper-card border border-paper-line rounded p-4 shadow-card">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xs uppercase tracking-[0.12em] text-ink-muted font-medium">
          {t("title")}
        </h2>
        <button onClick={onReset} className="btn-ghost text-xs">
          {t("reset")}
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div>
          <label htmlFor="f-cat" className="label">
            {t("category")}
          </label>
          <select
            id="f-cat"
            className="field"
            value={value.categoryId}
            onChange={(e) => set("categoryId", e.target.value)}
          >
            <option value="">{t("allCategories")}</option>
            {categories.map((c) => (
              <option key={c.id} value={c.id}>
                {c.icon ? `${c.icon}  ` : ""}
                {c.name}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="f-mode" className="label">
            {t("dateFilter")}
          </label>
          <select
            id="f-mode"
            className="field"
            value={value.dateMode}
            onChange={(e) =>
              onChange({
                ...value,
                dateMode: e.target.value as "month" | "range",
                month: "",
                dateFrom: "",
                dateTo: "",
              })
            }
          >
            <option value="month">{t("byMonth")}</option>
            <option value="range">{t("byDateRange")}</option>
          </select>
        </div>

        {value.dateMode === "month" ? (
          <div className="lg:col-span-2">
            <label htmlFor="f-month" className="label">
              {t("month")}
            </label>
            <input
              id="f-month"
              type="month"
              className="field"
              value={value.month}
              onChange={(e) => set("month", e.target.value)}
            />
          </div>
        ) : (
          <>
            <div>
              <label htmlFor="f-from" className="label">
                {t("from")}
              </label>
              <input
                id="f-from"
                type="date"
                className="field"
                value={value.dateFrom}
                onChange={(e) => set("dateFrom", e.target.value)}
              />
            </div>
            <div>
              <label htmlFor="f-to" className="label">
                {t("to")}
              </label>
              <input
                id="f-to"
                type="date"
                className="field"
                value={value.dateTo}
                onChange={(e) => set("dateTo", e.target.value)}
              />
            </div>
          </>
        )}

        <div className="md:col-span-2 lg:col-span-4">
          <label htmlFor="f-q" className="label">
            {t("searchDescription")}
          </label>
          <input
            id="f-q"
            type="text"
            className="field"
            placeholder={t("searchPlaceholder")}
            value={value.q}
            onChange={(e) => set("q", e.target.value)}
          />
        </div>
      </div>
    </div>
  );
}
