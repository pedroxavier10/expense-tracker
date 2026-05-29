"use client";

import { useTranslations } from "next-intl";

import { CategoryList } from "@/components/categories/CategoryList";
import { useCategories } from "@/hooks/useCategories";

export default function CategoriesPage() {
  const { categories, loading } = useCategories();
  const t = useTranslations("categories");
  const tCommon = useTranslations("common");

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-3xl text-ink">{t("title")}</h1>
        <p className="text-sm text-ink-muted mt-1">{t("subtitle")}</p>
      </div>

      {loading ? (
        <p className="text-sm text-ink-muted">{tCommon("loading")}</p>
      ) : (
        <CategoryList categories={categories} />
      )}
    </div>
  );
}
