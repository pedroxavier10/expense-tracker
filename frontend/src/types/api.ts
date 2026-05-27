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
}

export interface Expense {
  id: string;
  amount: string; // Decimal serialized as string by the API
  expense_date: string; // ISO date (YYYY-MM-DD)
  description: string;
  category: Category;
  created_at: string;
  updated_at: string;
}

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
