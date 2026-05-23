interface SummaryCardProps {
  title: string;
  value: string;
  subtext?: string;
}

export function SummaryCard({ title, value, subtext }: SummaryCardProps) {
  return (
    <div className="bg-paper-card border border-paper-line rounded p-5 shadow-card">
      <p className="label">{title}</p>
      <p className="font-display text-3xl text-ink mt-1 leading-none">{value}</p>
      {subtext && <p className="text-xs text-ink-muted mt-2">{subtext}</p>}
    </div>
  );
}
