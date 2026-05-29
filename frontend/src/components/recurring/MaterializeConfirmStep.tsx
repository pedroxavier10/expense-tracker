"use client";

import { useTranslations } from "next-intl";

interface Props {
  currentMonthLabel: string;
  busy: boolean;
  onConfirm: () => void;
  onSkip: () => void;
}

export function MaterializeConfirmStep({ currentMonthLabel, busy, onConfirm, onSkip }: Props) {
  const t = useTranslations("recurring");
  const tCommon = useTranslations("common");

  return (
    <div className="space-y-5">
      <h2 id="recurring-modal-title" className="font-display text-2xl text-ink">
        {t("confirmMaterializeTitle")}
      </h2>
      <p className="text-ink-muted">
        {t("confirmMaterializeBody", { month: currentMonthLabel })}
      </p>
      <div className="flex items-center gap-3 pt-2">
        <button
          className="btn-primary"
          onClick={onConfirm}
          disabled={busy}
        >
          {busy ? tCommon("saving") : t("confirmYes")}
        </button>
        <button className="btn-ghost" onClick={onSkip}>
          {t("confirmNo")}
        </button>
      </div>
    </div>
  );
}
