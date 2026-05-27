/**
 * Internationalization primitives.
 *
 * Two languages supported: `en` and `pt` (pt-PT). Default is English.
 * The user's preference is persisted on the backend (`users.language`) and
 * mirrored to `localStorage` for fast hydration before the user is loaded.
 */

export const SUPPORTED_LOCALES = ["en", "pt"] as const;
export type Locale = (typeof SUPPORTED_LOCALES)[number];

export const DEFAULT_LOCALE: Locale = "en";

export function isLocale(value: string): value is Locale {
  return (SUPPORTED_LOCALES as readonly string[]).includes(value);
}

export function detectBrowserLocale(): Locale {
  if (typeof navigator === "undefined") return DEFAULT_LOCALE;
  const raw = navigator.language?.toLowerCase() ?? "";
  if (raw.startsWith("pt")) return "pt";
  return DEFAULT_LOCALE;
}

/**
 * BCP-47 tag used by `Intl.NumberFormat` / `Intl.DateTimeFormat`. We treat
 * `pt` as pt-PT (European Portuguese) and `en` as en-IE so that euros remain
 * the displayed currency while the number/date formatting follows the locale.
 */
export function toIntlLocale(locale: Locale): string {
  return locale === "pt" ? "pt-PT" : "en-IE";
}
