import { NavLink } from 'react-router-dom';
import { FileText, FolderKanban, LayoutDashboard, LogOut, Settings, Users, X } from 'lucide-react';
import { useAuth } from '../../hooks/useAuth';
import { useProjects } from '../../hooks/useProjects';
import { Avatar } from '../ui/Avatar';

const linkBase =
  'flex items-center gap-3 rounded-btn px-3 py-2 text-sm font-medium transition-colors duration-150';

function navClass({ isActive }: { isActive: boolean }) {
  return `${linkBase} ${
    isActive ? 'bg-white text-accent shadow-card' : 'text-ink-soft hover:bg-white/60 hover:text-ink'
  }`;
}

interface Props {
  onNavigate?: () => void;
  onClose?: () => void;
}

export function Sidebar({ onNavigate, onClose }: Props) {
  const { user, logout } = useAuth();
  const { projects } = useProjects();

  return (
    <div className="flex h-full w-60 flex-col border-r border-line bg-[rgba(255,245,238,0.85)] p-4 backdrop-blur-lg">
      <div className="mb-6 flex items-center justify-between px-2">
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent text-white">
            <FolderKanban size={18} strokeWidth={1.5} aria-hidden />
          </div>
          <span className="text-[15px] font-semibold leading-tight tracking-tight">
            Project Management
          </span>
        </div>
        {onClose && (
          <button type="button" onClick={onClose} aria-label="Закрити меню" className="p-1 md:hidden">
            <X size={18} strokeWidth={1.5} />
          </button>
        )}
      </div>

      <nav className="flex flex-col gap-1" aria-label="Основна навігація" onClick={onNavigate}>
        <NavLink to="/dashboard" className={navClass}>
          <LayoutDashboard size={18} strokeWidth={1.5} aria-hidden /> Дашборд
        </NavLink>
        <NavLink to="/projects" className={navClass}>
          <FolderKanban size={18} strokeWidth={1.5} aria-hidden />
          <span className="flex-1">Проєкти</span>
          <span className="rounded-full bg-black/5 px-2 text-xs text-ink-soft">{projects.length}</span>
        </NavLink>
        <NavLink to="/documents" className={navClass}>
          <FileText size={18} strokeWidth={1.5} aria-hidden /> Документи
        </NavLink>
        <NavLink to="/team" className={navClass}>
          <Users size={18} strokeWidth={1.5} aria-hidden /> Команда
        </NavLink>
      </nav>

      <div className="mt-auto flex flex-col gap-3">
        <div className="h-px bg-line" />
        <NavLink to="/settings" className={navClass} onClick={onNavigate}>
          <Settings size={18} strokeWidth={1.5} aria-hidden /> Налаштування
        </NavLink>
        {user && (
          <div className="flex items-center gap-3 rounded-btn px-2 py-1.5">
            <Avatar name={user.login} size={34} />
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium">{user.login}</p>
              <p className="text-xs text-ink-soft">Користувач</p>
            </div>
            <button
              type="button"
              onClick={logout}
              aria-label="Вийти"
              title="Вийти"
              className="rounded-btn p-1.5 text-ink-soft transition-colors hover:bg-black/5 hover:text-ink"
            >
              <LogOut size={18} strokeWidth={1.5} />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
