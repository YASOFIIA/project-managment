import type { ReactNode } from 'react';

export type Tone = 'info' | 'warning' | 'success' | 'neutral' | 'accent';

const tones: Record<Tone, string> = {
  info: 'bg-blue-50 text-blue-700',
  warning: 'bg-amber-50 text-amber-700',
  success: 'bg-green-50 text-green-700',
  neutral: 'bg-black/5 text-ink-soft',
  accent: 'bg-accent-soft text-accent-hover',
};

export function Badge({ tone = 'neutral', children }: { tone?: Tone; children: ReactNode }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${tones[tone]}`}
    >
      {children}
    </span>
  );
}
