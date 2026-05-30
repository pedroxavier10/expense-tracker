"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";

import { CategoryForm } from "@/components/categories/CategoryForm";
import type { Category, CategoryUpdatePayload } from "@/types/api";

interface Props {
  categories: Category[];
  onUpdate: (id: string, payload: CategoryUpdatePayload) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
  onRestore: (id: string) => Promise<void>;
}

export function CategoryList({ categories, onUpdate, onDelete, onRestore }: Props) {
  const t = useTranslations("categories");
  const tCommon = useTranslations("common");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

  const active = categories.filter((c) => c.is_active);
  const archived = categories.filter((c) => !c.is_active);

  if (categories.length === 0) {
    return <p className="text-sm text-ink-muted">{t("noCategoriesFound")}</p>;
  }

  function renderCard(c: Category) {
    if (editingId === c.id) {
      return (
        <div
          key={c.id}
          className="bg-paper-card border border-paper-line rounded p-4 shadow-card col-span-2 sm:col-span-3 md:col-span-4"
        >
          <CategoryForm
            initial={c}
            submitLabel={tCommon("save")}
            onCancel={() => setEditingId(null)}
            onSubmit={async (data) => {
              await onUpdate(c.id, data);
              setEditingId(null);
            }}
          />
        </div>
      );
    }

    const isConfirming = confirmDeleteId === c.id;

    return (
      <div
        key={c.id}
        className="bg-paper-card border border-paper-line rounded p-4 shadow-card flex flex-col gap-3"
      >
        <div className="flex items-center gap-3">
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

        {isConfirming ? (
          <div className="space-y-2">
            <p className="text-xs text-ink-muted">{t("confirmDeleteNote")}</p>
            <div className="flex items-center gap-1">
              <button
                className="btn-danger"
                onClick={async () => {
                  await onDelete(c.id);
                  setConfirmDeleteId(null);
                }}
              >
                {tCommon("delete")}
              </button>
              <button className="btn-ghost" onClick={() => setConfirmDeleteId(null)}>
                {tCommon("no")}
              </button>
            </div>
          </div>
        ) : (
          <div className="flex items-center gap-1">
            <button className="btn-ghost" onClick={() => setEditingId(c.id)}>
              {tCommon("edit")}
            </button>
            <button className="btn-danger" onClick={() => setConfirmDeleteId(c.id)}>
              {tCommon("delete")}
            </button>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
        {active.map(renderCard)}
      </div>

      {archived.length > 0 && (
        <section className="space-y-3">
          <h2 className="text-xs uppercase tracking-[0.12em] text-ink-muted font-medium">
            {t("archived")}
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
            {archived.map((c) => (
              <div
                key={c.id}
                className="bg-paper-card border border-paper-line rounded p-4 shadow-card flex flex-col gap-3 opacity-60"
              >
                <div className="flex items-center gap-3">
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
                <button className="btn-ghost self-start" onClick={() => onRestore(c.id)}>
                  {t("restore")}
                </button>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
