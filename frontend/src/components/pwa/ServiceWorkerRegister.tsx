"use client";

/**
 * Registers the service worker (production builds only) and, when a new
 * version finishes installing, offers the user a reload instead of swapping
 * the app under their feet.
 */

import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

export function ServiceWorkerRegister() {
  const t = useTranslations("pwa");
  const [waiting, setWaiting] = useState<ServiceWorker | null>(null);

  useEffect(() => {
    // In dev the SW would cache stale HMR bundles; keep it production-only.
    if (process.env.NODE_ENV !== "production") return;
    if (!("serviceWorker" in navigator)) return;

    let reloading = false;
    const onControllerChange = () => {
      if (reloading) return;
      reloading = true;
      window.location.reload();
    };

    const watch = (registration: ServiceWorkerRegistration) => {
      // A worker may already be waiting from a previous visit.
      if (registration.waiting && navigator.serviceWorker.controller) {
        setWaiting(registration.waiting);
      }
      registration.addEventListener("updatefound", () => {
        const installing = registration.installing;
        if (!installing) return;
        installing.addEventListener("statechange", () => {
          if (installing.state === "installed" && navigator.serviceWorker.controller) {
            setWaiting(installing);
          }
        });
      });
    };

    navigator.serviceWorker.addEventListener("controllerchange", onControllerChange);
    navigator.serviceWorker
      .register("/sw.js", { scope: "/" })
      .then(watch)
      .catch(() => undefined);

    return () => {
      navigator.serviceWorker.removeEventListener("controllerchange", onControllerChange);
    };
  }, []);

  if (!waiting) return null;

  return (
    <div
      role="status"
      className="fixed inset-x-4 bottom-4 z-[60] mx-auto flex max-w-sm items-center justify-between gap-3 rounded border border-paper-line bg-paper-card px-4 py-3 shadow-card pb-[max(0.75rem,env(safe-area-inset-bottom))]"
    >
      <p className="text-sm text-ink">{t("updateAvailable")}</p>
      <button
        type="button"
        className="btn-primary !px-3 !py-1.5 text-sm"
        onClick={() => waiting.postMessage({ type: "SKIP_WAITING" })}
      >
        {t("reload")}
      </button>
    </div>
  );
}
