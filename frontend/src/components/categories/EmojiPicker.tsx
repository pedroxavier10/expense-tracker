"use client";

/**
 * Curated emoji picker — a small grid of expense-relevant emojis. No external
 * dependency: the category `icon` column just stores the chosen emoji string.
 */

const EMOJIS = [
  "🍔", "🍕", "🍎", "☕", "🍷", "🛒", "🛍️",
  "🚗", "⛽", "🚌", "✈️", "🚆", "🅿️", "🚲",
  "🏠", "💡", "🔌", "💧", "🧾", "📱", "💻",
  "🩺", "💊", "🏥", "🦷", "🧘", "🏋️", "🏃",
  "🎮", "🎬", "🎵", "📚", "🎁", "🐶", "🌱",
  "💼", "🏦", "💳", "📈", "🎓", "✂️", "📦",
];

interface Props {
  value: string | null;
  onChange: (icon: string | null) => void;
}

export function EmojiPicker({ value, onChange }: Props) {
  return (
    <div className="grid grid-cols-7 gap-1.5">
      {EMOJIS.map((emoji) => {
        const selected = value === emoji;
        return (
          <button
            key={emoji}
            type="button"
            onClick={() => onChange(selected ? null : emoji)}
            aria-pressed={selected}
            className={`text-xl leading-none aspect-square rounded border flex items-center justify-center transition-colors ${
              selected
                ? "border-accent bg-accent/10"
                : "border-paper-line hover:bg-paper-line/40"
            }`}
          >
            {emoji}
          </button>
        );
      })}
    </div>
  );
}
