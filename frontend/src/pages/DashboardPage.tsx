import { useState } from 'react';
import { Link } from 'react-router-dom';
import { FileText, FolderKanban, HardDrive, Plus, Users } from 'lucide-react';
import { FileTypeIcon } from '../components/documents/DocumentRow';
import { ProjectCard } from '../components/projects/ProjectCard';
import { ProjectFormModal } from '../components/projects/ProjectFormModal';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { EmptyState } from '../components/ui/EmptyState';
import { useAuth } from '../hooks/useAuth';
import { useIsOwnerOf, useProjects } from '../hooks/useProjects';
import { formatBytes } from '../utils/formatBytes';
import { formatDate } from '../utils/formatDate';

export default function DashboardPage() {
  const { user } = useAuth();
  const { projects, membersByProject, loading } = useProjects();
  const isOwnerOf = useIsOwnerOf();
  const [creating, setCreating] = useState(false);

  const documents = projects.flatMap((p) => p.documents.map((d) => ({ ...d, projectName: p.name })));
  const totalBytes = projects.reduce((sum, p) => sum + p.total_size_bytes, 0);
  const people = new Set(Object.values(membersByProject).flatMap((ms) => ms.map((m) => m.user_id)));
  const recent = [...documents]
    .sort((a, b) => b.created_at.localeCompare(a.created_at))
    .slice(0, 5);

  const stats = [
    { icon: FolderKanban, label: 'Проєкти', value: projects.length },
    { icon: FileText, label: 'Документи', value: documents.length },
    { icon: HardDrive, label: 'Використано', value: formatBytes(totalBytes) },
    { icon: Users, label: 'Колеги', value: Math.max(people.size - 1, 0) },
  ];

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h2 className="text-2xl">Привіт, {user?.login} 👋</h2>
        <p className="mt-1 text-sm text-ink-soft">Ось що відбувається у ваших проєктах.</p>
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {stats.map(({ icon: Icon, label, value }) => (
          <Card key={label} className="pm-enter flex items-center gap-3 p-4">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-accent-soft text-accent">
              <Icon size={20} strokeWidth={1.5} aria-hidden />
            </div>
            <div>
              <p className="text-xl font-semibold leading-none tracking-tight">{loading ? '–' : value}</p>
              <p className="mt-1 text-xs text-ink-soft">{label}</p>
            </div>
          </Card>
        ))}
      </div>

      <section aria-labelledby="dash-projects">
        <div className="mb-4 flex items-center justify-between">
          <h2 id="dash-projects" className="text-lg">Проєкти</h2>
          <div className="flex items-center gap-2">
            {projects.length > 6 && (
              <Link to="/projects" className="text-sm text-accent hover:text-accent-hover">
                Усі проєкти
              </Link>
            )}
            <Button size="sm" onClick={() => setCreating(true)} aria-label="Створити проєкт">
              <Plus size={16} strokeWidth={1.5} aria-hidden /> Створити
            </Button>
          </div>
        </div>
        {!loading && projects.length === 0 ? (
          <Card>
            <EmptyState
              icon={FolderKanban}
              title="Створіть перший проєкт"
              description="Проєкт обʼєднує документи та команду в одному місці."
              action={<Button onClick={() => setCreating(true)}>Новий проєкт</Button>}
            />
          </Card>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {projects.slice(0, 6).map((p) => (
              <ProjectCard
                key={p.id}
                project={p}
                members={membersByProject[p.id] ?? []}
                isOwner={isOwnerOf(p.id)}
              />
            ))}
          </div>
        )}
      </section>

      <section aria-labelledby="dash-recent">
        <h2 id="dash-recent" className="mb-4 text-lg">Нещодавні документи</h2>
        <Card className="overflow-hidden">
          {recent.length === 0 ? (
            <EmptyState icon={FileText} title="Документів поки немає" description="Завантажені файли зʼявляться тут." />
          ) : (
            <ul>
              {recent.map((d, i) => (
                <li key={d.id} className={i > 0 ? 'border-t border-line' : ''}>
                  <Link
                    to={`/project/${d.project_id}`}
                    className="flex items-center gap-3 px-4 py-3 transition-colors hover:bg-white/60"
                  >
                    <FileTypeIcon filename={d.filename} size={20} />
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium">{d.filename}</p>
                      <p className="truncate text-xs text-ink-soft">{d.projectName}</p>
                    </div>
                    <span className="hidden text-xs text-ink-soft sm:block">{formatBytes(d.file_size_bytes)}</span>
                    <span className="text-xs text-ink-soft">{formatDate(d.created_at)}</span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </section>

      <ProjectFormModal open={creating} onClose={() => setCreating(false)} />
    </div>
  );
}
