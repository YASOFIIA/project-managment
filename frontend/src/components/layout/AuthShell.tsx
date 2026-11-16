import type { ReactNode } from 'react';
import { FolderKanban } from 'lucide-react';

export function AuthShell({ title, subtitle, children }: { title: string; subtitle: string; children: ReactNode }) {
  return (
    <main className="flex min-h-screen items-center justify-center px-4 py-10">
      <div className="pm-enter glass w-full max-w-sm rounded-card border border-line p-8 shadow-pop">
        <div className="mb-6 flex flex-col items-center text-center">
          <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-2xl bg-accent text-white shadow-card">
            <FolderKanban size={24} strokeWidth={1.5} aria-hidden />
          </div>
          <p className="text-sm font-semibold tracking-tight text-ink-soft">Project Management</p>
          <h1 className="mt-4 text-2xl">{title}</h1>
          <p className="mt-1 text-sm text-ink-soft">{subtitle}</p>
        </div>
        {children}
      </div>
    </main>
  );
}
