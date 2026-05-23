"use client";

import { CategoryList } from "@/components/CategoryList";
import { useCategories } from "@/hooks/useCategories";

export default function CategoriesPage() {
  const { categories, loading } = useCategories();

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-3xl text-ink">Categories</h1>
        <p className="text-sm text-ink-muted mt-1">
          Available spending categories.
        </p>
      </div>

      {loading ? (
        <p className="text-sm text-ink-muted">Loading…</p>
      ) : (
        <CategoryList categories={categories} />
      )}
    </div>
  );
}
