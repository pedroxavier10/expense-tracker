/**
 * Thin fetch wrapper around the FastAPI backend.
 *
 * - Token is stored in localStorage under `auth_token`.
 * - All methods throw on non-2xx with a descriptive message.
 * - The same client will work for the future mobile app: replace the
 *   localStorage calls with SecureStore (Expo) or Keychain (native) and
 *   everything else stays.
 */

import type {
  AnnualSummaryResponse,
  AuthConfig,
  Category,
  CategoryCreatePayload,
  CategoryDeleteResult,
  CategoryUpdatePayload,
  ChatMessage,
  ChatStreamEvent,
  Expense,
  ExpenseCreatePayload,
  ExpenseFilters,
  ExpenseListResponse,
  ExpenseUpdatePayload,
  ImportOptions,
  ImportPreview,
  ImportResult,
  MonthlySummaryResponse,
  RecurringExpense,
  RecurringExpenseCreatePayload,
  RecurringExpenseUpdatePayload,
  Token,
  User,
  UserUpdatePayload,
} from "@/types/api";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

const TOKEN_KEY = "auth_token";

// ---------- Token storage ----------

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(TOKEN_KEY);
}

// ---------- Core request helper ----------

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(
  path: string,
  init: RequestInit & { skipAuth?: boolean } = {}
): Promise<T> {
  const { skipAuth, headers, ...rest } = init;
  const finalHeaders: Record<string, string> = {
    "Content-Type": "application/json",
    ...((headers as Record<string, string>) || {}),
  };

  if (!skipAuth) {
    const token = getToken();
    if (token) finalHeaders["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_URL}${path}`, {
    ...rest,
    headers: finalHeaders,
  });

  if (response.status === 204) {
    return undefined as T;
  }

  const text = await response.text();
  const body = text ? JSON.parse(text) : null;

  if (!response.ok) {
    const detail =
      body && typeof body === "object" && "detail" in body
        ? typeof body.detail === "string"
          ? body.detail
          : JSON.stringify(body.detail)
        : response.statusText;
    throw new ApiError(response.status, detail);
  }

  return body as T;
}

// ---------- Auth ----------

export async function getAuthConfig(): Promise<AuthConfig> {
  return request<AuthConfig>("/auth/config", { skipAuth: true });
}

/** Exchange a Google Identity Services credential (ID token) for an app token. */
export async function loginWithGoogle(credential: string): Promise<Token> {
  const token = await request<Token>("/auth/google", {
    method: "POST",
    body: JSON.stringify({ credential }),
    skipAuth: true,
  });
  setToken(token.access_token);
  return token;
}

/** Passwordless dev login. The backend only allows it when Google sign-in is disabled. */
export async function devLogin(): Promise<Token> {
  const token = await request<Token>("/auth/dev-login", {
    method: "POST",
    skipAuth: true,
  });
  setToken(token.access_token);
  return token;
}

export async function getMe(): Promise<User> {
  return request<User>("/auth/me");
}

export async function updateMe(payload: UserUpdatePayload): Promise<User> {
  return request<User>("/auth/me", {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function logout(): void {
  clearToken();
}

// ---------- Categories ----------

export async function listCategories(
  includeInactive = false
): Promise<Category[]> {
  const q = includeInactive ? "?include_inactive=true" : "";
  return request<Category[]>(`/categories${q}`);
}

export async function createCategory(
  payload: CategoryCreatePayload
): Promise<Category> {
  return request<Category>("/categories", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateCategory(
  id: string,
  payload: CategoryUpdatePayload
): Promise<Category> {
  return request<Category>(`/categories/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function deleteCategory(id: string): Promise<CategoryDeleteResult> {
  return request<CategoryDeleteResult>(`/categories/${id}`, {
    method: "DELETE",
  });
}

// ---------- Expenses ----------

function buildQuery(filters: ExpenseFilters): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value === undefined || value === null || value === "") continue;
    params.set(key, String(value));
  }
  const q = params.toString();
  return q ? `?${q}` : "";
}

export async function listExpenses(
  filters: ExpenseFilters = {}
): Promise<ExpenseListResponse> {
  return request<ExpenseListResponse>(`/expenses${buildQuery(filters)}`);
}

export async function createExpense(
  payload: ExpenseCreatePayload
): Promise<Expense> {
  return request<Expense>("/expenses", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateExpense(
  id: string,
  payload: ExpenseUpdatePayload
): Promise<Expense> {
  return request<Expense>(`/expenses/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function deleteExpense(id: string): Promise<void> {
  return request<void>(`/expenses/${id}`, { method: "DELETE" });
}

export async function getMonthSummary(month: string): Promise<MonthlySummaryResponse> {
  return request<MonthlySummaryResponse>(`/expenses/summary?month=${month}`);
}

export async function getAnnualSummary(year: number): Promise<AnnualSummaryResponse> {
  return request<AnnualSummaryResponse>(`/expenses/annual-summary?year=${year}`);
}

// ---------- Recurring Expenses ----------

export async function listRecurringExpenses(): Promise<RecurringExpense[]> {
  return request<RecurringExpense[]>("/recurring-expenses");
}

export async function createRecurringExpense(
  payload: RecurringExpenseCreatePayload
): Promise<RecurringExpense> {
  return request<RecurringExpense>("/recurring-expenses", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateRecurringExpense(
  id: string,
  payload: RecurringExpenseUpdatePayload
): Promise<RecurringExpense> {
  return request<RecurringExpense>(`/recurring-expenses/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function deleteRecurringExpense(id: string): Promise<void> {
  return request<void>(`/recurring-expenses/${id}`, { method: "DELETE" });
}

export async function materializeRecurringExpenseCurrentMonth(
  id: string
): Promise<Expense> {
  return request<Expense>(`/recurring-expenses/${id}/materialize-current-month`, {
    method: "POST",
  });
}

// ---------- CSV import / export ----------
// `request()` always sends and parses JSON, so file transfers use these two
// helpers (same Bearer token + ApiError behaviour).

function authHeader(): Record<string, string> {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function apiErrorFrom(res: Response): Promise<ApiError> {
  let detail = res.statusText;
  try {
    const body = await res.json();
    if (body && typeof body.detail === "string") detail = body.detail;
    else if (body && body.detail) detail = JSON.stringify(body.detail);
  } catch {
    // non-JSON error body: keep statusText
  }
  return new ApiError(res.status, detail);
}

async function requestBlob(path: string): Promise<Blob> {
  const res = await fetch(`${API_URL}${path}`, { headers: authHeader() });
  if (!res.ok) throw await apiErrorFrom(res);
  return res.blob();
}

async function requestForm<T>(path: string, form: FormData): Promise<T> {
  // No Content-Type: the browser sets multipart/form-data with its boundary.
  const res = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers: authHeader(),
    body: form,
  });
  if (!res.ok) throw await apiErrorFrom(res);
  return (await res.json()) as T;
}

export async function downloadImportTemplate(): Promise<Blob> {
  return requestBlob("/import-export/template");
}

export async function exportExpensesCsv(dateFrom: string, dateTo: string): Promise<Blob> {
  const qs = new URLSearchParams({ date_from: dateFrom, date_to: dateTo });
  return requestBlob(`/import-export/export?${qs.toString()}`);
}

export async function previewImport(file: File, defaultMonth: string): Promise<ImportPreview> {
  const form = new FormData();
  form.append("file", file);
  form.append("default_month", defaultMonth);
  return requestForm<ImportPreview>("/import-export/import/preview", form);
}

export async function importExpenses(file: File, options: ImportOptions): Promise<ImportResult> {
  const form = new FormData();
  form.append("file", file);
  form.append("default_month", options.defaultMonth);
  form.append("duplicate_mode", options.duplicateMode);
  form.append("confirm_duplicates", String(options.confirmDuplicates));
  return requestForm<ImportResult>("/import-export/import", form);
}

// ---------- Chat (SSE streaming) ----------

/**
 * POST /chat/stream and dispatch SSE events to `onEvent`.
 *
 * We can't use `EventSource` here: it only supports GET and cannot send the
 * Authorization header. So we use fetch + a manual reader over the response
 * body, splitting on the SSE `\n\n` boundary.
 */
export async function streamChat(
  messages: ChatMessage[],
  onEvent: (event: ChatStreamEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const token = getToken();
  const res = await fetch(`${API_URL}/chat/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ messages }),
    signal,
  });

  if (!res.ok || !res.body) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      if (body && typeof body.detail === "string") detail = body.detail;
    } catch {
      // ignore
    }
    throw new ApiError(res.status, detail);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() ?? "";
    for (const part of parts) {
      const dataLine = part
        .split("\n")
        .find((line) => line.startsWith("data: "));
      if (!dataLine) continue;
      try {
        onEvent(JSON.parse(dataLine.slice(6)) as ChatStreamEvent);
      } catch {
        // ignore malformed lines
      }
    }
  }
}

export { ApiError };
