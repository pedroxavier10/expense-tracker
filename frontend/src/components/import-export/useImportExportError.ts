"use client";

import { useTranslations } from "next-intl";
import { useCallback } from "react";

import { ApiError } from "@/lib/api";

/** Map backend `detail` codes (e.g. `csv_too_large`) to translated messages. */
export function useImportExportError(): (err: unknown) => string {
  const t = useTranslations("importExport.errors");
  return useCallback(
    (err: unknown) => {
      if (err instanceof ApiError && t.has(err.message)) return t(err.message);
      if (err instanceof Error && err.message) return err.message;
      return t("generic");
    },
    [t]
  );
}
