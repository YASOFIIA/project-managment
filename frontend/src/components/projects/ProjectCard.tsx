import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { FileText, Mail, MoreHorizontal, Pencil, Trash2, UserPlus } from 'lucide-react';
import type { ProjectDetail, ProjectMember } from '../../types';
import { formatBytes, PROJECT_LIMIT_BYTES } from '../../utils/formatBytes';
import { formatDate } from '../../utils/formatDate';
import { getProjectStatus } from '../../utils/projectStatus';
import { AvatarStack } from '../ui/Avatar';
import { Badge } from '../ui/Badge';
import { Card } from '../ui/Card';
import { ProgressBar } from '../ui/ProgressBar';

export type ProjectAction = 'edit' | 'invite' | 'share' | 'delete';

interface Props {
  project: ProjectDetail;
  members: ProjectMember[];
  isOwner: boolean;
  onAction?: (action: ProjectAction) => void;
}

export function ProjectCard({ project, members, isOwner, onAction }: Props) {
  const status = getProjectStatus(project, project.documents.length);
  const pct = (project.total_size_bytes / PROJECT_LIMIT_BYTES) * 100;

  return (
    <Card className="pm-enter relative flex flex-col p-5 transition-shadow duration-150 hover:shadow-pop">
      <div className="flex items-start justify-between gap-2">
        <Badge tone={status.tone}>{status.label}</Badge>
        {onAction && isOwner && <CardMenu onAction={onAction} />}
      </div>

      <h3 className="mt-3 text-base">
        <Link
          to={`/project/${project.id}`}
          className="after:absolute after:inset-0 after:rounded-card hover:text-accent"
        >
          {project.name}
        </Link>
      </h3>
      <p className="mt-1 line-clamp-2 min-h-[2.75rem] text-sm text-ink-soft">
        {project.description || 'Без опису'}
      </p>

      <div className="mt-4">
        <div className="mb-1.5 flex justify-between text-xs text-ink-soft">
          <span>{formatBytes(project.total_size_bytes)}</span>
          <span>з {formatBytes(PROJECT_LIMIT_BYTES)}</span>
        </div>
        <ProgressBar value={pct} tone="auto" label="Використано місця" />
      </div>

      <div className="mt-4 flex items-center justify-between text-xs text-ink-soft">
        <AvatarStack names={members.map((m) => m.login)} />
        <div className="flex items-center gap-3">
          <span className="inline-flex items-center gap-1">
            <FileText size={14} strokeWidth={1.5} aria-hidden /> {project.documents.length}
          </span>
          <span>{formatDate(project.updated_at)}</span>
        </div>
      </div>
    </Card>
  );
}

function CardMenu({ onAction }: { onAction: (a: ProjectAction) => void }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const close = (e: Event) => {
      if (e instanceof KeyboardEvent ? e.key === 'Escape' : !ref.current?.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('pointerdown', close);
    document.addEventListener('keydown', close);
    return () => {
      document.removeEventListener('pointerdown', close);
      document.removeEventListener('keydown', close);
    };
  }, [open]);

  const item = (action: ProjectAction, label: string, icon: React.ReactNode, danger = false) => (
    <button
      type="button"
      role="menuitem"
      onClick={() => {
        setOpen(false);
        onAction(action);
      }}
      className={`flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm transition-colors hover:bg-black/5 ${
        danger ? 'text-danger' : ''
      }`}
    >
      {icon} {label}
    </button>
  );

  return (
    <div ref={ref} className="relative z-10">
      <button
        type="button"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label="Дії з проєктом"
        onClick={() => setOpen((v) => !v)}
        className="rounded-btn p-1 text-ink-soft transition-colors hover:bg-black/5 hover:text-ink"
      >
        <MoreHorizontal size={18} strokeWidth={1.5} />
      </button>
      {open && (
        <div
          role="menu"
          className="glass absolute right-0 top-8 z-20 w-56 rounded-xl border border-line bg-white p-1 shadow-pop"
        >
          {item('edit', 'Редагувати', <Pencil size={16} strokeWidth={1.5} />)}
          {item('invite', 'Запросити учасника', <UserPlus size={16} strokeWidth={1.5} />)}
          {item('share', 'Email-запрошення', <Mail size={16} strokeWidth={1.5} />)}
          <div className="my-1 h-px bg-line" />
          {item('delete', 'Видалити', <Trash2 size={16} strokeWidth={1.5} />, true)}
        </div>
      )}
    </div>
  );
}
