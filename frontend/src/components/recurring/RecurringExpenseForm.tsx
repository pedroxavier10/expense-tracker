"use client";

import { useTranslations } from "next-intl";
import { useEffect, useState, type FormEvent } from "react";
import type {
  Category,
  RecurringExpense,
  RecurringExpenseCreatePayload,
  RecurringExpenseUpdatePayload,
} from "@/types/api";

interface Props {
  categories: Category[];
  initial?: RecurringExpense;
  onSubmit: (
    data: RecurringExpenseCreatePayload | RecurringExpenseUpdatePayload,
  ) => Promise<void>;
  onCancel?: () => void;
  submitLabel?: string;
}

export function RecurringExpenseForm({
  categories,
  initial,
  onSubmit,
  onCancel,
  submitLabel,
}: Props) {
  const t = useTranslations("recurring");
  const tForms = useTranslations("forms");
  const tCommon = useTranslations("common");
  const effectiveSubmitLabel = submitLabel ?? tCommon("save");

  const [amount, setAmount] = useState(initial?.amount ?? "");
  const [description, setDescription] = useState(initial?.description ?? "");
  const [dayOfMonth, setDayOfMonth] = useState(initial?.day_of_month?.toString() ?? "1");
  const [categoryId, setCategoryId] = useState(
    initial?.category.id ?? categories[0]?.id ?? "",
  );
  const [endDate, setEndDate] = useState(initial?.end_date ?? "");
  const [isActive, setIsActive] = useState(initial?.is_active ?? true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!categoryId && categories[0]) setCategoryId(categories[0].id);
  }, [categories, categoryId]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const payload: RecurringExpenseCreatePayload | RecurringExpenseUpdatePayload = {
        amount,
        description: description.trim(),
        day_of_month: parseInt(dayOfMonth, 10),
        category_id: categoryId,
        end_date: endDate || null,
        is_active: isActive,
      };
      await onSubmit(payload);
      if (!initial) {
        setAmount("");
        setDescription("");
        setDayOfMonth("1");
        setEndDate("");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : t("saveFailed"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label htmlFor="r-amount" className="label">
            {tForms("amount")}
          </label>
          <input
            id="r-amount"
            type="number"
            step="0.01"
            min="0.01"
            required
            inputMode="decimal"
            className="field text-amount"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            placeholder="0.00"
          />
        </div>

        <div>
          <label htmlFor="r-day" className="label">
            {t("dayOfMonth")}
          </label>
          <input
            id="r-day"
            type="number"
            min="1"
            max="31"
            required
            className="field text-amount"
            value={dayOfMonth}
            onChange={(e) => setDayOfMonth(e.target.value)}
          />
          <p className="text-xs text-ink-muted mt-1">{t("dayOfMonthHelp")}</p>
        </div>
      </div>

      <div>
        <label htmlFor="r-category" className="label">
          {tForms("category")}
        </label>
        <select
          id="r-category"
          required
          className="field"
          value={categoryId}
          onChange={(e) => setCategoryId(e.target.value)}
        >
          {categories.map((c) => (
            <option key={c.id} value={c.id}>
              {c.icon ? `${c.icon}  ` : ""}
              {c.name}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label htmlFor="r-description" className="label">
          {tForms("description")}
        </label>
        <input
          id="r-description"
          type="text"
          required
          maxLength={500}
          className="field"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder={tForms("descriptionPlaceholder")}
        />
      </div>

      <div>
        <label htmlFor="r-enddate" className="label">
          {t("endDate")}
        </label>
        <input
          id="r-enddate"
          type="date"
          className="field"
          value={endDate}
          onChange={(e) => setEndDate(e.target.value)}
        />
        <p className="text-xs text-ink-muted mt-1">{t("endDateOptional")}</p>
      </div>

      {initial && (
        <div className="flex items-center gap-2">
          <input
            id="r-active"
            type="checkbox"
            checked={isActive}
            onChange={(e) => setIsActive(e.target.checked)}
            className="w-4 h-4"
          />
          <label htmlFor="r-active" className="text-sm text-ink cursor-pointer">
            {t("active")}
          </label>
        </div>
      )}

      {error && (
        <p className="text-sm text-accent" role="alert">
          {error}
        </p>
      )}

      <div className="flex items-center gap-2 pt-2">
        <button type="submit" disabled={busy} className="btn-primary">
          {busy ? tCommon("saving") : effectiveSubmitLabel}
        </button>
        {onCancel && (
          <button type="button" onClick={onCancel} className="btn-ghost">
            {tCommon("cancel")}
          </button>
        )}
      </div>
    </form>
  );
}
