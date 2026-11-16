import { useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import toast from 'react-hot-toast';
import { FolderKanban, Plus, SearchX } from 'lucide-react';
import { deleteProject } from '../api/projects';
import { InviteForm } from '../components/projects/InviteForm';
import { ProjectCard, type ProjectAction } from '../components/projects/ProjectCard';
import { ProjectFormModal } from '../components/projects/ProjectFormModal';
import { ShareForm } from '../components/projects/ShareForm';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { ConfirmDialog } from '../components/ui/ConfirmDialog';
import { EmptyState } from '../components/ui/EmptyState';
import { Modal } from '../components/ui/Modal';
import { useIsOwnerOf, useProjects } from '../hooks/useProjects';
import type { ProjectDetail } from '../types';
import { getErrorMessage } from '../utils/errors';

type Sort = 'updated' | 'name' | 'size';
type ModalState = { action: ProjectAction | 'create'; project?: ProjectDetail } | null;

export default function ProjectsPage() {
  const { projects, membersByProject, loading, reload } = useProjects();
  const isOwnerOf = useIsOwnerOf();
  const [params, setParams] = useSearchParams();
  const [sort, setSort] = useState<Sort>('updated');
  const [modal, setModal] = useState<ModalState>(null);
  const query = params.get('q')?.trim().toLowerCase() ?? '';

  const visible = useMemo(() => {
    const filtered = projects.filter(
      (p) => !query || p.name.toLowerCase().includes(query) || (p.description ?? '').toLowerCase().includes(query),
    );
    return [...filtered].sort((a, b) => {
      if (sort === 'name') return a.name.localeCompare(b.name, 'uk');
      if (sort === 'size') return b.total_size_bytes - a.total_size_bytes;
      return b.updated_at.localeCompare(a.updated_at);
    });
  }, [projects, query, sort]);

  const close = () => setModal(null);
  const project = modal?.project;

  const handleDelete = async () => {
    if (!project) return;
    try {
      await deleteProject(project.id);
      toast.success('Проєкт видалено');
      await reload();
    } catch (error) {
      toast.error(getErrorMessage(error));
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-2xl">Проєкти</h2>
          <p className="mt-1 text-sm text-ink-soft">
            {query ? `Результати за запитом «${params.get('q')}»` : 'Усі проєкти, до яких у вас є доступ'}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <label className="sr-only" htmlFor="sort">Сортування</label>
          <select
            id="sort"
            value={sort}
            onChange={(e) => setSort(e.target.value as Sort)}
            className="h-10 rounded-input border border-black/10 bg-white/80 px-3 text-sm focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/20"
          >
            <option value="updated">Нещодавно оновлені</option>
            <option value="name">За назвою</option>
            <option value="size">За розміром</option>
          </select>
          <Button onClick={() => setModal({ action: 'create' })}>
            <Plus size={16} strokeWidth={1.5} aria-hidden /> Створити проєкт
          </Button>
        </div>
      </div>

      {!loading && visible.length === 0 ? (
        <Card>
          {query ? (
            <EmptyState
              icon={SearchX}
              title="Нічого не знайдено"
              description="Спробуйте змінити пошуковий запит."
              action={<Button variant="secondary" onClick={() => setParams({})}>Скинути пошук</Button>}
            />
          ) : (
            <EmptyState
              icon={FolderKanban}
              title="Створіть перший проєкт"
              description="Проєкт обʼєднує документи та команду в одному місці."
              action={<Button onClick={() => setModal({ action: 'create' })}>Новий проєкт</Button>}
            />
          )}
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {visible.map((p) => (
            <ProjectCard
              key={p.id}
              project={p}
              members={membersByProject[p.id] ?? []}
              isOwner={isOwnerOf(p.id)}
              onAction={(action) => setModal({ action, project: p })}
            />
          ))}
        </div>
      )}

      <ProjectFormModal
        open={modal?.action === 'create' || modal?.action === 'edit'}
        project={modal?.action === 'edit' ? project : null}
        onClose={close}
      />
      <Modal open={modal?.action === 'invite'} onClose={close} title={`Запросити в «${project?.name ?? ''}»`}>
        {project && (
          <>
            <p className="mb-3 text-sm text-ink-soft">Додайте користувача за його логіном — він одразу стане учасником.</p>
            <InviteForm projectId={project.id} onDone={() => { void reload(); close(); }} />
          </>
        )}
      </Modal>
      <Modal open={modal?.action === 'share'} onClose={close} title={`Email-запрошення в «${project?.name ?? ''}»`}>
        {project && (
          <>
            <p className="mb-3 text-sm text-ink-soft">Ми надішлемо лист із посиланням, яке діє обмежений час.</p>
            <ShareForm projectId={project.id} onDone={close} />
          </>
        )}
      </Modal>
      <ConfirmDialog
        open={modal?.action === 'delete'}
        title="Видалити проєкт?"
        message={`Проєкт «${project?.name ?? ''}» разом з усіма документами буде видалено назавжди.`}
        confirmLabel="Видалити"
        onConfirm={handleDelete}
        onClose={close}
      />
    </div>
  );
}
