"use client";

/**
 * Locale-aware versions of `formatCurrency` / `formatDate`. Components should
 * prefer these over the static helpers in `format.ts` so that switching
 * language updates numbers and dates without a reload.
 */

import { useMemo } from "react";

import { useLocale } from "@/components/LocaleProvider";
import { formatCurrency as baseFormatCurrency, formatDate as baseFormatDate } from "@/lib/format";
import { toIntlLocale } from "@/lib/i18n";

export function useFormat() {
  const { locale } = useLocale();
  return useMemo(() => {
    const intlLocale = toIntlLocale(locale);
    return {
      formatCurrency: (amount: string | number, currency: string = "EUR") =>
        baseFormatCurrency(amount, currency, intlLocale),
      formatDate: (isoDate: string) => baseFormatDate(isoDate, intlLocale),
      locale,
      intlLocale,
    };
  }, [locale]);
}
