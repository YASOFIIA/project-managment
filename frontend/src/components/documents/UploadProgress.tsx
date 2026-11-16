import { Loader2 } from 'lucide-react';
import { ProgressBar } from '../ui/ProgressBar';

export function UploadProgress({ percent, label }: { percent: number; label: string }) {
  return (
    <div className="rounded-input border border-line bg-white/70 p-3" aria-live="polite">
      <div className="mb-2 flex items-center justify-between text-sm">
        <span className="flex items-center gap-2">
          <Loader2 size={16} className="animate-spin text-accent" aria-hidden /> {label}
        </span>
        <span className="tabular-nums text-ink-soft">{percent}%</span>
      </div>
      <ProgressBar value={percent} label="Прогрес завантаження" />
    </div>
  );
}
