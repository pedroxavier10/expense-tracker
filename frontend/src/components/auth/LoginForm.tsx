"use client";

import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useCallback, useEffect, useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { GoogleSignInButton } from "@/components/auth/GoogleSignInButton";
import { useLocale } from "@/components/LocaleProvider";
import { ApiError, getAuthConfig } from "@/lib/api";
import { toIntlLocale } from "@/lib/i18n";
import type { AuthConfig } from "@/types/api";

export function LoginForm() {
  const { loginWithGoogle, devLogin, user, loading } = useAuth();
  const { locale } = useLocale();
  const router = useRouter();
  const tLogin = useTranslations("login");
  const tBrand = useTranslations("brand");
  const [config, setConfig] = useState<AuthConfig | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!loading && user) router.replace("/dashboard");
  }, [loading, user, router]);

  useEffect(() => {
    getAuthConfig()
      .then(setConfig)
      .catch(() => setError(tLogin("googleUnavailable")));
  }, [tLogin]);

  const signIn = useCallback(
    async (action: () => Promise<void>) => {
      setBusy(true);
      setError(null);
      try {
        await action();
        router.push("/dashboard");
      } catch (err) {
        setError(
          err instanceof ApiError && err.status === 403
            ? tLogin("notAllowed")
            : tLogin("loginFailed"),
        );
      } finally {
        setBusy(false);
      }
    },
    [router, tLogin],
  );

  const onGoogleCredential = useCallback(
    (credential: string) => signIn(() => loginWithGoogle(credential)),
    [signIn, loginWithGoogle],
  );

  const onGoogleError = useCallback(() => setError(tLogin("googleUnavailable")), [tLogin]);

  return (
    <div className="min-h-screen flex items-center justify-center px-6">
      <div className="w-full max-w-sm">
        <div className="mb-12 text-center">
          <h1 className="font-display text-5xl italic text-ink mb-2">
            {tBrand("name")}
          </h1>
          <p className="text-ink-muted text-sm">{tBrand("loginTagline")}</p>
        </div>

        <div className="space-y-4">
          {config?.google_enabled && config.google_client_id && (
            <GoogleSignInButton
              clientId={config.google_client_id}
              locale={toIntlLocale(locale)}
              onCredential={onGoogleCredential}
              onError={onGoogleError}
            />
          )}

          {config && !config.google_enabled && (
            <>
              <button
                type="button"
                disabled={busy}
                className="btn-primary w-full"
                onClick={() => signIn(devLogin)}
              >
                {busy ? tLogin("signingIn") : tLogin("continueWithGoogle")}
              </button>
              <p className="text-center text-xs text-ink-muted">{tLogin("devMode")}</p>
            </>
          )}

          {busy && config?.google_enabled && (
            <p className="text-center text-sm text-ink-muted">{tLogin("signingIn")}</p>
          )}

          {error && (
            <p className="text-sm text-accent text-center" role="alert">
              {error}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
