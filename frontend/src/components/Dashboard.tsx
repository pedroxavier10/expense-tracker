"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { useAuth } from "@/components/AuthProvider";
import { ExpenseForm } from "@/components/ExpenseForm";
import { ExpenseList } from "@/components/ExpenseList";
import { FilterBar, type FilterValues } from "@/components/FilterBar";
import * as api from "@/lib/api";
import { currentMonthIso } from "@/lib/format";
import type {
  Category,
  Expense,
  ExpenseCreatePayload,
  ExpenseFilters,
  ExpenseUpdatePayload,
} from "@/types/api";

const EMPTY_FILTERS: FilterValues = {
  categoryId: "",
  month: currentMonthIso(),
  dateFrom: "",
  dateTo: "",
  q: "",
  dateMode: "month",
};

function filtersToQuery(f: FilterValues): ExpenseFilters {
  const out: ExpenseFilters = { limit: 500 };
  if (f.categoryId) out.category_id = f.categoryId;
  if (f.q) out.description_contains = f.q;
  if (f.dateMode === "month") {
    if (f.month) out.month = f.month;
  } else {
    if (f.dateFrom) out.date_from = f.dateFrom;
    if (f.dateTo) out.date_to = f.dateTo;
  }
  return out;
}

export function Dashboard() {
  const { user, logout } = useAuth();
  const [categories, setCategories] = useState<Category[]>([]);
  const [expenses, setExpenses] = useState<Expense[]>([]);
  const [total, setTotal] = useState(0);
  const [filters, setFilters] = useState<FilterValues>(EMPTY_FILTERS);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Load categories once.
  useEffect(() => {
    api.listCategories().then(setCategories).catch(console.error);
  }, []);

  const query = useMemo(() => filtersToQuery(filters), [filters]);

  // Reload expenses whenever filters change. Debounce the text search a little.
  useEffect(() => {
    const t = setTimeout(() => {
      setLoading(true);
      api
        .listExpenses(query)
        .then((res) => {
          setExpenses(res.items);
          setTotal(res.total);
          setError(null);
        })
        .catch((err) => setError(err instanceof Error ? err.message : "Load failed"))
        .finally(() => setLoading(false));
    }, 200);
    return () => clearTimeout(t);
  }, [query]);

  const refresh = useCallback(async () => {
    const res = await api.listExpenses(query);
    setExpenses(res.items);
    setTotal(res.total);
  }, [query]);

  const handleCreate = useCallback(
    async (data: ExpenseCreatePayload | ExpenseUpdatePayload) => {
      await api.createExpense(data as ExpenseCreatePayload);
      await refresh();
    },
    [refresh]
  );

  const handleUpdate = useCallback(
    async (id: string, data: ExpenseUpdatePayload) => {
      await api.updateExpense(id, data);
      await refresh();
    },
    [refresh]
  );

  const handleDelete = useCallback(
    async (id: string) => {
      await api.deleteExpense(id);
      await refresh();
    },
    [refresh]
  );

  return (
    <div className="min-h-screen">
      <header className="border-b border-paper-line">
        <div className="max-w-5xl mx-auto px-6 py-6 flex items-center justify-between">
          <div>
            <h1 className="font-display text-3xl italic text-ink leading-none">
              Ledger
            </h1>
            <p className="text-xs text-ink-muted mt-1">{user?.email}</p>
          </div>
          <button onClick={logout} className="btn-ghost">
            Sign out
          </button>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-8 space-y-8">
        <section>
          <h2 className="font-display text-2xl text-ink mb-4">New expense</h2>
          <div className="bg-paper-card border border-paper-line rounded p-6 shadow-card">
            {categories.length > 0 ? (
              <ExpenseForm
                categories={categories}
                onSubmit={handleCreate}
                submitLabel="Add expense"
              />
            ) : (
              <p className="text-ink-muted text-sm">Loading categories…</p>
            )}
          </div>
        </section>

        <section className="space-y-4">
          <h2 className="font-display text-2xl text-ink">History</h2>

          <FilterBar
            categories={categories}
            value={filters}
            onChange={setFilters}
            onReset={() => setFilters(EMPTY_FILTERS)}
          />

          {error && (
            <p className="text-sm text-accent" role="alert">
              {error}
            </p>
          )}

          {loading ? (
            <p className="text-ink-muted text-sm">Loading…</p>
          ) : (
            <ExpenseList
              expenses={expenses}
              categories={categories}
              total={total}
              onUpdate={handleUpdate}
              onDelete={handleDelete}
            />
          )}
        </section>
      </main>

      <footer className="max-w-5xl mx-auto px-6 py-8 text-xs text-ink-muted">
        Built for personal use. API docs at{" "}
        <a
          href={`${
            process.env.NEXT_PUBLIC_API_URL?.replace(/\/api\/v1$/, "") ||
            "http://localhost:8000"
          }/docs`}
          target="_blank"
          rel="noreferrer"
          className="underline hover:text-ink"
        >
          /docs
        </a>
        .
      </footer>
    </div>
  );
}
