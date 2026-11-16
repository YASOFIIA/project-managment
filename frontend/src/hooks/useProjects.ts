import { useContext } from 'react';
import { ProjectsContext, type ProjectsContextValue } from '../context/ProjectsContext';
import type { Role } from '../types';
import { useAuth } from './useAuth';

export function useProjects(): ProjectsContextValue {
  const ctx = useContext(ProjectsContext);
  if (!ctx) throw new Error('useProjects must be used inside ProjectsProvider');
  return ctx;
}

// Role of the current user in a project (null if unknown / not loaded yet)
export function useProjectRole(projectId: number): Role | null {
  const { user } = useAuth();
  const { membersByProject } = useProjects();
  return membersByProject[projectId]?.find((m) => m.user_id === user?.id)?.role ?? null;
}

// Returns a checker: is the current user the owner of a given project
export function useIsOwnerOf(): (projectId: number) => boolean {
  const { user } = useAuth();
  const { membersByProject } = useProjects();
  return (projectId) =>
    !!membersByProject[projectId]?.some((m) => m.user_id === user?.id && m.role === 'owner');
}
