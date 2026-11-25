import { renderPwaIcon } from "@/lib/pwaIcon";

export const size = { width: 180, height: 180 };
export const contentType = "image/png";

// iOS applies its own rounded mask, so the full-bleed variant is used.
export default function AppleIcon() {
  return renderPwaIcon(size.width, true);
}
