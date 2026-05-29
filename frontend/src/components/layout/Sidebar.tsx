"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { useAuth } from "@/components/auth/AuthProvider";
import { useLocale } from "@/components/LocaleProvider";
import { SUPPORTED_LOCALES, type Locale } from "@/lib/i18n";

const NAV_ITEMS = [
  {
    href: "/dashboard",
    key: "dashboard" as const,
    icon: (
      <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <rect x="2" y="2" width="6" height="6" rx="1" />
        <rect x="10" y="2" width="6" height="6" rx="1" />
        <rect x="2" y="10" width="6" height="6" rx="1" />
        <rect x="10" y="10" width="6" height="6" rx="1" />
      </svg>
    ),
  },
  {
    href: "/expenses",
    key: "expenses" as const,
    icon: (
      <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M3 4h12M3 8h8M3 12h10" />
      </svg>
    ),
  },
  {
    href: "/recurring",
    key: "recurring" as const,
    icon: (
      <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M4 9a5 5 0 1 1 1.5 3.5" />
        <path d="M4 13V9h4" />
      </svg>
    ),
  },
  {
    href: "/categories",
    key: "categories" as const,
    icon: (
      <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="5" cy="5" r="2.5" />
        <circle cx="13" cy="5" r="2.5" />
        <circle cx="5" cy="13" r="2.5" />
        <circle cx="13" cy="13" r="2.5" />
      </svg>
    ),
  },
  {
    href: "/reports",
    key: "reports" as const,
    icon: (
      <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M3 14V8M7 14V5M11 14V9M15 14V3" />
      </svg>
    ),
  },
  {
    href: "/chat",
    key: "chat" as const,
    icon: (
      <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M2 4.5A1.5 1.5 0 0 1 3.5 3h11A1.5 1.5 0 0 1 16 4.5v7A1.5 1.5 0 0 1 14.5 13H7l-3 2.5V13H3.5A1.5 1.5 0 0 1 2 11.5v-7z" />
      </svg>
    ),
  },
];

export function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const { locale, setLocale } = useLocale();
  const t = useTranslations("sidebar");
  const tBrand = useTranslations("brand");

  useEffect(() => {
    const stored = localStorage.getItem("sidebar-collapsed");
    if (stored !== null) setCollapsed(stored === "true");
  }, []);

  const toggle = () => {
    setCollapsed((prev) => {
      const next = !prev;
      localStorage.setItem("sidebar-collapsed", String(next));
      return next;
    });
  };

  return (
    <nav
      className={`
        flex flex-col flex-shrink-0 border-r border-paper-line bg-paper-card
        transition-all duration-200 ease-in-out h-screen sticky top-0
        ${collapsed ? "w-[60px]" : "w-[220px]"}
      `}
    >
      {/* Brand */}
      <div className={`px-3 py-4 border-b border-paper-line flex items-center ${collapsed ? "flex-col gap-2" : "justify-between"}`}>
        {!collapsed && (
          <span className="font-display italic text-xl text-ink leading-none">
            {tBrand("name")}
          </span>
        )}
        <button
          onClick={toggle}
          title={collapsed ? t("expandSidebar") : t("collapseSidebar")}
          className="flex items-center justify-center w-8 h-8 rounded text-ink-muted hover:text-ink hover:bg-paper-line/40 transition-colors flex-shrink-0"
        >
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <rect x="2" y="2" width="14" height="14" rx="2" />
            <path d="M6 2v14" />
            {collapsed
              ? <path d="M9.5 7l2.5 2-2.5 2" />
              : <path d="M12 7l-2.5 2 2.5 2" />
            }
          </svg>
        </button>
        {collapsed && (
          <span className="font-display italic text-sm text-ink leading-none">Lx</span>
        )}
      </div>

      {/* Nav items */}
      <div className="flex-1 py-3 overflow-hidden">
        {NAV_ITEMS.map((item) => {
          const active = pathname === item.href;
          const label = t(item.key);
          return (
            <Link
              key={item.href}
              href={item.href}
              title={collapsed ? label : undefined}
              className={`
                flex items-center gap-3 mx-2 px-2 py-2 rounded text-sm transition-colors
                ${collapsed ? "justify-center" : ""}
                ${active
                  ? "bg-paper-line/60 text-ink font-medium"
                  : "text-ink-muted hover:text-ink hover:bg-paper-line/40"
                }
              `}
            >
              <span className="flex-shrink-0">{item.icon}</span>
              {!collapsed && <span>{label}</span>}
            </Link>
          );
        })}
      </div>

      {/* Footer: language + user + sign out + toggle */}
      <div className="border-t border-paper-line py-3 px-2 space-y-1">
        {!collapsed && (
          <div className="flex items-center gap-1 px-2 pb-1">
            {SUPPORTED_LOCALES.map((code: Locale) => {
              const active = locale === code;
              return (
                <button
                  key={code}
                  type="button"
                  onClick={() => setLocale(code)}
                  aria-pressed={active}
                  className={`text-xs uppercase tracking-[0.12em] px-2 py-1 rounded transition-colors ${
                    active
                      ? "bg-ink text-paper"
                      : "text-ink-muted hover:text-ink hover:bg-paper-line/40"
                  }`}
                >
                  {code}
                </button>
              );
            })}
          </div>
        )}
        {!collapsed && user && (
          <p className="px-2 text-xs text-ink-muted truncate">{user.email}</p>
        )}
        <button
          onClick={logout}
          title={collapsed ? t("signOut") : undefined}
          className={`btn-ghost w-full ${collapsed ? "justify-center px-2" : ""}`}
        >
          <svg width="15" height="15" viewBox="0 0 15 15" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M6 2H2.5A1.5 1.5 0 0 0 1 3.5v8A1.5 1.5 0 0 0 2.5 13H6M10 10l3-2.5L10 5M13 7.5H5" />
          </svg>
          {!collapsed && <span>{t("signOut")}</span>}
        </button>
      </div>
    </nav>
  );
}
