"use client";

import { useCallback, useEffect, useState } from "react";
import * as api from "@/lib/api";
import type { Expense, ExpenseFilters } from "@/types/api";

export function useExpenses(filters: ExpenseFilters) {
  const [expenses, setExpenses] = useState<Expense[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchExpenses = useCallback(
    async (showLoading = true) => {
      if (showLoading) setLoading(true);
      try {
        const res = await api.listExpenses(filters);
        setExpenses(res.items);
        setTotal(res.total);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Load failed");
      } finally {
        setLoading(false);
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [JSON.stringify(filters)]
  );

  useEffect(() => {
    const hasTextSearch = Boolean(
      filters.description_contains && filters.description_contains.length > 0
    );
    const delay = hasTextSearch ? 200 : 0;
    const t = setTimeout(() => fetchExpenses(), delay);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [JSON.stringify(filters)]);

  const refresh = useCallback(() => fetchExpenses(false), [fetchExpenses]);

  return { expenses, total, loading, error, refresh };
}
