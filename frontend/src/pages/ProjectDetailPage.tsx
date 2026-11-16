import { useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import toast from 'react-hot-toast';
import { FileText, FolderX, Settings, Users } from 'lucide-react';
import { deleteProject, updateProject } from '../api/projects';
import { deleteDocument, downloadDocument, replaceDocument, uploadDocuments } from '../api/documents';
import { DocumentTable } from '../components/documents/DocumentTable';
import { UploadProgress } from '../components/documents/UploadProgress';
import { InviteForm } from '../components/projects/InviteForm';
import { ProjectForm } from '../components/projects/ProjectForm';
import { ShareForm } from '../components/projects/ShareForm';
import { Avatar } from '../components/ui/Avatar';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { ConfirmDialog } from '../components/ui/ConfirmDialog';
import { EmptyState } from '../components/ui/EmptyState';
import { FileDropZone } from '../components/ui/FileDropZone';
import { ProgressBar } from '../components/ui/ProgressBar';
import { useDocuments } from '../hooks/useDocuments';
import { useProjectRole, useProjects } from '../hooks/useProjects';
import type { Document } from '../types';
import { getErrorMessage } from '../utils/errors';
import { isAllowedFile } from '../utils/fileType';
import { formatBytes, MAX_FILE_BYTES, PROJECT_LIMIT_BYTES } from '../utils/formatBytes';
import { formatDate } from '../utils/formatDate';
import { getProjectStatus } from '../utils/projectStatus';

const TABS = [
  { id: 'documents', label: 'Документи', icon: FileText },
  { id: 'team', label: 'Команда', icon: Users },
  { id: 'settings', label: 'Налаштування', icon: Settings },
] as const;
type TabId = (typeof TABS)[number]['id'];

export default function ProjectDetailPage() {
  const projectId = Number(useParams().id);
  const { projects, loading } = useProjects();
  const [params, setParams] = useSearchParams();
  const tab: TabId = TABS.some((t) => t.id === params.get('tab')) ? (params.get('tab') as TabId) : 'documents';
  const project = projects.find((p) => p.id === projectId);

  if (!loading && !project) {
    return (
      <Card>
        <EmptyState
          icon={FolderX}
          title="Проєкт не знайдено"
          description="Його не існує, або у вас немає до нього доступу."
          action={<Link to="/projects"><Button variant="secondary">До списку проєктів</Button></Link>}
        />
      </Card>
    );
  }
  if (!project) return null;

  const status = getProjectStatus(project, project.documents.length);

  return (
    <div className="flex flex-col gap-6">
      <div className="pm-enter">
        <div className="flex flex-wrap items-center gap-3">
          <h2 className="text-2xl">{project.name}</h2>
          <Badge tone={status.tone}>{status.label}</Badge>
        </div>
        {project.description && <p className="mt-1 max-w-2xl text-sm text-ink-soft">{project.description}</p>}
        <div className="mt-4 max-w-sm">
          <div className="mb-1.5 flex justify-between text-xs text-ink-soft">
            <span>{formatBytes(project.total_size_bytes)}</span>
            <span>з {formatBytes(PROJECT_LIMIT_BYTES)}</span>
          </div>
          <ProgressBar value={(project.total_size_bytes / PROJECT_LIMIT_BYTES) * 100} tone="auto" label="Використано місця" />
        </div>
      </div>

      <div role="tablist" aria-label="Розділи проєкту" className="flex gap-1 border-b border-line">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            type="button"
            role="tab"
            id={`tab-${id}`}
            aria-selected={tab === id}
            aria-controls={`panel-${id}`}
            onClick={() => setParams(id === 'documents' ? {} : { tab: id }, { replace: true })}
            className={`-mb-px flex items-center gap-2 border-b-2 px-4 py-2.5 text-sm font-medium transition-colors ${
              tab === id ? 'border-accent text-accent' : 'border-transparent text-ink-soft hover:text-ink'
            }`}
          >
            <Icon size={16} strokeWidth={1.5} aria-hidden /> {label}
          </button>
        ))}
      </div>

      <div role="tabpanel" id={`panel-${tab}`} aria-labelledby={`tab-${tab}`}>
        {tab === 'documents' && <DocumentsTab projectId={projectId} />}
        {tab === 'team' && <TeamTab projectId={projectId} />}
        {tab === 'settings' && <SettingsTab projectId={projectId} />}
      </div>
    </div>
  );
}

function DocumentsTab({ projectId }: { projectId: number }) {
  const { documents, loading, reload } = useDocuments(projectId);
  const { reload: reloadProjects } = useProjects();
  const [progress, setProgress] = useState<{ percent: number; label: string } | null>(null);
  const [toDelete, setToDelete] = useState<Document | null>(null);

  const refresh = async () => {
    await Promise.all([reload(), reloadProjects()]);
  };

  const handleUpload = async (files: File[]) => {
    const valid = files.filter((f) => {
      if (!isAllowedFile(f)) {
        toast.error(`«${f.name}»: дозволені лише PDF, DOCX, PNG, JPG`);
        return false;
      }
      if (f.size > MAX_FILE_BYTES) {
        toast.error(`«${f.name}»: файл більший за 50 МБ`);
        return false;
      }
      return true;
    });
    if (!valid.length) return;
    setProgress({ percent: 0, label: valid.length > 1 ? `Завантаження ${valid.length} файлів…` : valid[0].name });
    try {
      await uploadDocuments(projectId, valid, (percent) => setProgress((p) => p && { ...p, percent }));
      toast.success(valid.length > 1 ? 'Файли завантажено' : 'Файл завантажено');
      await refresh();
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setProgress(null);
    }
  };

  const handleReplace = async (doc: Document, file: File) => {
    if (!isAllowedFile(file)) return void toast.error('Дозволені лише PDF, DOCX, PNG, JPG');
    if (file.size > MAX_FILE_BYTES) return void toast.error('Файл більший за 50 МБ');
    setProgress({ percent: 0, label: `Заміна «${doc.filename}»…` });
    try {
      await replaceDocument(doc.id, file, (percent) => setProgress((p) => p && { ...p, percent }));
      toast.success('Файл замінено');
      await refresh();
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setProgress(null);
    }
  };

  const handleDownload = async (doc: Document) => {
    try {
      await downloadDocument(doc.id, doc.filename);
    } catch (error) {
      toast.error(getErrorMessage(error));
    }
  };

  const handleDelete = async () => {
    if (!toDelete) return;
    try {
      await deleteDocument(toDelete.id);
      toast.success('Документ видалено');
      await refresh();
    } catch (error) {
      toast.error(getErrorMessage(error));
    }
  };

  return (
    <div className="flex flex-col gap-4">
      <FileDropZone onFiles={handleUpload} disabled={!!progress} />
      {progress && <UploadProgress {...progress} />}
      <Card className="overflow-hidden">
        {!loading && documents.length === 0 ? (
          <EmptyState icon={FileText} title="Документів ще немає" description="Завантажте перший файл, перетягнувши його у зону вище." />
        ) : (
          <DocumentTable
            documents={documents}
            onDownload={handleDownload}
            onReplace={handleReplace}
            onDelete={setToDelete}
          />
        )}
      </Card>
      <ConfirmDialog
        open={!!toDelete}
        title="Видалити документ?"
        message={`Файл «${toDelete?.filename ?? ''}» буде видалено без можливості відновлення.`}
        confirmLabel="Видалити"
        onConfirm={handleDelete}
        onClose={() => setToDelete(null)}
      />
    </div>
  );
}

function TeamTab({ projectId }: { projectId: number }) {
  const { membersByProject, reload } = useProjects();
  const isOwner = useProjectRole(projectId) === 'owner';
  const members = membersByProject[projectId] ?? [];

  return (
    <div className="flex flex-col gap-4">
      {isOwner && (
        <Card className="grid gap-6 p-5 md:grid-cols-2">
          <section aria-labelledby="invite-title">
            <h3 id="invite-title" className="text-sm">Запросити за логіном</h3>
            <p className="mb-3 mt-1 text-xs text-ink-soft">Користувач одразу стане учасником.</p>
            <InviteForm projectId={projectId} onDone={() => void reload()} />
          </section>
          <section aria-labelledby="share-title">
            <h3 id="share-title" className="text-sm">Запросити електронною поштою</h3>
            <p className="mb-3 mt-1 text-xs text-ink-soft">Надішлемо посилання, що діє обмежений час.</p>
            <ShareForm projectId={projectId} />
          </section>
        </Card>
      )}
      <Card className="overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr>
              <th scope="col" className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-ink-soft">Учасник</th>
              <th scope="col" className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-ink-soft">Роль</th>
              <th scope="col" className="hidden px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-ink-soft sm:table-cell">Додано</th>
            </tr>
          </thead>
          <tbody>
            {members.map((m) => (
              <tr key={m.id} className="border-t border-line">
                <td className="px-4 py-3">
                  <div className="flex items-center gap-3">
                    <Avatar name={m.login} size={32} />
                    <span className="font-medium">{m.login}</span>
                  </div>
                </td>
                <td className="px-4 py-3">
                  <Badge tone={m.role === 'owner' ? 'accent' : 'neutral'}>
                    {m.role === 'owner' ? 'Власник' : 'Учасник'}
                  </Badge>
                </td>
                <td className="hidden px-4 py-3 text-ink-soft sm:table-cell">{formatDate(m.created_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}

function SettingsTab({ projectId }: { projectId: number }) {
  const { projects, reload } = useProjects();
  const navigate = useNavigate();
  const isOwner = useProjectRole(projectId) === 'owner';
  const [confirming, setConfirming] = useState(false);
  const project = projects.find((p) => p.id === projectId);
  if (!project) return null;

  if (!isOwner) {
    return (
      <Card>
        <EmptyState icon={Settings} title="Лише для власника" description="Редагувати та видаляти проєкт може тільки його власник." />
      </Card>
    );
  }

  return (
    <div className="flex max-w-2xl flex-col gap-6">
      <Card className="p-5">
        <h3 className="mb-4 text-base">Загальні</h3>
        <ProjectForm
          key={project.updated_at}
          initial={project}
          submitLabel="Зберегти зміни"
          onSubmit={async (values) => {
            try {
              await updateProject(projectId, {
                name: values.name.trim(),
                description: values.description?.trim() || null,
              });
              toast.success('Зміни збережено');
              await reload();
            } catch (error) {
              toast.error(getErrorMessage(error));
            }
          }}
        />
      </Card>

      <Card className="border-danger/30 p-5">
        <h3 className="text-base text-danger">Небезпечна зона</h3>
        <p className="mb-4 mt-1 text-sm text-ink-soft">
          Видалення проєкту прибере всі його документи та учасників. Цю дію не можна скасувати.
        </p>
        <Button variant="danger" onClick={() => setConfirming(true)}>Видалити проєкт</Button>
      </Card>

      <ConfirmDialog
        open={confirming}
        title="Видалити проєкт?"
        message={`Проєкт «${project.name}» разом з усіма документами буде видалено назавжди.`}
        confirmLabel="Видалити"
        onConfirm={async () => {
          try {
            await deleteProject(projectId);
            toast.success('Проєкт видалено');
            await reload();
            navigate('/projects', { replace: true });
          } catch (error) {
            toast.error(getErrorMessage(error));
          }
        }}
        onClose={() => setConfirming(false)}
      />
    </div>
  );
}
