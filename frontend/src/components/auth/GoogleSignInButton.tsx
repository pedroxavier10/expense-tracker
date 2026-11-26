"use client";

/**
 * Renders the official Google Identity Services (GIS) sign-in button.
 *
 * Loads https://accounts.google.com/gsi/client once and hands the resulting
 * credential (a Google ID token) to `onCredential`. The backend verifies it.
 */

import { useEffect, useRef, useState } from "react";

const GSI_SRC = "https://accounts.google.com/gsi/client";

interface GsiCredentialResponse {
  credential?: string;
}

interface GsiAccountsId {
  initialize(config: {
    client_id: string;
    callback: (response: GsiCredentialResponse) => void;
    ux_mode?: "popup" | "redirect";
    auto_select?: boolean;
  }): void;
  renderButton(
    parent: HTMLElement,
    options: {
      type?: "standard" | "icon";
      theme?: "outline" | "filled_blue" | "filled_black";
      size?: "large" | "medium" | "small";
      text?: "signin_with" | "signup_with" | "continue_with" | "signin";
      shape?: "rectangular" | "pill" | "circle" | "square";
      width?: number;
      locale?: string;
    },
  ): void;
}

declare global {
  interface Window {
    google?: { accounts: { id: GsiAccountsId } };
  }
}

let scriptPromise: Promise<void> | null = null;

function loadGsiScript(): Promise<void> {
  if (window.google?.accounts?.id) return Promise.resolve();
  if (!scriptPromise) {
    scriptPromise = new Promise<void>((resolve, reject) => {
      const script = document.createElement("script");
      script.src = GSI_SRC;
      script.async = true;
      script.defer = true;
      script.onload = () => resolve();
      script.onerror = () => {
        scriptPromise = null;
        reject(new Error("Failed to load Google Identity Services"));
      };
      document.head.appendChild(script);
    });
  }
  return scriptPromise;
}

interface Props {
  clientId: string;
  locale: string;
  onCredential: (credential: string) => void;
  onError: () => void;
}

export function GoogleSignInButton({ clientId, locale, onCredential, onError }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  // Keep the latest callbacks without re-initialising GIS on every render.
  const callbacks = useRef({ onCredential, onError });
  callbacks.current = { onCredential, onError };
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let cancelled = false;
    loadGsiScript()
      .then(() => {
        const gsi = window.google?.accounts.id;
        if (cancelled || !gsi || !containerRef.current) return;
        gsi.initialize({
          client_id: clientId,
          ux_mode: "popup",
          callback: (response) => {
            if (response.credential) callbacks.current.onCredential(response.credential);
            else callbacks.current.onError();
          },
        });
        gsi.renderButton(containerRef.current, {
          type: "standard",
          theme: "outline",
          size: "large",
          text: "continue_with",
          shape: "rectangular",
          width: 320,
          locale,
        });
        setReady(true);
      })
      .catch(() => {
        if (!cancelled) callbacks.current.onError();
      });
    return () => {
      cancelled = true;
    };
  }, [clientId, locale]);

  return (
    <div
      ref={containerRef}
      className="flex justify-center min-h-[44px]"
      aria-busy={!ready}
    />
  );
}
