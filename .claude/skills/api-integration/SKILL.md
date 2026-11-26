---
name: api-integration
description: Use this skill when adding new frontend features that call the Expense Tracker backend, or when adding new API methods, types, or hooks. It documents the existing client patterns so new code stays consistent. Trigger this skill any time you would touch `frontend/src/lib/api.ts`, `frontend/src/types/api.ts`, or create a component that fetches from the API.
---

# Expense Tracker Frontend — API Integration

## Where things live

- `src/types/api.ts` — hand-written TypeScript mirrors of the backend
  Pydantic schemas. **Keep these in sync** when the API changes. If the
  API surface grows large, switch to `openapi-typescript` generation.

- `src/lib/api.ts` — the API client. Single source of `fetch` calls.
  Handles auth header injection, JSON parsing, and error mapping.

- `src/components/auth/AuthProvider.tsx` — auth context with `user`, `loading`,
  `loginWithGoogle`, `devLogin`, `logout`.

- `src/lib/format.ts` — pure currency/date formatting helpers. Accept a
  locale argument; default is `pt-PT`. Prefer the locale-aware `useFormat()`
  hook (see Internationalization below) in components.

- `src/components/LocaleProvider.tsx` — i18n state (`useLocale()` →
  `{ locale, setLocale }`). Sits above `AuthProvider` in the layout tree.

- `src/lib/i18n.ts` — `SUPPORTED_LOCALES`, `detectBrowserLocale`,
  `toIntlLocale` (maps `pt` → `pt-PT`, `en` → `en-IE`).

- `frontend/messages/{en,pt}.json` — translation namespaces consumed by
  `next-intl`.

## Adding a new API call

1. Add the request/response types to `src/types/api.ts`. Match the backend
   Pydantic field names exactly — no `camelCase` translation.

2. Add the function to `src/lib/api.ts`. Use the `request<T>` helper; never
   call `fetch` directly. It handles token injection and error mapping.

3. From a component, call it inside `useEffect` (one-shot) or wrap with
   TanStack Query if you add it later. Cancel/dedupe is currently the
   caller's responsibility — see `Dashboard.tsx` for the debounce pattern
   on the filter inputs.

## Conventions

- Components that need auth state use `useAuth()` and assume they're
  inside `<AuthProvider>`.
- Errors from `request<T>` are `ApiError` with `status` and `message`. Show
  them inline (`role="alert"`), don't toast.
- Forms use uncontrolled-ish patterns (single `useState` per field). For
  more than ~5 fields, switch to react-hook-form.
- All amounts are strings on the wire (`Decimal` from the backend). Convert
  with `Number(...)` only for math; format with `formatCurrency` for
  display.
- Dates are `YYYY-MM-DD` strings. Use `formatDate` to display, `todayIso` /
  `currentMonthIso` for defaults.

## Internationalization

Two languages: `en` (default) and `pt`. Translations live entirely on the
frontend; the backend just stores the chosen language on `users.language`
and uses it to pick the chat system prompt.

**Adding a new user-facing string:**

1. Pick a namespace in `frontend/messages/en.json` (e.g. `dashboard`,
   `expenses`, `chat`). Add the key + English text. Add the same key to
   `pt.json` with the Portuguese translation. **Both files must stay in
   sync** — missing keys throw at render time.
2. In the component (must be a client component), use:
   ```tsx
   import { useTranslations } from "next-intl";
   const t = useTranslations("expenses");
   <button>{t("addExpense")}</button>
   ```
3. For pluralization, use ICU syntax:
   `"expenseCount": "{count, plural, one {# expense} other {# expenses}}"`
   then `t("expenseCount", { count: total })`.

**Locale-aware formatting:** in components, use the `useFormat()` hook
instead of the static helpers — it picks up the current locale:

```tsx
import { useFormat } from "@/lib/useFormat";
const { formatCurrency, formatDate } = useFormat();
```

**Switching locale:** `useLocale().setLocale("pt")` updates the UI
immediately, persists to `localStorage`, and PATCHes `/auth/me` so the
preference survives across devices and the chat bot follows along.

## Styling

- Tailwind only. Custom classes are defined in `src/app/globals.css` under
  `@layer components` — `field`, `label`, `btn-primary`, `btn-ghost`,
  `btn-danger`, `text-amount`.
- Don't introduce a UI kit. If a one-off component needs a new pattern,
  add it locally; if a pattern repeats 3+ times, promote it to
  `globals.css`.

## When porting to mobile

`src/types/api.ts` and `src/lib/format.ts` are 100% portable. `src/lib/api.ts`
needs one substitution: replace the three `localStorage` calls with
`expo-secure-store`. `AuthProvider.tsx` and `LocaleProvider.tsx` are also
portable as-is — just swap the `localStorage` calls in `LocaleProvider`
for AsyncStorage. See `docs/MOBILE_EVOLUTION.md`.
