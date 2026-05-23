import type { Config } from "tailwindcss";

/**
 * Design system:
 * - Editorial, calm, money-serious aesthetic
 * - Monochrome stone palette + a single accent (warm orange) for value emphasis
 * - Serif display for headings, neutral sans for body, monospace for amounts
 */
const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        display: ["var(--font-display)", "Georgia", "serif"],
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
      colors: {
        ink: {
          DEFAULT: "#1a1a1a",
          soft: "#2a2a2a",
          muted: "#6b6660",
        },
        paper: {
          DEFAULT: "#faf8f4",
          card: "#ffffff",
          line: "#e8e3dc",
        },
        accent: {
          DEFAULT: "#c2410c", // burnt orange
          soft: "#fed7aa",
        },
      },
      borderRadius: {
        sm: "2px",
        DEFAULT: "4px",
      },
      boxShadow: {
        card: "0 1px 0 rgba(0,0,0,0.04), 0 1px 3px rgba(0,0,0,0.04)",
      },
    },
  },
  plugins: [],
};

export default config;
