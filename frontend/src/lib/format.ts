/**
 * Small formatting helpers. Locale-aware where it matters; defaults to EUR
 * since the project is built for a Portugal-based user, but `formatCurrency`
 * accepts overrides.
 */

export function formatCurrency(
  amount: string | number,
  currency: string = "EUR",
  locale: string = "pt-PT"
): string {
  const value = typeof amount === "string" ? Number(amount) : amount;
  return new Intl.NumberFormat(locale, {
    style: "currency",
    currency,
  }).format(value);
}

export function formatDate(isoDate: string, locale: string = "pt-PT"): string {
  // Parse as local date, not UTC, so YYYY-MM-DD doesn't drift across timezones.
  const [y, m, d] = isoDate.split("-").map(Number);
  const date = new Date(y, m - 1, d);
  return new Intl.DateTimeFormat(locale, {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(date);
}

export function todayIso(): string {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

export function currentMonthIso(): string {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  return `${y}-${m}`;
}
