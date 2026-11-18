import { useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import toast from 'react-hot-toast';
import { FileText, FolderX, Settings, Trash2, Users } from 'lucide-react';
import { deleteProject, removeMember, updateProject } from '../api/projects';
import { deleteDocument, downloadDocument, replaceDocument, uploadDocuments } from '../api/documents';
import { DocumentTable } from '../components/documents/DocumentTable';
import { UploadProgress } from '../components/documents/UploadProgress';
import { ProjectForm } from '../components/projects/ProjectForm';
import { InviteForm } from '../components/projects/InviteForm';
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
import type { Document, ProjectMember } from '../types';
import { getErrorMessage } from '../utils/errors';
import { isAllowedFile } from '../utils/fileType';
import { formatBytes, MAX_FILE_BYTES, PROJECT_LIMIT_BYTES } from '../utils/formatBytes';
import { formatDate } from '../utils/formatDate';
import { getProjectStatus } from '../utils/projectStatus';

const TABS = [
  { id: 'documents', label: 'Documents', icon: FileText },
  { id: 'team', label: 'Team', icon: Users },
  { id: 'settings', label: 'Settings', icon: Settings },
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
          title="Project not found"
          description="It does not exist, or you do not have access to it."
          action={<Link to="/projects"><Button variant="secondary">Back to Projects</Button></Link>}
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
            <span>of {formatBytes(PROJECT_LIMIT_BYTES)}</span>
          </div>
          <ProgressBar value={(project.total_size_bytes / PROJECT_LIMIT_BYTES) * 100} tone="auto" label="Storage used" />
        </div>
      </div>

      <div role="tablist" aria-label="Project sections" className="flex gap-1 border-b border-line">
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
        toast.error(`"${f.name}": only PDF, DOCX, PNG, JPG are allowed`);
        return false;
      }
      if (f.size > MAX_FILE_BYTES) {
        toast.error(`"${f.name}": file exceeds 50 MB`);
        return false;
      }
      return true;
    });
    if (!valid.length) return;
    setProgress({ percent: 0, label: valid.length > 1 ? `Uploading ${valid.length} files…` : valid[0].name });
    try {
      await uploadDocuments(projectId, valid, (percent) => setProgress((p) => p && { ...p, percent }));
      toast.success(valid.length > 1 ? 'Files uploaded' : 'File uploaded');
      await refresh();
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setProgress(null);
    }
  };

  const handleReplace = async (doc: Document, file: File) => {
    if (!isAllowedFile(file)) return void toast.error('Only PDF, DOCX, PNG, JPG are allowed');
    if (file.size > MAX_FILE_BYTES) return void toast.error('File exceeds 50 MB');
    setProgress({ percent: 0, label: `Replacing "${doc.filename}"…` });
    try {
      await replaceDocument(doc.id, file, (percent) => setProgress((p) => p && { ...p, percent }));
      toast.success('File replaced');
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
      toast.success('Document deleted');
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
          <EmptyState icon={FileText} title="No documents yet" description="Upload your first file by dropping it into the area above." />
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
        title="Delete document?"
        message={`File "${toDelete?.filename ?? ''}" will be permanently deleted.`}
        confirmLabel="Delete"
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
  const [toRemove, setToRemove] = useState<ProjectMember | null>(null);

  const handleRemoveMember = async () => {
    if (!toRemove) return;
    try {
      await removeMember(projectId, toRemove.id);
      toast.success('Member removed');
      await reload();
    } catch (error) {
      toast.error(getErrorMessage(error));
    }
  };

  return (
    <div className="flex flex-col gap-4">
      {isOwner && (
        <Card className="p-5">
          <section aria-labelledby="share-title" className="max-w-lg">
            <h3 id="share-title" className="text-sm font-semibold">Invite by Email</h3>
            <p className="mb-3 mt-1 text-xs text-ink-soft">Send a time-limited invitation link.</p>
            <ShareForm projectId={projectId} />
          </section>
        </Card>
      )}
      {isOwner && (
        <Card className="p-5">
          <section aria-labelledby="invite-login-title" className="max-w-lg">
            <h3 id="invite-login-title" className="text-sm font-semibold">Invite by Login</h3>
            <p className="mb-3 mt-1 text-xs text-ink-soft">Add an existing user directly by their username.</p>
            <InviteForm projectId={projectId} onDone={reload} />
          </section>
        </Card>
      )}
      <Card className="overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr>
              <th scope="col" className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-ink-soft">Member</th>
              <th scope="col" className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-ink-soft">Role</th>
              <th scope="col" className="hidden px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-ink-soft sm:table-cell">Added</th>
              {isOwner && (
                <th scope="col" className="w-16 px-4 py-3 text-right text-xs font-medium uppercase tracking-wide text-ink-soft">
                  <span className="sr-only">Actions</span>
                </th>
              )}
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
                    {m.role === 'owner' ? 'Owner' : 'Participant'}
                  </Badge>
                </td>
                <td className="hidden px-4 py-3 text-ink-soft sm:table-cell">{formatDate(m.created_at)}</td>
                {isOwner && (
                  <td className="px-4 py-3 text-right">
                    {m.role !== 'owner' && (
                      <button
                        type="button"
                        title={`Remove ${m.login}`}
                        aria-label={`Remove ${m.login}`}
                        onClick={() => setToRemove(m)}
                        className="rounded-lg p-2 text-gray-500 transition-colors hover:bg-red-50 hover:text-danger"
                      >
                        <Trash2 size={18} strokeWidth={1.5} />
                      </button>
                    )}
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      <ConfirmDialog
        open={!!toRemove}
        title="Remove member?"
        message={`Remove ${toRemove?.login ?? ''} from this project?`}
        confirmLabel="Remove"
        onConfirm={handleRemoveMember}
        onClose={() => setToRemove(null)}
      />
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
        <EmptyState icon={Settings} title="Owner only" description="Only the project owner can edit settings or delete this project." />
      </Card>
    );
  }

  return (
    <div className="flex max-w-2xl flex-col gap-6">
      <Card className="p-5">
        <h3 className="mb-4 text-base">General</h3>
        <ProjectForm
          key={project.updated_at}
          initial={project}
          submitLabel="Save Changes"
          onSubmit={async (values) => {
            try {
              await updateProject(projectId, {
                name: values.name.trim(),
                description: values.description?.trim() || null,
              });
              toast.success('Changes saved');
              await reload();
            } catch (error) {
              toast.error(getErrorMessage(error));
            }
          }}
        />
      </Card>

      <Card className="border-danger/30 p-5">
        <h3 className="text-base text-danger">Danger Zone</h3>
        <p className="mb-4 mt-1 text-sm text-ink-soft">
          Deleting a project permanently removes all of its documents and members. This action cannot be undone.
        </p>
        <Button variant="danger" onClick={() => setConfirming(true)}>Delete Project</Button>
      </Card>

      <ConfirmDialog
        open={confirming}
        title="Delete project?"
        message={`Project "${project.name}" and all of its documents will be permanently deleted.`}
        confirmLabel="Delete"
        onConfirm={async () => {
          try {
            await deleteProject(projectId);
            toast.success('Project deleted');
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
