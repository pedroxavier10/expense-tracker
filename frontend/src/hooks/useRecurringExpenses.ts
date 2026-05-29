"use client";

import { useCallback, useEffect, useState } from "react";
import * as api from "@/lib/api";
import type { RecurringExpense } from "@/types/api";

export function useRecurringExpenses() {
  const [rules, setRules] = useState<RecurringExpense[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchRules = useCallback(async (showLoading = true) => {
    if (showLoading) setLoading(true);
    try {
      const data = await api.listRecurringExpenses();
      setRules(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Load failed");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRules();
  }, [fetchRules]);

  const refresh = useCallback(() => fetchRules(false), [fetchRules]);

  return { rules, loading, error, refresh };
}
