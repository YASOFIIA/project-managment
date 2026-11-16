import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react';
import { Link, useLocation, useMatch, useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { Bell, ChevronRight, FolderKanban, Menu, Search } from 'lucide-react';
import {
  acceptInvitation,
  declineInvitation,
  getPendingInvitations,
  type PendingInvitation,
} from '../../api/invitations';
import { useAuth } from '../../hooks/useAuth';
import { useProjects } from '../../hooks/useProjects';
import { getErrorMessage } from '../../utils/errors';
import { formatExpiresIn } from '../../utils/formatDate';
import { Avatar } from '../ui/Avatar';
import { Button } from '../ui/Button';

const TITLES: Record<string, string> = {
  '/dashboard': 'Dashboard',
  '/projects': 'Projects',
  '/documents': 'Documents',
  '/team': 'Team',
  '/settings': 'Settings',
};

export function TopBar({ onMenu }: { onMenu: () => void }) {
  const { user } = useAuth();
  const { projects, reload: reloadProjects } = useProjects();
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [invitations, setInvitations] = useState<PendingInvitation[]>([]);
  const [openInv, setOpenInv] = useState(false);
  const [busyId, setBusyId] = useState<number | null>(null);
  const bellRef = useRef<HTMLDivElement>(null);
  const projectMatch = useMatch('/project/:id');

  const projectName = projectMatch
    ? projects.find((p) => p.id === Number(projectMatch.params.id))?.name
    : undefined;

  const fetchInvitations = useCallback(async () => {
    try {
      const data = await getPendingInvitations();
      setInvitations(data);
    } catch {
      // Ignore background poll failures silently
    }
  }, []);

  useEffect(() => {
    void fetchInvitations();
    const interval = setInterval(() => void fetchInvitations(), 30_000);
    return () => clearInterval(interval);
  }, [fetchInvitations, pathname]);

  useEffect(() => {
    if (!openInv) return;
    const close = (e: Event) => {
      if (
        e instanceof KeyboardEvent
          ? e.key === 'Escape'
          : !bellRef.current?.contains(e.target as Node)
      ) {
        setOpenInv(false);
      }
    };
    document.addEventListener('pointerdown', close);
    document.addEventListener('keydown', close);
    return () => {
      document.removeEventListener('pointerdown', close);
      document.removeEventListener('keydown', close);
    };
  }, [openInv]);

  const handleAccept = async (inv: PendingInvitation) => {
    setBusyId(inv.id);
    try {
      await acceptInvitation(inv.id);
      toast.success(`You joined ${inv.project_name}!`);
      setInvitations((prev) => prev.filter((item) => item.id !== inv.id));
      await reloadProjects();
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setBusyId(null);
    }
  };

  const handleDecline = async (inv: PendingInvitation) => {
    setBusyId(inv.id);
    try {
      await declineInvitation(inv.id);
      toast('Invitation declined');
      setInvitations((prev) => prev.filter((item) => item.id !== inv.id));
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setBusyId(null);
    }
  };

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
        aria-label="Open menu"
        className="rounded-btn p-2 text-ink-soft hover:bg-black/5 md:hidden"
      >
        <Menu size={20} strokeWidth={1.5} />
      </button>

      <nav aria-label="Breadcrumbs" className="flex min-w-0 items-center gap-1.5 text-sm">
        {projectMatch ? (
          <>
            <Link to="/projects" className="text-ink-soft hover:text-ink">
              Projects
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
            placeholder="Search projects..."
            aria-label="Search projects"
            className="h-9 w-full rounded-input border border-black/10 bg-white/70 pl-9 pr-3 text-sm focus:border-accent focus:bg-white focus:outline-none focus:ring-2 focus:ring-accent/20"
          />
        </div>
      </form>

      <div ref={bellRef} className="relative ml-auto sm:ml-0">
        <button
          type="button"
          onClick={() => {
            setOpenInv((v) => !v);
            void fetchInvitations();
          }}
          aria-label="Notifications"
          aria-expanded={openInv}
          title="Invitations"
          className="relative rounded-btn p-2 text-ink-soft transition-colors hover:bg-black/5 hover:text-ink"
        >
          <Bell size={20} strokeWidth={1.5} />
          {invitations.length > 0 && (
            <span className="absolute right-1 top-1 flex h-4 min-w-[16px] items-center justify-center rounded-full bg-danger px-1 text-[10px] font-bold leading-none text-white">
              {invitations.length}
            </span>
          )}
        </button>

        {openInv && (
          <div className="glass absolute right-0 top-11 z-30 w-80 rounded-2xl border border-line bg-white/95 p-3 shadow-pop">
            <div className="mb-2 flex items-center justify-between border-b border-line pb-2">
              <span className="text-sm font-semibold">
                Invitations ({invitations.length})
              </span>
            </div>
            {invitations.length === 0 ? (
              <p className="py-6 text-center text-sm text-ink-soft">No pending invitations</p>
            ) : (
              <ul className="flex max-h-80 flex-col divide-y divide-line overflow-y-auto">
                {invitations.map((inv) => (
                  <li key={inv.id} className="py-3 first:pt-1 last:pb-1">
                    <div className="flex items-start gap-2.5">
                      <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-accent-soft text-accent">
                        <FolderKanban size={16} strokeWidth={1.5} aria-hidden />
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-semibold">{inv.project_name}</p>
                        <p className="truncate text-xs text-ink-soft">for {inv.email}</p>
                        <p className="mt-0.5 text-xs text-ink-soft">
                          {formatExpiresIn(inv.expires_at)}
                        </p>
                        <div className="mt-2.5 flex gap-2">
                          <Button
                            size="sm"
                            loading={busyId === inv.id}
                            onClick={() => void handleAccept(inv)}
                          >
                            Accept
                          </Button>
                          <Button
                            size="sm"
                            variant="secondary"
                            disabled={busyId === inv.id}
                            onClick={() => void handleDecline(inv)}
                          >
                            Decline
                          </Button>
                        </div>
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>

      {user && <Avatar name={user.login} size={32} />}
    </header>
  );
}
