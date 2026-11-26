"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";

import * as api from "@/lib/api";
import { saveBlob } from "@/lib/download";

import { useImportExportError } from "./useImportExportError";

export function ExportCard() {
  const t = useTranslations("importExport.export");
  const errorMessage = useImportExportError();
  const year = new Date().getFullYear();
  const [dateFrom, setDateFrom] = useState(`${year}-01-01`);
  const [dateTo, setDateTo] = useState(`${year}-12-31`);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const rangeInvalid = Boolean(dateFrom && dateTo && dateFrom > dateTo);

  async function handleExport() {
    setBusy(true);
    setError(null);
    try {
      const blob = await api.exportExpensesCsv(dateFrom, dateTo);
      saveBlob(blob, `${t("filePrefix")}_${dateFrom}_${dateTo}.csv`);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="bg-paper-card border border-paper-line rounded shadow-card p-6 space-y-4">
      <div>
        <h2 className="font-display text-2xl text-ink">{t("title")}</h2>
        <p className="text-sm text-ink-muted mt-1">{t("intro")}</p>
      </div>

      <div className="flex flex-wrap items-end gap-4">
        <div>
          <label htmlFor="export-from" className="label">
            {t("from")}
          </label>
          <input
            id="export-from"
            type="date"
            className="field"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            required
          />
        </div>
        <div>
          <label htmlFor="export-to" className="label">
            {t("to")}
          </label>
          <input
            id="export-to"
            type="date"
            className="field"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            required
          />
        </div>
        <button
          type="button"
          className="btn-primary"
          onClick={handleExport}
          disabled={busy || rangeInvalid || !dateFrom || !dateTo}
        >
          {busy ? t("exporting") : t("button")}
        </button>
      </div>

      {rangeInvalid && (
        <p className="text-sm text-accent" role="alert">
          {t("invalidRange")}
        </p>
      )}
      {error && (
        <p className="text-sm text-accent" role="alert">
          {error}
        </p>
      )}
      <p className="text-xs text-ink-muted">{t("note")}</p>
    </section>
  );
}
