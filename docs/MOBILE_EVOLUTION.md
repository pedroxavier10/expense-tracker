# Mobile Evolution Guide

The backend is already API-first and stateless. Adding a mobile app is mostly
client work plus a few small server-side tweaks.

## Recommended stack

**Expo + React Native + TypeScript.**

- Reuse the `frontend/src/types/api.ts` file verbatim. It's plain TS, no Next
  dependencies — copy it into the mobile project or share it via a workspace.
- Reuse the API client (`frontend/src/lib/api.ts`) with one substitution:
  replace the `localStorage` calls with `expo-secure-store`. Everything else
  is the same fetch logic.
- TanStack Query is a good fit for the data layer (caching, retries, offline
  hints).

## What to change on the backend

Minimal. Things you'll want to add (none are blocking):

1. **Refresh tokens.** Right now we issue a 7-day access token. Mobile apps
   prefer short-lived access tokens (~15 min) plus a long-lived refresh
   token. Add a `RefreshToken` model and a `/auth/refresh` endpoint.
2. **Push token registration.** Add a `device_tokens` table keyed by user
   for future notifications ("you hit your monthly food budget").
3. **CORS** is not a concern for native — the mobile client doesn't enforce
   it. The current CORS config is web-only and you can ignore it on mobile.
4. **Account creation.** Currently disabled (seed-only). Add a `/auth/register`
   endpoint if you want self-service signup from the app.

## File-by-file translation (web → mobile)

| Web file                          | Mobile equivalent                            |
| --------------------------------- | -------------------------------------------- |
| `src/types/api.ts`                | identical                                    |
| `src/lib/api.ts`                  | swap `localStorage` for `expo-secure-store`  |
| `src/lib/format.ts`               | identical                                    |
| `src/components/AuthProvider.tsx` | identical (React context, not DOM)           |
| `src/components/ExpenseForm.tsx`  | rewrite using `<TextInput>` / native pickers |
| `src/components/ExpenseList.tsx`  | rewrite with `FlatList`                      |
| `src/components/FilterBar.tsx`    | rewrite, ideally as a bottom sheet           |

## Offline support (later)

The current API is straightforward to wrap with an offline-first client:

- Use TanStack Query's persistence layer + AsyncStorage.
- For writes, queue mutations locally and replay on reconnect — the API
  endpoints are idempotent enough (PATCH/DELETE are; POST isn't but a
  client-side UUID + an `Idempotency-Key` header would fix that).
- Add an `Idempotency-Key` header check to `POST /expenses` when this
  becomes a priority.

## Building both clients from one OpenAPI spec

The backend already publishes its OpenAPI spec at `/api/v1/openapi.json`.
Once stable, you can stop hand-writing types and use `openapi-typescript` to
generate them for both web and mobile from the same source of truth.
