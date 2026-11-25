"use client";

/**
 * Mobile navigation (below the `md` breakpoint): a fixed bottom tab bar with the
 * four main destinations plus a "More" sheet holding the remaining routes,
 * language switch and sign out — everything the desktop Sidebar offers.
 */

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { useLocale } from "@/components/LocaleProvider";
import { NAV_ITEMS, type NavKey } from "@/components/layout/navItems";
import { SUPPORTED_LOCALES, type Locale } from "@/lib/i18n";

const PRIMARY_KEYS: NavKey[] = ["dashboard", "expenses", "recurring", "reports"];

const primaryItems = NAV_ITEMS.filter((item) => PRIMARY_KEYS.includes(item.key));
const secondaryItems = NAV_ITEMS.filter((item) => !PRIMARY_KEYS.includes(item.key));

export function BottomNav() {
  const pathname = usePathname();
  const t = useTranslations("sidebar");
  const tCommon = useTranslations("common");
  const { user, logout } = useAuth();
  const { locale, setLocale } = useLocale();
  const [moreOpen, setMoreOpen] = useState(false);

  useEffect(() => {
    setMoreOpen(false);
  }, [pathname]);

  useEffect(() => {
    if (!moreOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setMoreOpen(false);
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [moreOpen]);

  const moreActive = secondaryItems.some((item) => pathname === item.href);

  const tabClass = (active: boolean) =>
    `flex flex-1 min-h-[56px] flex-col items-center justify-center gap-0.5 text-[11px] transition-colors ${
      active ? "text-ink font-medium" : "text-ink-muted"
    }`;

  return (
    <>
      {moreOpen && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label={t("more")}
          className="md:hidden fixed inset-0 z-50 flex items-end"
        >
          <div className="absolute inset-0 bg-ink/40" onClick={() => setMoreOpen(false)} />
          <div className="relative w-full rounded-t border-t border-paper-line bg-paper-card px-4 pt-3 shadow-card pb-[max(1rem,env(safe-area-inset-bottom))]">
            <div className="mb-2 flex items-center justify-between">
              {user && <p className="truncate text-xs text-ink-muted">{user.email}</p>}
              <button
                type="button"
                className="btn-ghost ml-auto"
                onClick={() => setMoreOpen(false)}
                aria-label={tCommon("close")}
              >
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
                  <path d="M2 2l12 12M14 2 2 14" />
                </svg>
              </button>
            </div>

            <div className="space-y-1">
              {secondaryItems.map((item) => {
                const active = pathname === item.href;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={() => setMoreOpen(false)}
                    className={`flex min-h-[44px] items-center gap-3 rounded px-2 text-sm transition-colors ${
                      active ? "bg-paper-line/60 text-ink font-medium" : "text-ink-muted"
                    }`}
                  >
                    <span className="flex-shrink-0">{item.icon}</span>
                    <span>{t(item.key)}</span>
                  </Link>
                );
              })}
            </div>

            <div className="mt-3 flex items-center gap-2 border-t border-paper-line pt-3">
              <span className="text-xs text-ink-muted">{t("language")}</span>
              {SUPPORTED_LOCALES.map((code: Locale) => {
                const active = locale === code;
                return (
                  <button
                    key={code}
                    type="button"
                    onClick={() => setLocale(code)}
                    aria-pressed={active}
                    className={`min-h-[36px] rounded px-3 text-xs uppercase tracking-[0.12em] transition-colors ${
                      active ? "bg-ink text-paper" : "text-ink-muted"
                    }`}
                  >
                    {code}
                  </button>
                );
              })}
            </div>

            <button type="button" onClick={logout} className="btn-ghost mt-2 min-h-[44px] w-full justify-start">
              <svg width="15" height="15" viewBox="0 0 15 15" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M6 2H2.5A1.5 1.5 0 0 0 1 3.5v8A1.5 1.5 0 0 0 2.5 13H6M10 10l3-2.5L10 5M13 7.5H5" />
              </svg>
              <span>{t("signOut")}</span>
            </button>
          </div>
        </div>
      )}

      <nav
        aria-label={t("mainNavigation")}
        className="md:hidden fixed inset-x-0 bottom-0 z-40 flex border-t border-paper-line bg-paper-card pb-[env(safe-area-inset-bottom)]"
      >
        {primaryItems.map((item) => {
          const active = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              aria-current={active ? "page" : undefined}
              className={tabClass(active)}
            >
              {item.icon}
              <span>{t(item.key)}</span>
            </Link>
          );
        })}
        <button
          type="button"
          onClick={() => setMoreOpen(true)}
          aria-haspopup="dialog"
          aria-expanded={moreOpen}
          className={tabClass(moreActive || moreOpen)}
        >
          <svg width="18" height="18" viewBox="0 0 18 18" fill="currentColor">
            <circle cx="3.5" cy="9" r="1.4" />
            <circle cx="9" cy="9" r="1.4" />
            <circle cx="14.5" cy="9" r="1.4" />
          </svg>
          <span>{t("more")}</span>
        </button>
      </nav>
    </>
  );
}
