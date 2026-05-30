"use client";

import { useTranslations } from "next-intl";
import { useEffect } from "react";

import { CategoryForm } from "@/components/categories/CategoryForm";
import type { CategoryCreatePayload } from "@/types/api";

interface Props {
  onSubmit: (data: CategoryCreatePayload) => Promise<void>;
  onClose: () => void;
}

export function AddCategoryModal({ onSubmit, onClose }: Props) {
  const t = useTranslations("categories");
  const tCommon = useTranslations("common");

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [onClose]);

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="category-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center"
    >
      <div className="absolute inset-0 bg-ink/40" onClick={onClose} />
      <div className="relative bg-paper-card border border-paper-line rounded shadow-card w-full max-w-md mx-4 p-6">
        <div className="flex items-center justify-between mb-5">
          <h2 id="category-modal-title" className="font-display text-2xl text-ink">
            {t("add")}
          </h2>
          <button onClick={onClose} className="btn-ghost" aria-label={tCommon("close")}>
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
              <path d="M2 2l12 12M14 2 2 14" />
            </svg>
          </button>
        </div>
        <CategoryForm
          submitLabel={t("add")}
          onCancel={onClose}
          onSubmit={async (data) => {
            await onSubmit(data);
            onClose();
          }}
        />
      </div>
    </div>
  );
}
