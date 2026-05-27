"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuth } from "@/components/AuthProvider";

const NAV_ITEMS = [
  {
    href: "/dashboard",
    label: "Dashboard",
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
    label: "Expenses",
    icon: (
      <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M3 4h12M3 8h8M3 12h10" />
      </svg>
    ),
  },
  {
    href: "/categories",
    label: "Categories",
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
    label: "Reports",
    icon: (
      <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M3 14V8M7 14V5M11 14V9M15 14V3" />
      </svg>
    ),
  },
  {
    href: "/chat",
    label: "Chat",
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
      <div className={`px-4 py-5 border-b border-paper-line flex items-center ${collapsed ? "justify-center" : "justify-between"}`}>
        {collapsed ? (
          <span className="font-display italic text-xl text-ink leading-none">Lx</span>
        ) : (
          <span className="font-display italic text-xl text-ink leading-none">Ledger-x</span>
        )}
      </div>

      {/* Nav items */}
      <div className="flex-1 py-3 overflow-hidden">
        {NAV_ITEMS.map((item) => {
          const active = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              title={collapsed ? item.label : undefined}
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
              {!collapsed && <span>{item.label}</span>}
            </Link>
          );
        })}
      </div>

      {/* Footer: user + sign out + toggle */}
      <div className="border-t border-paper-line py-3 px-2 space-y-1">
        {!collapsed && user && (
          <p className="px-2 text-xs text-ink-muted truncate">{user.email}</p>
        )}
        <button
          onClick={logout}
          title={collapsed ? "Sign out" : undefined}
          className={`btn-ghost w-full ${collapsed ? "justify-center px-2" : ""}`}
        >
          <svg width="15" height="15" viewBox="0 0 15 15" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M6 2H2.5A1.5 1.5 0 0 0 1 3.5v8A1.5 1.5 0 0 0 2.5 13H6M10 10l3-2.5L10 5M13 7.5H5" />
          </svg>
          {!collapsed && <span>Sign out</span>}
        </button>
        <button
          onClick={toggle}
          title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          className={`btn-ghost w-full ${collapsed ? "justify-center px-2" : ""}`}
        >
          {collapsed ? (
            <svg width="15" height="15" viewBox="0 0 15 15" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M5 7.5h8M9 4l3 3.5L9 11" />
            </svg>
          ) : (
            <svg width="15" height="15" viewBox="0 0 15 15" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M10 7.5H2M6 11 3 7.5 6 4" />
            </svg>
          )}
          {!collapsed && <span>Collapse</span>}
        </button>
      </div>
    </nav>
  );
}
