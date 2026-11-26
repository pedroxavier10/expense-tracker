"use client";

import { useTranslations } from "next-intl";
import { useEffect, useState, type FormEvent } from "react";

import { suggestCategory } from "@/lib/api";
import { todayIso } from "@/lib/format";
import type {
  Category,
  CategorySuggestion,
  Expense,
  ExpenseCreatePayload,
  ExpenseUpdatePayload,
} from "@/types/api";

const SUGGESTION_DEBOUNCE_MS = 400;
const SUGGESTION_MIN_LENGTH = 3;

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
  // The category was picked explicitly (by the user, or prefilled by the chat):
  // never overwrite it with a suggestion. Editing an existing expense counts too.
  const [categoryTouched, setCategoryTouched] = useState(
    Boolean(initial || initialValues?.category_id),
  );
  const [suggestionSource, setSuggestionSource] = useState<
    CategorySuggestion["source"] | null
  >(null);

  // If the available categories list arrives after initial render, fill it in.
  useEffect(() => {
    if (!categoryId && categories[0]) setCategoryId(categories[0].id);
  }, [categories, categoryId]);

  // Pre-select the category learned from the user's corrections/history.
  useEffect(() => {
    const text = description.trim();
    if (categoryTouched || text.length < SUGGESTION_MIN_LENGTH) return;
    let cancelled = false;
    const timer = setTimeout(() => {
      suggestCategory(text)
        .then((suggestion) => {
          if (cancelled || !suggestion) return;
          if (!categories.some((c) => c.id === suggestion.category.id)) return;
          setCategoryId(suggestion.category.id);
          setSuggestionSource(suggestion.source);
        })
        .catch(() => {
          // Suggestions are best-effort; the user can always pick manually.
        });
    }, SUGGESTION_DEBOUNCE_MS);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [description, categoryTouched, categories]);

  function handleCategoryChange(value: string) {
    setCategoryId(value);
    setCategoryTouched(true);
    setSuggestionSource(null);
  }

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
        // The next description may suggest a different category again.
        setAmount("");
        setDescription("");
        setCategoryTouched(false);
        setSuggestionSource(null);
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
          onChange={(e) => handleCategoryChange(e.target.value)}
          aria-describedby={suggestionSource ? "category-suggestion" : undefined}
        >
          {categories.map((c) => (
            <option key={c.id} value={c.id}>
              {c.icon ? `${c.icon}  ` : ""}
              {c.name}
            </option>
          ))}
        </select>
        {suggestionSource && (
          <p id="category-suggestion" className="mt-1 text-xs text-ink-muted">
            {suggestionSource === "learned"
              ? t("categorySuggestedLearned")
              : t("categorySuggestedHistory")}
          </p>
        )}
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
