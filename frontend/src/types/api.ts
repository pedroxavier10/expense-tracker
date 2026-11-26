/**
 * Types mirroring the FastAPI schemas in `backend/app/schemas/`.
 *
 * Kept hand-written and deliberately small. If the API grows, switch to
 * auto-generated types from the OpenAPI spec (e.g. `openapi-typescript`).
 */

export interface Category {
  id: string;
  slug: string;
  name: string;
  icon: string | null;
  is_active: boolean;
}

export interface CategoryCreatePayload {
  name: string;
  icon?: string | null;
}

export interface CategoryUpdatePayload {
  name?: string;
  icon?: string | null;
  is_active?: boolean;
}

export interface CategoryDeleteResult {
  action: "deleted" | "archived";
  category: Category | null;
}

export interface Expense {
  id: string;
  amount: string; // Decimal serialized as string by the API
  expense_date: string; // ISO date (YYYY-MM-DD)
  description: string;
  category: Category;
  is_recurring: boolean;
  recurring_expense_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface RecurringExpense {
  id: string;
  amount: string;
  description: string;
  day_of_month: number;
  is_active: boolean;
  end_date: string | null;
  category: Category;
  created_at: string;
  updated_at: string;
}

export interface RecurringExpenseCreatePayload {
  amount: string;
  description: string;
  day_of_month: number;
  category_id: string;
  end_date?: string | null;
  is_active?: boolean;
}

export type RecurringExpenseUpdatePayload = Partial<RecurringExpenseCreatePayload>;

export interface ExpenseListResponse {
  items: Expense[];
  total: number;
  limit: number;
  offset: number;
}

export interface ExpenseCreatePayload {
  amount: string;
  expense_date: string;
  description: string;
  category_id: string;
}

export type ExpenseUpdatePayload = Partial<ExpenseCreatePayload>;

export interface ExpenseFilters {
  category_id?: string;
  category_slug?: string;
  date_from?: string;
  date_to?: string;
  month?: string; // YYYY-MM
  description_contains?: string;
  limit?: number;
  offset?: number;
}

export interface User {
  id: string;
  email: string;
  is_active: boolean;
  language: "en" | "pt";
  created_at: string;
}

export interface UserUpdatePayload {
  language?: "en" | "pt";
}

export interface Token {
  access_token: string;
  token_type: string;
}

export interface AuthConfig {
  google_enabled: boolean;
  google_client_id: string | null;
}

// ---------- Reports / summary ----------

export interface CategorySummary {
  category_id: string;
  slug: string;
  name: string;
  icon: string | null;
  total: string; // Decimal serialized as string
  count: number;
}

export interface MonthlySummaryResponse {
  month: string; // YYYY-MM
  total: string;
  count: number;
  by_category: CategorySummary[];
}

export interface MonthlyTotal {
  month: string; // YYYY-MM
  total: string;
}

export interface AnnualSummaryResponse {
  year: number;
  total: string;
  by_month: MonthlyTotal[];
  by_category: CategorySummary[];
}

// ---------- Chat ----------

export type ChatRole = "user" | "assistant";

export interface ChatMessage {
  role: ChatRole;
  content: string;
}

export type ChatStreamEvent =
  | { type: "text"; delta: string }
  | { type: "tool_use"; name: string; args: unknown }
  | { type: "tool_result"; name: string; ok: boolean }
  | {
      type: "client_action";
      action: string;
      payload: Record<string, unknown>;
    }
  | { type: "done" }
  | { type: "error"; message: string };
