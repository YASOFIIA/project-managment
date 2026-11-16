import { api } from './client';
import type { MembershipResponse, PendingInvitation } from '../types';

export type { PendingInvitation };

export const getPendingInvitations = async (): Promise<PendingInvitation[]> =>
  (await api.get<PendingInvitation[]>('/invitations')).data;

export const acceptInvitation = async (invitationId: number): Promise<MembershipResponse> =>
  (await api.post<MembershipResponse>(`/invitations/${invitationId}/accept`)).data;

export const declineInvitation = async (invitationId: number): Promise<void> => {
  await api.post(`/invitations/${invitationId}/decline`);
};
