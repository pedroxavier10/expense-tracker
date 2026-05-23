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

- `src/components/AuthProvider.tsx` — auth context with `user`, `loading`,
  `login`, `logout`.

- `src/lib/format.ts` — currency/date formatting helpers. Locale defaults
  to `pt-PT` / `EUR`.

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
`expo-secure-store`. `AuthProvider.tsx` is also portable as-is.
See `docs/MOBILE_EVOLUTION.md`.
