"use client";

import { useCallback, useEffect, useState } from "react";
import * as api from "@/lib/api";
import type { Category } from "@/types/api";

export function useCategories(includeInactive = false) {
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);

  const refetch = useCallback(() => {
    setLoading(true);
    return api
      .listCategories(includeInactive)
      .then(setCategories)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [includeInactive]);

  useEffect(() => {
    refetch();
  }, [refetch]);

  return { categories, loading, refetch };
}
