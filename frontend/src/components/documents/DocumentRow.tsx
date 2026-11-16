import { useRef } from 'react';
import { Download, File as FileIcon, FileImage, FileText, RefreshCw, Trash2 } from 'lucide-react';
import type { Document } from '../../types';
import { ACCEPT_ATTR, getFileKind } from '../../utils/fileType';
import { formatBytes } from '../../utils/formatBytes';
import { formatDate } from '../../utils/formatDate';

interface Props {
  doc: Document;
  onDownload: (doc: Document) => void;
  onReplace: (doc: Document, file: File) => void;
  onDelete: (doc: Document) => void;
}

export function FileTypeIcon({ filename, size = 18 }: { filename: string; size?: number }) {
  const kind = getFileKind(filename);
  const props = { size, strokeWidth: 1.5, 'aria-hidden': true } as const;
  if (kind === 'image') return <FileImage {...props} className="text-emerald-500" />;
  if (kind === 'pdf') return <FileText {...props} className="text-red-500" />;
  if (kind === 'doc') return <FileText {...props} className="text-blue-500" />;
  return <FileIcon {...props} className="text-ink-soft" />;
}

const KIND_LABEL = { pdf: 'PDF', doc: 'DOCX', image: 'Image', other: 'File' } as const;

export function DocumentRow({ doc, onDownload, onReplace, onDelete }: Props) {
  const replaceRef = useRef<HTMLInputElement>(null);

  return (
    <tr className="border-t border-line transition-colors hover:bg-white/50">
      <td className="max-w-0 px-4 py-3">
        <div className="flex items-center gap-3">
          <FileTypeIcon filename={doc.filename} />
          <span className="truncate font-medium" title={doc.filename}>
            {doc.filename}
          </span>
        </div>
      </td>
      <td className="hidden whitespace-nowrap px-4 py-3 text-ink-soft sm:table-cell">
        {KIND_LABEL[getFileKind(doc.filename)]}
      </td>
      <td className="whitespace-nowrap px-4 py-3 text-ink-soft">{formatBytes(doc.file_size_bytes)}</td>
      <td className="hidden whitespace-nowrap px-4 py-3 text-ink-soft md:table-cell">
        {formatDate(doc.created_at)}
      </td>
      <td className="whitespace-nowrap px-4 py-3">
        <div className="flex justify-end gap-1">
          <button
            type="button"
            title="Download"
            aria-label={`Download ${doc.filename}`}
            onClick={() => onDownload(doc)}
            className="rounded-lg p-2 text-gray-500 transition-colors hover:bg-gray-100 hover:text-gray-700"
          >
            <Download size={18} strokeWidth={1.5} />
          </button>
          <button
            type="button"
            title="Replace"
            aria-label={`Replace ${doc.filename}`}
            onClick={() => replaceRef.current?.click()}
            className="rounded-lg p-2 text-gray-500 transition-colors hover:bg-gray-100 hover:text-gray-700"
          >
            <RefreshCw size={18} strokeWidth={1.5} />
          </button>
          <button
            type="button"
            title="Delete"
            aria-label={`Delete ${doc.filename}`}
            onClick={() => onDelete(doc)}
            className="rounded-lg p-2 text-gray-500 transition-colors hover:bg-gray-100 hover:text-danger"
          >
            <Trash2 size={18} strokeWidth={1.5} />
          </button>
          <input
            ref={replaceRef}
            type="file"
            hidden
            accept={ACCEPT_ATTR}
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) onReplace(doc, file);
              e.target.value = '';
            }}
          />
        </div>
      </td>
    </tr>
  );
}
