"use client";

import { useEffect, useState } from "react";
import * as api from "@/lib/api";
import type { Category } from "@/types/api";

export function useCategories() {
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .listCategories()
      .then(setCategories)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  return { categories, loading };
}
