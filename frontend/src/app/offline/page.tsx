"use client";

import { useTranslations } from "next-intl";

// Served by the service worker when a navigation fails. Keep it free of any
// authenticated data: it is cached and shown to whoever opens the app offline.
export default function OfflinePage() {
  const t = useTranslations("pwa");
  return (
    <div className="min-h-[100dvh] flex items-center justify-center px-6">
      <div className="max-w-sm text-center space-y-4">
        <h1 className="font-display text-3xl text-ink">{t("offlineTitle")}</h1>
        <p className="text-sm text-ink-muted">{t("offlineBody")}</p>
        <button type="button" className="btn-primary" onClick={() => window.location.reload()}>
          {t("retry")}
        </button>
      </div>
    </div>
  );
}
