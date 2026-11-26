"use client";

import { useTranslations } from "next-intl";
import { useCallback, useState } from "react";

import { AddCategoryModal } from "@/components/categories/AddCategoryModal";
import { CategoryList } from "@/components/categories/CategoryList";
import { LearnedHintsSection } from "@/components/categories/LearnedHintsSection";
import { useCategories } from "@/hooks/useCategories";
import { useCategoryHints } from "@/hooks/useCategoryHints";
import * as api from "@/lib/api";
import type { CategoryCreatePayload, CategoryUpdatePayload } from "@/types/api";

export default function CategoriesPage() {
  // Include archived so they can be shown (and restored) on this page.
  const { categories, loading, refetch: refetchCategories } = useCategories(true);
  const { hints, loading: hintsLoading, refetch: refetchHints } = useCategoryHints();
  // Hints embed their category (name, icon, archived state), so refresh both
  // whenever a category changes.
  const refetch = useCallback(
    () => Promise.all([refetchCategories(), refetchHints()]),
    [refetchCategories, refetchHints]
  );
  const [showModal, setShowModal] = useState(false);
  const t = useTranslations("categories");
  const tCommon = useTranslations("common");

  const handleCreate = useCallback(
    async (data: CategoryCreatePayload) => {
      await api.createCategory(data);
      await refetch();
    },
    [refetch]
  );

  const handleUpdate = useCallback(
    async (id: string, data: CategoryUpdatePayload) => {
      await api.updateCategory(id, data);
      await refetch();
    },
    [refetch]
  );

  const handleDelete = useCallback(
    async (id: string) => {
      await api.deleteCategory(id);
      await refetch();
    },
    [refetch]
  );

  const handleRestore = useCallback(
    async (id: string) => {
      await api.updateCategory(id, { is_active: true });
      await refetch();
    },
    [refetch]
  );

  const handleHintCategoryChange = useCallback(
    async (hintId: string, categoryId: string) => {
      await api.updateCategoryHint(hintId, { category_id: categoryId });
      await refetchHints();
    },
    [refetchHints]
  );

  const handleHintDelete = useCallback(
    async (hintId: string) => {
      await api.deleteCategoryHint(hintId);
      await refetchHints();
    },
    [refetchHints]
  );

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl text-ink">{t("title")}</h1>
          <p className="text-sm text-ink-muted mt-1">{t("subtitle")}</p>
        </div>
        <button className="btn-primary shrink-0" onClick={() => setShowModal(true)}>
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <path d="M7 1v12M1 7h12" />
          </svg>
          {t("add")}
        </button>
      </div>

      {loading ? (
        <p className="text-sm text-ink-muted">{tCommon("loading")}</p>
      ) : (
        <CategoryList
          categories={categories}
          onUpdate={handleUpdate}
          onDelete={handleDelete}
          onRestore={handleRestore}
        />
      )}

      {!loading && (
        <LearnedHintsSection
          hints={hints}
          loading={hintsLoading}
          categories={categories.filter((c) => c.is_active)}
          onChangeCategory={handleHintCategoryChange}
          onDelete={handleHintDelete}
        />
      )}

      {showModal && (
        <AddCategoryModal onSubmit={handleCreate} onClose={() => setShowModal(false)} />
      )}
    </div>
  );
}
