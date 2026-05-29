"use client";

import { useTranslations } from "next-intl";
import { useEffect, useState, type FormEvent } from "react";

import { todayIso } from "@/lib/format";
import type {
  Category,
  Expense,
  ExpenseCreatePayload,
  ExpenseUpdatePayload,
} from "@/types/api";

export interface ExpenseFormInitialValues {
  amount?: string;
  expense_date?: string;
  description?: string;
  category_id?: string;
}

interface Props {
  categories: Category[];
  initial?: Expense;
  initialValues?: ExpenseFormInitialValues;
  onSubmit: (
    data: ExpenseCreatePayload | ExpenseUpdatePayload,
  ) => Promise<void>;
  onCancel?: () => void;
  submitLabel?: string;
}

export function ExpenseForm({
  categories,
  initial,
  initialValues,
  onSubmit,
  onCancel,
  submitLabel,
}: Props) {
  const t = useTranslations("forms");
  const tCommon = useTranslations("common");
  const effectiveSubmitLabel = submitLabel ?? tCommon("save");
  const [amount, setAmount] = useState(
    initial?.amount ?? initialValues?.amount ?? "",
  );
  const [date, setDate] = useState(
    initial?.expense_date ?? initialValues?.expense_date ?? todayIso(),
  );
  const [description, setDescription] = useState(
    initial?.description ?? initialValues?.description ?? "",
  );
  const [categoryId, setCategoryId] = useState(
    initial?.category.id ?? initialValues?.category_id ?? categories[0]?.id ?? "",
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // If the available categories list arrives after initial render, fill it in.
  useEffect(() => {
    if (!categoryId && categories[0]) setCategoryId(categories[0].id);
  }, [categories, categoryId]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await onSubmit({
        amount,
        expense_date: date,
        description: description.trim(),
        category_id: categoryId,
      });
      if (!initial) {
        // Reset on successful create; keep date and category for fast multi-entry.
        setAmount("");
        setDescription("");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : t("saveFailed"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label htmlFor="amount" className="label">
            {t("amount")}
          </label>
          <input
            id="amount"
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
          <label htmlFor="date" className="label">
            {t("date")}
          </label>
          <input
            id="date"
            type="date"
            required
            className="field"
            value={date}
            onChange={(e) => setDate(e.target.value)}
          />
        </div>
      </div>

      <div>
        <label htmlFor="category" className="label">
          {t("category")}
        </label>
        <select
          id="category"
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
        <label htmlFor="description" className="label">
          {t("description")}
        </label>
        <input
          id="description"
          type="text"
          required
          maxLength={500}
          className="field"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder={t("descriptionPlaceholder")}
        />
      </div>

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
