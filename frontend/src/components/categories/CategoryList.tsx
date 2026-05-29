"use client";

import { useTranslations } from "next-intl";

import type { Category } from "@/types/api";

interface Props {
  categories: Category[];
}

export function CategoryList({ categories }: Props) {
  const t = useTranslations("categories");
  if (categories.length === 0) {
    return <p className="text-sm text-ink-muted">{t("noCategoriesFound")}</p>;
  }

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
      {categories.map((c) => (
        <div
          key={c.id}
          className="bg-paper-card border border-paper-line rounded p-4 shadow-card flex items-center gap-3"
        >
          {c.icon ? (
            <span className="text-2xl leading-none flex-shrink-0">{c.icon}</span>
          ) : (
            <span className="w-7 h-7 rounded-full bg-paper-line flex-shrink-0" />
          )}
          <div className="min-w-0">
            <p className="text-sm text-ink font-medium truncate">{c.name}</p>
            <p className="text-xs text-ink-muted">{c.slug}</p>
          </div>
        </div>
      ))}
    </div>
  );
}
