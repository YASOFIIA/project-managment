import { useCallback, useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import { listDocuments } from '../api/documents';
import type { Document } from '../types';
import { getErrorMessage } from '../utils/errors';

// Documents of a single project with a reload helper
export function useDocuments(projectId: number) {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);

  const reload = useCallback(async () => {
    try {
      setDocuments(await listDocuments(projectId));
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    setLoading(true);
    void reload();
  }, [reload]);

  return { documents, loading, reload };
}
