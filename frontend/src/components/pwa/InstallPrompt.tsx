"use client";

/**
 * Inline "install the app" hint.
 *
 * - Chromium (Android/desktop): captures `beforeinstallprompt` and offers a button.
 * - iOS Safari: no install API exists, so a how-to hint is shown instead.
 * - Hidden when already running as an installed app or after being dismissed.
 */

import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

const DISMISSED_KEY = "pwa-install-dismissed";

function isStandalone(): boolean {
  const nav = navigator as Navigator & { standalone?: boolean };
  return window.matchMedia("(display-mode: standalone)").matches || nav.standalone === true;
}

function isIos(): boolean {
  const ua = navigator.userAgent;
  // iPadOS 13+ reports itself as a Mac with touch support.
  return /iphone|ipad|ipod/i.test(ua) || (ua.includes("Macintosh") && navigator.maxTouchPoints > 1);
}

function readDismissed(): boolean {
  try {
    return window.localStorage.getItem(DISMISSED_KEY) === "true";
  } catch {
    return false;
  }
}

export function InstallPrompt() {
  const t = useTranslations("pwa");
  const [deferred, setDeferred] = useState<BeforeInstallPromptEvent | null>(null);
  const [showIosHint, setShowIosHint] = useState(false);
  const [dismissed, setDismissed] = useState(true); // hidden until we know

  useEffect(() => {
    if (isStandalone() || readDismissed()) return;
    setDismissed(false);
    if (isIos()) setShowIosHint(true);

    const onBeforeInstall = (event: Event) => {
      event.preventDefault();
      setDeferred(event as BeforeInstallPromptEvent);
    };
    const onInstalled = () => setDeferred(null);

    window.addEventListener("beforeinstallprompt", onBeforeInstall);
    window.addEventListener("appinstalled", onInstalled);
    return () => {
      window.removeEventListener("beforeinstallprompt", onBeforeInstall);
      window.removeEventListener("appinstalled", onInstalled);
    };
  }, []);

  if (dismissed || (!deferred && !showIosHint)) return null;

  const dismiss = () => {
    setDismissed(true);
    try {
      window.localStorage.setItem(DISMISSED_KEY, "true");
    } catch {
      // Private mode etc.: the hint simply reappears next visit.
    }
  };

  const install = async () => {
    if (!deferred) return;
    await deferred.prompt();
    await deferred.userChoice;
    setDeferred(null);
  };

  return (
    <div className="mb-6 flex items-center justify-between gap-3 rounded border border-paper-line bg-paper-card px-4 py-3 shadow-card">
      <p className="text-sm text-ink">
        {deferred ? t("installBody") : t("installIosHint")}
      </p>
      <div className="flex flex-shrink-0 items-center gap-1">
        {deferred && (
          <button type="button" className="btn-primary !px-3 !py-1.5 text-sm" onClick={install}>
            {t("install")}
          </button>
        )}
        <button type="button" className="btn-ghost" onClick={dismiss} aria-label={t("dismiss")}>
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
            <path d="M2 2l12 12M14 2 2 14" />
          </svg>
        </button>
      </div>
    </div>
  );
}
