"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { useRef, useState } from "react";

import * as api from "@/lib/api";
import { saveBlob } from "@/lib/download";
import { currentMonthIso } from "@/lib/format";
import type { DuplicateMode, ImportPreview, ImportResult } from "@/types/api";

import { ImportPreviewPanel } from "./ImportPreviewPanel";
import { useImportExportError } from "./useImportExportError";

export function ImportCard() {
  const t = useTranslations("importExport.import");
  const tResult = useTranslations("importExport.result");
  const errorMessage = useImportExportError();
  const fileInput = useRef<HTMLInputElement>(null);

  const [file, setFile] = useState<File | null>(null);
  const [defaultMonth, setDefaultMonth] = useState(currentMonthIso());
  const [preview, setPreview] = useState<ImportPreview | null>(null);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const formatRows: { column: string; required: boolean; rule: string }[] = [
    { column: "amount", required: true, rule: t("ruleAmount") },
    { column: "date", required: false, rule: t("ruleDate") },
    { column: "category", required: false, rule: t("ruleCategory") },
    { column: "description", required: false, rule: t("ruleDescription") },
  ];

  function reset() {
    setFile(null);
    setPreview(null);
    setResult(null);
    setError(null);
    if (fileInput.current) fileInput.current.value = "";
  }

  async function run<T>(action: () => Promise<T>): Promise<T | undefined> {
    setBusy(true);
    setError(null);
    try {
      return await action();
    } catch (err) {
      setError(errorMessage(err));
      return undefined;
    } finally {
      setBusy(false);
    }
  }

  async function handleTemplate() {
    const blob = await run(() => api.downloadImportTemplate());
    if (blob) saveBlob(blob, t("templateFileName"));
  }

  async function handlePreview() {
    if (!file) return;
    setResult(null);
    const data = await run(() => api.previewImport(file, defaultMonth));
    if (data) setPreview(data);
  }

  async function handleImport(duplicateMode: DuplicateMode, confirmDuplicates: boolean) {
    if (!file) return;
    const data = await run(() =>
      api.importExpenses(file, { defaultMonth, duplicateMode, confirmDuplicates })
    );
    if (data) {
      setPreview(null);
      setResult(data);
      setFile(null);
      if (fileInput.current) fileInput.current.value = "";
    }
  }

  return (
    <section className="bg-paper-card border border-paper-line rounded shadow-card p-6 space-y-5">
      <div>
        <h2 className="font-display text-2xl text-ink">{t("title")}</h2>
        <p className="text-sm text-ink-muted mt-1">{t("intro")}</p>
      </div>

      <details className="group border border-paper-line rounded" open>
        <summary className="cursor-pointer px-4 py-2 text-sm text-ink font-medium">
          {t("formatTitle")}
        </summary>
        <div className="px-4 pb-4 space-y-3">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-ink-muted border-b border-paper-line">
                  <th className="py-1.5 pr-4 font-normal">{t("colColumn")}</th>
                  <th className="py-1.5 pr-4 font-normal">{t("colRequired")}</th>
                  <th className="py-1.5 font-normal">{t("colRules")}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-paper-line">
                {formatRows.map((row) => (
                  <tr key={row.column} className="align-top">
                    <td className="py-1.5 pr-4 font-mono text-ink">{row.column}</td>
                    <td className="py-1.5 pr-4 text-ink">{row.required ? t("yes") : t("no")}</td>
                    <td className="py-1.5 text-ink-muted">{row.rule}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="text-xs text-ink-muted">{t("formatNotes")}</p>
          <div>
            <p className="label">{t("example")}</p>
            <pre className="text-xs bg-paper border border-paper-line rounded p-3 overflow-x-auto">
              {t("exampleCsv")}
            </pre>
          </div>
          <button type="button" className="btn-ghost" onClick={handleTemplate} disabled={busy}>
            {t("downloadTemplate")}
          </button>
        </div>
      </details>

      {result ? (
        <div className="space-y-2" role="status">
          <h3 className="font-display text-xl text-ink">{tResult("title")}</h3>
          <p className="text-sm text-ink">{tResult("imported", { count: result.imported })}</p>
          {result.skipped_duplicates > 0 && (
            <p className="text-sm text-ink-muted">
              {tResult("skippedDuplicates", { count: result.skipped_duplicates })}
            </p>
          )}
          {result.skipped_invalid > 0 && (
            <p className="text-sm text-ink-muted">
              {tResult("skippedInvalid", { count: result.skipped_invalid })}
            </p>
          )}
          {result.created_categories.length > 0 && (
            <p className="text-sm text-ink-muted">
              {tResult("createdCategories", {
                names: result.created_categories.map((c) => c.name).join(", "),
              })}
            </p>
          )}
          <div className="flex flex-wrap gap-2 pt-2">
            <Link href="/expenses" className="btn-primary">
              {tResult("viewExpenses")}
            </Link>
            <button type="button" className="btn-ghost" onClick={reset}>
              {tResult("importAnother")}
            </button>
          </div>
        </div>
      ) : (
        <div className="flex flex-wrap items-end gap-4">
          <div className="min-w-0 flex-1 basis-64">
            <label htmlFor="import-file" className="label">
              {t("fileLabel")}
            </label>
            <input
              id="import-file"
              ref={fileInput}
              type="file"
              accept=".csv,text/csv"
              className="field"
              onChange={(e) => {
                setFile(e.target.files?.[0] ?? null);
                setPreview(null);
                setError(null);
              }}
            />
          </div>
          <div>
            <label htmlFor="import-month" className="label">
              {t("defaultMonthLabel")}
            </label>
            <input
              id="import-month"
              type="month"
              className="field"
              value={defaultMonth}
              onChange={(e) => {
                setDefaultMonth(e.target.value || currentMonthIso());
                setPreview(null);
              }}
            />
          </div>
          <button
            type="button"
            className="btn-primary"
            onClick={handlePreview}
            disabled={!file || busy || preview !== null}
          >
            {busy && !preview ? t("checking") : t("preview")}
          </button>
        </div>
      )}

      {error && (
        <p className="text-sm text-accent" role="alert">
          {error}
        </p>
      )}

      {preview && !result && (
        <ImportPreviewPanel
          preview={preview}
          busy={busy}
          onImport={handleImport}
          onCancel={reset}
        />
      )}
    </section>
  );
}
