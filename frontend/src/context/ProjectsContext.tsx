import { createContext, useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';
import toast from 'react-hot-toast';
import { listMembers, listProjects } from '../api/projects';
import type { ProjectDetail, ProjectMember } from '../types';
import { getErrorMessage } from '../utils/errors';
import { useAuth } from '../hooks/useAuth';

export interface ProjectsContextValue {
  projects: ProjectDetail[];
  membersByProject: Record<number, ProjectMember[]>;
  loading: boolean;
  reload: () => Promise<void>;
}

export const ProjectsContext = createContext<ProjectsContextValue | null>(null);

// Loads all user projects once, plus members of each (for avatars and role checks)
export function ProjectsProvider({ children }: { children: ReactNode }) {
  const { isAuthenticated } = useAuth();
  const [projects, setProjects] = useState<ProjectDetail[]>([]);
  const [membersByProject, setMembers] = useState<Record<number, ProjectMember[]>>({});
  const [loading, setLoading] = useState(true);

  const reload = useCallback(async () => {
    try {
      const list = await listProjects();
      const entries = await Promise.all(
        list.map(async (p) => [p.id, await listMembers(p.id).catch(() => [])] as const),
      );
      setProjects(list);
      setMembers(Object.fromEntries(entries));
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (isAuthenticated) void reload();
  }, [isAuthenticated, reload]);

  const value = useMemo(
    () => ({ projects, membersByProject, loading, reload }),
    [projects, membersByProject, loading, reload],
  );
  return <ProjectsContext.Provider value={value}>{children}</ProjectsContext.Provider>;
}
