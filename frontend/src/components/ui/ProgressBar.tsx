interface Props {
  value: number; // 0..100
  tone?: 'accent' | 'auto';
  label?: string;
}

export function ProgressBar({ value, tone = 'accent', label }: Props) {
  const pct = Math.max(0, Math.min(100, value));
  const color =
    tone === 'auto' && pct >= 90 ? 'bg-danger' : tone === 'auto' && pct >= 70 ? 'bg-warning' : 'bg-accent';
  return (
    <div
      role="progressbar"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={Math.round(pct)}
      aria-label={label}
      className="h-1.5 w-full overflow-hidden rounded-full bg-black/5"
    >
      <div
        className={`h-full rounded-full transition-[width] duration-300 ${color}`}
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}
