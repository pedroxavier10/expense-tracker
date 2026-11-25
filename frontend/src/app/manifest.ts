import type { MetadataRoute } from "next";

// Values mirror the design tokens in tailwind.config.ts (paper.DEFAULT / ink.DEFAULT).
const BACKGROUND_COLOR = "#faf8f4";
const THEME_COLOR = "#1a1a1a";

export default function manifest(): MetadataRoute.Manifest {
  return {
    id: "/",
    name: "Ledger-x",
    short_name: "Ledger-x",
    description: "A quiet place to record what you spend.",
    start_url: "/dashboard",
    scope: "/",
    display: "standalone",
    orientation: "portrait",
    background_color: BACKGROUND_COLOR,
    theme_color: THEME_COLOR,
    icons: [
      { src: "/icons/icon-192.png", sizes: "192x192", type: "image/png", purpose: "any" },
      { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png", purpose: "any" },
      {
        src: "/icons/icon-512-maskable.png",
        sizes: "512x512",
        type: "image/png",
        purpose: "maskable",
      },
    ],
  };
}
