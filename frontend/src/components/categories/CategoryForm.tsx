"use client";

import { useTranslations } from "next-intl";
import { useState, type FormEvent } from "react";

import { EmojiPicker } from "@/components/categories/EmojiPicker";
import type { Category, CategoryCreatePayload } from "@/types/api";

interface Props {
  initial?: Category;
  onSubmit: (data: CategoryCreatePayload) => Promise<void>;
  onCancel?: () => void;
  submitLabel?: string;
}

export function CategoryForm({ initial, onSubmit, onCancel, submitLabel }: Props) {
  const t = useTranslations("categories");
  const tCommon = useTranslations("common");
  const [name, setName] = useState(initial?.name ?? "");
  const [icon, setIcon] = useState<string | null>(initial?.icon ?? null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await onSubmit({ name: name.trim(), icon });
    } catch (err) {
      setError(err instanceof Error ? err.message : tCommon("save"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label htmlFor="category-name" className="label">
          {t("nameLabel")}
        </label>
        <input
          id="category-name"
          type="text"
          required
          maxLength={100}
          className="field"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder={t("namePlaceholder")}
        />
        <p className="text-xs text-ink-muted mt-1">{t("slugAutoNote")}</p>
      </div>

      <div>
        <label className="label">{t("iconLabel")}</label>
        <EmojiPicker value={icon} onChange={setIcon} />
      </div>

      {error && (
        <p className="text-sm text-accent" role="alert">
          {error}
        </p>
      )}

      <div className="flex items-center gap-2 pt-2">
        <button type="submit" disabled={busy} className="btn-primary">
          {busy ? tCommon("saving") : submitLabel ?? tCommon("save")}
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
