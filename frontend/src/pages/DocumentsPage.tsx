import { Link } from 'react-router-dom';
import toast from 'react-hot-toast';
import { Download, FileText } from 'lucide-react';
import { downloadDocument } from '../api/documents';
import { FileTypeIcon } from '../components/documents/DocumentRow';
import { Card } from '../components/ui/Card';
import { EmptyState } from '../components/ui/EmptyState';
import { useProjects } from '../hooks/useProjects';
import { getErrorMessage } from '../utils/errors';
import { formatBytes } from '../utils/formatBytes';
import { formatDate } from '../utils/formatDate';

// Global list of documents across all projects
export default function DocumentsPage() {
  const { projects, loading } = useProjects();
  const rows = projects
    .flatMap((p) => p.documents.map((d) => ({ doc: d, project: p })))
    .sort((a, b) => b.doc.created_at.localeCompare(a.doc.created_at));

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h2 className="text-2xl">Документи</h2>
        <p className="mt-1 text-sm text-ink-soft">Усі файли з ваших проєктів</p>
      </div>
      <Card className="overflow-hidden">
        {!loading && rows.length === 0 ? (
          <EmptyState icon={FileText} title="Документів поки немає" description="Завантажте файли на сторінці проєкту." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs font-medium uppercase tracking-wide text-ink-soft">
                  <th scope="col" className="px-4 py-3">Назва</th>
                  <th scope="col" className="hidden px-4 py-3 sm:table-cell">Проєкт</th>
                  <th scope="col" className="px-4 py-3">Розмір</th>
                  <th scope="col" className="hidden px-4 py-3 md:table-cell">Дата</th>
                  <th scope="col" className="px-4 py-3"><span className="sr-only">Дії</span></th>
                </tr>
              </thead>
              <tbody>
                {rows.map(({ doc, project }) => (
                  <tr key={doc.id} className="border-t border-line hover:bg-white/50">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-3">
                        <FileTypeIcon filename={doc.filename} />
                        <span className="font-medium">{doc.filename}</span>
                      </div>
                    </td>
                    <td className="hidden px-4 py-3 sm:table-cell">
                      <Link to={`/project/${project.id}`} className="text-ink-soft hover:text-accent">{project.name}</Link>
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-ink-soft">{formatBytes(doc.file_size_bytes)}</td>
                    <td className="hidden whitespace-nowrap px-4 py-3 text-ink-soft md:table-cell">{formatDate(doc.created_at)}</td>
                    <td className="px-4 py-3 text-right">
                      <button
                        type="button"
                        aria-label={`Завантажити ${doc.filename}`}
                        title="Скачати"
                        className="rounded-btn p-1.5 text-ink-soft transition-colors hover:bg-black/5 hover:text-ink"
                        onClick={() => downloadDocument(doc.id, doc.filename).catch((e) => toast.error(getErrorMessage(e)))}
                      >
                        <Download size={18} strokeWidth={1.5} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
