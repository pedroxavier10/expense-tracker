"use client";

import { useEffect } from "react";
import { ExpenseForm, type ExpenseFormInitialValues } from "@/components/ExpenseForm";
import type { Category, ExpenseCreatePayload, ExpenseUpdatePayload } from "@/types/api";

interface Props {
  categories: Category[];
  onSubmit: (data: ExpenseCreatePayload | ExpenseUpdatePayload) => Promise<void>;
  onClose: () => void;
  initialValues?: ExpenseFormInitialValues;
}

export function AddExpenseModal({ categories, onSubmit, onClose, initialValues }: Props) {
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
      aria-labelledby="modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center"
    >
      <div
        className="absolute inset-0 bg-ink/40"
        onClick={onClose}
      />
      <div className="relative bg-paper-card border border-paper-line rounded shadow-card w-full max-w-lg mx-4 p-6">
        <div className="flex items-center justify-between mb-5">
          <h2 id="modal-title" className="font-display text-2xl text-ink">
            Add Expense
          </h2>
          <button onClick={onClose} className="btn-ghost" aria-label="Close">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
              <path d="M2 2l12 12M14 2 2 14" />
            </svg>
          </button>
        </div>
        <ExpenseForm
          categories={categories}
          initialValues={initialValues}
          onSubmit={async (data) => {
            await onSubmit(data);
            onClose();
          }}
          submitLabel="Add expense"
          onCancel={onClose}
        />
      </div>
    </div>
  );
}
