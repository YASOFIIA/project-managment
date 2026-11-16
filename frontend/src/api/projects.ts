import { api } from './client';
import type {
  InvitationResponse,
  MembershipResponse,
  Project,
  ProjectDetail,
  ProjectMember,
} from '../types';

export interface ProjectPayload {
  name: string;
  description?: string | null;
}

export const listProjects = async (): Promise<ProjectDetail[]> =>
  (await api.get<ProjectDetail[]>('/projects')).data;

export const createProject = async (payload: ProjectPayload): Promise<Project> =>
  (await api.post<Project>('/projects', payload)).data;

export const getProject = async (id: number): Promise<Project> =>
  (await api.get<Project>(`/project/${id}/info`)).data;

export const updateProject = async (id: number, payload: ProjectPayload): Promise<Project> =>
  (await api.put<Project>(`/project/${id}/info`, payload)).data;

export const deleteProject = async (id: number): Promise<void> => {
  await api.delete(`/project/${id}`);
};

export const listMembers = async (id: number): Promise<ProjectMember[]> =>
  (await api.get<ProjectMember[]>(`/project/${id}/members`)).data;

export const inviteByLogin = async (id: number, login: string): Promise<MembershipResponse> =>
  (await api.post<MembershipResponse>(`/project/${id}/invite`, null, { params: { user: login } }))
    .data;

export const shareByEmail = async (id: number, email: string): Promise<InvitationResponse> =>
  (await api.get<InvitationResponse>(`/project/${id}/share`, { params: { with: email } })).data;

export const joinByToken = async (token: string): Promise<MembershipResponse> =>
  (await api.get<MembershipResponse>('/join', { params: { token } })).data;
