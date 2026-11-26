"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";

import { useFormat } from "@/lib/useFormat";
import type { Category, CategoryHint } from "@/types/api";

interface Props {
  hints: CategoryHint[];
  loading: boolean;
  /** Active categories the user can re-point a hint to. */
  categories: Category[];
  onChangeCategory: (hintId: string, categoryId: string) => Promise<void>;
  onDelete: (hintId: string) => Promise<void>;
}

/** "What I learned": descriptions whose category the app learned from the user's corrections. */
export function LearnedHintsSection({
  hints,
  loading,
  categories,
  onChangeCategory,
  onDelete,
}: Props) {
  const t = useTranslations("categories.learned");
  const tCommon = useTranslations("common");
  const { formatDate } = useFormat();
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function run(hintId: string, action: () => Promise<void>) {
    setBusyId(hintId);
    setError(null);
    try {
      await action();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("saveFailed"));
    } finally {
      setBusyId(null);
    }
  }

  return (
    <section className="space-y-3" aria-labelledby="learned-hints-title">
      <div>
        <h2 id="learned-hints-title" className="font-display text-2xl text-ink">
          {t("title")}
        </h2>
        <p className="text-sm text-ink-muted mt-1">{t("subtitle")}</p>
      </div>

      {error && (
        <p className="text-sm text-accent" role="alert">
          {error}
        </p>
      )}

      {loading ? (
        <p className="text-sm text-ink-muted">{tCommon("loading")}</p>
      ) : hints.length === 0 ? (
        <p className="text-sm text-ink-muted">{t("empty")}</p>
      ) : (
        <ul className="bg-paper-card border border-paper-line rounded shadow-card divide-y divide-paper-line">
          {hints.map((hint) => {
            const busy = busyId === hint.id;
            const archived = !hint.category.is_active;
            const selectId = `hint-category-${hint.id}`;
            return (
              <li
                key={hint.id}
                className="px-4 py-3 flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4"
              >
                <div className="min-w-0 flex-1">
                  <p className="text-sm text-ink font-medium break-words">{hint.description}</p>
                  <p className="text-xs text-ink-muted">
                    {t("meta", {
                      count: hint.hit_count,
                      date: formatDate(hint.last_used_at.slice(0, 10)),
                    })}
                    {archived && ` · ${t("archivedCategory")}`}
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  <label htmlFor={selectId} className="sr-only">
                    {t("categoryLabel", { description: hint.description })}
                  </label>
                  <select
                    id={selectId}
                    className="field sm:w-48"
                    value={hint.category.id}
                    disabled={busy}
                    onChange={(e) => {
                      const categoryId = e.target.value;
                      void run(hint.id, () => onChangeCategory(hint.id, categoryId));
                    }}
                  >
                    {archived && (
                      <option value={hint.category.id} disabled>
                        {hint.category.icon ? `${hint.category.icon}  ` : ""}
                        {hint.category.name}
                      </option>
                    )}
                    {categories.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.icon ? `${c.icon}  ` : ""}
                        {c.name}
                      </option>
                    ))}
                  </select>
                  <button
                    type="button"
                    className="btn-danger shrink-0"
                    disabled={busy}
                    aria-label={t("forgetLabel", { description: hint.description })}
                    onClick={() => void run(hint.id, () => onDelete(hint.id))}
                  >
                    {t("forget")}
                  </button>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
