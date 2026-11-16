import { useState, type FormEvent } from 'react';
import { Link, useLocation, useMatch, useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { Bell, ChevronRight, Menu, Search } from 'lucide-react';
import { useAuth } from '../../hooks/useAuth';
import { useProjects } from '../../hooks/useProjects';
import { Avatar } from '../ui/Avatar';

const TITLES: Record<string, string> = {
  '/dashboard': 'Дашборд',
  '/projects': 'Проєкти',
  '/documents': 'Документи',
  '/team': 'Команда',
  '/settings': 'Налаштування',
};

export function TopBar({ onMenu }: { onMenu: () => void }) {
  const { user } = useAuth();
  const { projects } = useProjects();
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const projectMatch = useMatch('/project/:id');

  const projectName = projectMatch
    ? projects.find((p) => p.id === Number(projectMatch.params.id))?.name
    : undefined;

  const submit = (e: FormEvent) => {
    e.preventDefault();
    const q = query.trim();
    navigate(q ? `/projects?q=${encodeURIComponent(q)}` : '/projects');
  };

  return (
    <header className="sticky top-0 z-20 flex h-16 items-center gap-3 border-b border-line bg-[rgba(253,246,240,0.8)] px-4 backdrop-blur-lg md:px-8">
      <button
        type="button"
        onClick={onMenu}
        aria-label="Відкрити меню"
        className="rounded-btn p-2 text-ink-soft hover:bg-black/5 md:hidden"
      >
        <Menu size={20} strokeWidth={1.5} />
      </button>

      <nav aria-label="Breadcrumbs" className="flex min-w-0 items-center gap-1.5 text-sm">
        {projectMatch ? (
          <>
            <Link to="/projects" className="text-ink-soft hover:text-ink">
              Проєкти
            </Link>
            <ChevronRight size={14} className="shrink-0 text-ink-soft" aria-hidden />
            <span className="truncate font-semibold">{projectName ?? '…'}</span>
          </>
        ) : (
          <h1 className="truncate text-base">{TITLES[pathname] ?? 'Project Management'}</h1>
        )}
      </nav>

      <form onSubmit={submit} role="search" className="ml-auto hidden w-64 sm:block">
        <div className="relative">
          <Search
            size={16}
            strokeWidth={1.5}
            className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-soft"
            aria-hidden
          />
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Пошук проєктів…"
            aria-label="Пошук проєктів"
            className="h-9 w-full rounded-input border border-black/10 bg-white/70 pl-9 pr-3 text-sm focus:border-accent focus:bg-white focus:outline-none focus:ring-2 focus:ring-accent/20"
          />
        </div>
      </form>

      <button
        type="button"
        onClick={() => toast('Нових сповіщень немає')}
        aria-label="Сповіщення"
        className="ml-auto rounded-btn p-2 text-ink-soft transition-colors hover:bg-black/5 hover:text-ink sm:ml-0"
      >
        <Bell size={20} strokeWidth={1.5} />
      </button>
      {user && <Avatar name={user.login} size={32} />}
    </header>
  );
}
