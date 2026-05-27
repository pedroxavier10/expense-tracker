"use client";

/**
 * Locale state for the whole app.
 *
 * Sits above AuthProvider so the login screen can also be translated. The
 * initial value is read from `localStorage["app_locale"]`, falling back to the
 * browser language. Once the user logs in, AuthProvider calls `setLocale` with
 * the value coming from `users.language` to sync the UI with the backend.
 *
 * Every `setLocale` call best-effort PATCHes the user (if a token is present).
 */

import { NextIntlClientProvider, type AbstractIntlMessages } from "next-intl";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

import * as api from "@/lib/api";
import {
  DEFAULT_LOCALE,
  detectBrowserLocale,
  isLocale,
  toIntlLocale,
  type Locale,
} from "@/lib/i18n";
import enMessages from "../../messages/en.json";
import ptMessages from "../../messages/pt.json";

const MESSAGES: Record<Locale, AbstractIntlMessages> = {
  en: enMessages as AbstractIntlMessages,
  pt: ptMessages as AbstractIntlMessages,
};

const STORAGE_KEY = "app_locale";

interface LocaleState {
  locale: Locale;
  setLocale: (next: Locale, options?: { persist?: boolean }) => void;
}

const LocaleContext = createContext<LocaleState | null>(null);

export function LocaleProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(DEFAULT_LOCALE);

  // Initial locale: localStorage → browser → default. Runs client-side only.
  useEffect(() => {
    if (typeof window === "undefined") return;
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (stored && isLocale(stored)) {
      setLocaleState(stored);
    } else {
      setLocaleState(detectBrowserLocale());
    }
  }, []);

  // Keep the document language attribute in sync for accessibility / SEO.
  useEffect(() => {
    if (typeof document !== "undefined") {
      document.documentElement.lang = locale;
    }
  }, [locale]);

  const setLocale = useCallback(
    (next: Locale, options?: { persist?: boolean }) => {
      setLocaleState(next);
      if (typeof window !== "undefined") {
        window.localStorage.setItem(STORAGE_KEY, next);
      }
      const persist = options?.persist ?? true;
      if (persist && api.getToken()) {
        // Best-effort: failures are non-fatal (offline, etc.).
        void api.updateMe({ language: next }).catch(() => undefined);
      }
    },
    [],
  );

  return (
    <LocaleContext.Provider value={{ locale, setLocale }}>
      <NextIntlClientProvider
        locale={toIntlLocale(locale)}
        messages={MESSAGES[locale]}
        timeZone="UTC"
      >
        {children}
      </NextIntlClientProvider>
    </LocaleContext.Provider>
  );
}

export function useLocale(): LocaleState {
  const ctx = useContext(LocaleContext);
  if (!ctx) throw new Error("useLocale must be used inside <LocaleProvider>");
  return ctx;
}
