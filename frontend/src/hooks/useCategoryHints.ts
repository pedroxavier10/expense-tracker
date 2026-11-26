"use client";

import { useCallback, useEffect, useState } from "react";
import * as api from "@/lib/api";
import type { CategoryHint } from "@/types/api";

export function useCategoryHints() {
  const [hints, setHints] = useState<CategoryHint[]>([]);
  const [loading, setLoading] = useState(true);

  const refetch = useCallback(() => {
    setLoading(true);
    return api
      .listCategoryHints()
      .then(setHints)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    refetch();
  }, [refetch]);

  return { hints, loading, refetch };
}
