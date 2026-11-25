"use client";

import { useTranslations } from "next-intl";
import { useSyncExternalStore } from "react";

function subscribe(callback: () => void): () => void {
  window.addEventListener("online", callback);
  window.addEventListener("offline", callback);
  return () => {
    window.removeEventListener("online", callback);
    window.removeEventListener("offline", callback);
  };
}

const getSnapshot = () => navigator.onLine;
// Assume online during SSR/hydration to avoid a flash of the banner.
const getServerSnapshot = () => true;

export function OfflineIndicator() {
  const t = useTranslations("pwa");
  const online = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);

  if (online) return null;

  return (
    <div
      role="status"
      className="fixed inset-x-0 top-0 z-[60] bg-ink px-4 py-1.5 text-center text-xs text-paper pt-[max(0.375rem,env(safe-area-inset-top))]"
    >
      {t("offlineBanner")}
    </div>
  );
}
