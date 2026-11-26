"use client";

import { useTranslations } from "next-intl";

import { useFormat } from "@/lib/useFormat";
import type { DuplicateMode, ImportPreview } from "@/types/api";

interface Props {
  preview: ImportPreview;
  busy: boolean;
  onImport: (mode: DuplicateMode, confirmDuplicates: boolean) => void;
  onCancel: () => void;
}

export function ImportPreviewPanel({ preview, busy, onImport, onCancel }: Props) {
  const t = useTranslations("importExport.preview");
  const tRow = useTranslations("importExport.rowErrors");
  const tCommon = useTranslations("common");
  const { formatCurrency } = useFormat();

  const stats: { label: string; value: string | number }[] = [
    { label: t("totalRows"), value: preview.total_rows },
    { label: t("validRows"), value: preview.valid_rows },
    { label: t("invalidRows"), value: preview.invalid_rows.length },
    { label: t("duplicates"), value: preview.duplicates },
    { label: t("totalAmount"), value: formatCurrency(preview.total_amount) },
  ];

  return (
    <div className="border-t border-paper-line pt-4 space-y-4" aria-live="polite">
      <h3 className="font-display text-xl text-ink">{t("title")}</h3>

      <dl className="grid grid-cols-2 sm:grid-cols-5 gap-3">
        {stats.map((s) => (
          <div key={s.label} className="border border-paper-line rounded px-3 py-2">
            <dt className="text-xs text-ink-muted">{s.label}</dt>
            <dd className="text-lg text-ink text-amount">{s.value}</dd>
          </div>
        ))}
      </dl>

      {preview.inferred_categories > 0 && (
        <p className="text-sm text-ink-muted">
          {t("inferredCategories", { count: preview.inferred_categories })}
        </p>
      )}
      {preview.new_categories.length > 0 && (
        <CategoryChips label={t("newCategories")} names={preview.new_categories} />
      )}
      {preview.reactivated_categories.length > 0 && (
        <CategoryChips
          label={t("reactivatedCategories")}
          names={preview.reactivated_categories}
        />
      )}

      {preview.invalid_rows.length > 0 && (
        <div>
          <p className="label">{t("invalidTitle")}</p>
          <ul className="max-h-48 overflow-y-auto text-sm border border-paper-line rounded divide-y divide-paper-line">
            {preview.invalid_rows.map((row) => (
              <li key={row.line} className="px-3 py-1.5 flex gap-3">
                <span className="text-ink-muted shrink-0">{t("line", { line: row.line })}</span>
                <span className="text-ink">{tRow(row.code, { value: row.value })}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {preview.valid_rows === 0 ? (
        <div className="space-y-3">
          <p className="text-sm text-ink-muted">{t("nothingToImport")}</p>
          <button type="button" className="btn-ghost" onClick={onCancel}>
            {tCommon("cancel")}
          </button>
        </div>
      ) : preview.requires_confirmation ? (
        <div className="space-y-3 rounded border border-accent bg-accent-soft p-4" role="alert">
          <p className="text-sm text-ink">{t("duplicatesWarning", { count: preview.duplicates })}</p>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className="btn-primary"
              disabled={busy}
              onClick={() => onImport("import", true)}
            >
              {busy ? t("importing") : t("importAll")}
            </button>
            <button
              type="button"
              className="btn-ghost"
              disabled={busy}
              onClick={() => onImport("skip", true)}
            >
              {t("skipDuplicates")}
            </button>
            <button type="button" className="btn-ghost" disabled={busy} onClick={onCancel}>
              {tCommon("cancel")}
            </button>
          </div>
        </div>
      ) : (
        <div className="space-y-3">
          {preview.duplicates > 0 && (
            <p className="text-sm text-ink-muted">
              {t("duplicatesInfo", { count: preview.duplicates })}
            </p>
          )}
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className="btn-primary"
              disabled={busy}
              onClick={() => onImport("import", false)}
            >
              {busy ? t("importing") : t("importValid", { count: preview.valid_rows })}
            </button>
            <button type="button" className="btn-ghost" disabled={busy} onClick={onCancel}>
              {tCommon("cancel")}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function CategoryChips({ label, names }: { label: string; names: string[] }) {
  return (
    <div>
      <p className="label">{label}</p>
      <ul className="flex flex-wrap gap-2">
        {names.map((name) => (
          <li
            key={name}
            className="text-sm px-2 py-0.5 rounded border border-paper-line bg-paper text-ink"
          >
            {name}
          </li>
        ))}
      </ul>
    </div>
  );
}
