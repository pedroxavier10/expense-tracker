"use client";

import { useTranslations } from "next-intl";

import { ExportCard } from "@/components/import-export/ExportCard";
import { ImportCard } from "@/components/import-export/ImportCard";

export default function ImportExportPage() {
  const t = useTranslations("importExport");

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-3xl text-ink">{t("title")}</h1>
        <p className="text-sm text-ink-muted mt-1">{t("subtitle")}</p>
      </div>
      <ImportCard />
      <ExportCard />
    </div>
  );
}
