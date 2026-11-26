/** Navigation destinations shared by the desktop Sidebar and the mobile BottomNav. */

export type NavKey =
  | "dashboard"
  | "expenses"
  | "recurring"
  | "categories"
  | "reports"
  | "chat"
  | "importExport";

export interface NavItem {
  href: string;
  key: NavKey;
  icon: React.ReactNode;
}

export const NAV_ITEMS: NavItem[] = [
  {
    href: "/dashboard",
    key: "dashboard",
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
    key: "expenses",
    icon: (
      <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M3 4h12M3 8h8M3 12h10" />
      </svg>
    ),
  },
  {
    href: "/recurring",
    key: "recurring",
    icon: (
      <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M4 9a5 5 0 1 1 1.5 3.5" />
        <path d="M4 13V9h4" />
      </svg>
    ),
  },
  {
    href: "/categories",
    key: "categories",
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
    href: "/import-export",
    key: "importExport",
    icon: (
      <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M6 3v10M3 10l3 3 3-3" />
        <path d="M12 15V5M9 8l3-3 3 3" />
      </svg>
    ),
  },
  {
    href: "/reports",
    key: "reports",
    icon: (
      <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M3 14V8M7 14V5M11 14V9M15 14V3" />
      </svg>
    ),
  },
  {
    href: "/chat",
    key: "chat",
    icon: (
      <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M2 4.5A1.5 1.5 0 0 1 3.5 3h11A1.5 1.5 0 0 1 16 4.5v7A1.5 1.5 0 0 1 14.5 13H7l-3 2.5V13H3.5A1.5 1.5 0 0 1 2 11.5v-7z" />
      </svg>
    ),
  },
];
