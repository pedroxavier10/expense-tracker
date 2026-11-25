import { ImageResponse } from "next/og";

const BACKGROUND = "#1a1a1a"; // ink.DEFAULT
const FOREGROUND = "#faf8f4"; // paper.DEFAULT
const ACCENT = "#c2410c"; // accent.DEFAULT

/**
 * Renders the "Lx" brand mark as a PNG.
 *
 * Maskable icons are cropped by the OS to an arbitrary shape, so the artwork
 * must stay inside the central safe zone (~80%). Regular icons use a larger mark.
 */
export function renderPwaIcon(size: number, maskable: boolean): ImageResponse {
  const fontSize = Math.round(size * (maskable ? 0.4 : 0.52));
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: BACKGROUND,
          color: FOREGROUND,
          fontSize,
          fontWeight: 700,
          letterSpacing: "-0.04em",
        }}
      >
        <span>L</span>
        <span style={{ color: ACCENT }}>x</span>
      </div>
    ),
    { width: size, height: size },
  );
}
