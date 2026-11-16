import type { Project } from '../types';

export type ProjectStatus = { label: string; tone: 'info' | 'warning' | 'success' };

// Status is derived: no documents -> planned, recently updated -> in progress, else done
export function getProjectStatus(project: Project, documentCount: number): ProjectStatus {
  if (documentCount === 0) return { label: 'Планується', tone: 'warning' };
  const idleDays = (Date.now() - new Date(project.updated_at).getTime()) / 86_400_000;
  return idleDays > 30
    ? { label: 'Завершено', tone: 'success' }
    : { label: 'В роботі', tone: 'info' };
}
