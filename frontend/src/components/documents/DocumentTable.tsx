import type { Document } from '../../types';
import { DocumentRow } from './DocumentRow';

interface Props {
  documents: Document[];
  onDownload: (doc: Document) => void;
  onReplace: (doc: Document, file: File) => void;
  onDelete: (doc: Document) => void;
}

export function DocumentTable({ documents, ...handlers }: Props) {
  const th = 'px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-ink-soft';
  return (
    <div className="overflow-x-auto">
      <table className="w-full table-fixed text-sm">
        <thead>
          <tr>
            <th scope="col" className={`${th} w-auto`}>Назва</th>
            <th scope="col" className={`${th} hidden w-28 sm:table-cell`}>Тип</th>
            <th scope="col" className={`${th} w-24`}>Розмір</th>
            <th scope="col" className={`${th} hidden w-32 md:table-cell`}>Дата</th>
            <th scope="col" className={`${th} w-32`}><span className="sr-only">Дії</span></th>
          </tr>
        </thead>
        <tbody>
          {documents.map((doc) => (
            <DocumentRow key={doc.id} doc={doc} {...handlers} />
          ))}
        </tbody>
      </table>
    </div>
  );
}
