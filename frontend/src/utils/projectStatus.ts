import type { Project } from '../types';

export type ProjectStatus = { label: string; tone: 'info' | 'warning' | 'success' };

// Status is derived: no documents -> Planned, recently updated -> In Progress, else Completed
export function getProjectStatus(project: Project, documentCount: number): ProjectStatus {
  if (documentCount === 0) return { label: 'Planned', tone: 'warning' };
  const idleDays = (Date.now() - new Date(project.updated_at).getTime()) / 86_400_000;
  return idleDays > 30
    ? { label: 'Completed', tone: 'success' }
    : { label: 'In Progress', tone: 'info' };
}
