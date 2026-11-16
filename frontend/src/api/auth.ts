import { api } from './client';
import type { TokenResponse, User } from '../types';

export interface RegisterPayload {
  login: string;
  email: string;
  password: string;
  repeat_password: string;
}

export async function registerUser(data: RegisterPayload): Promise<User> {
  const res = await api.post<User>('/auth', data);
  return res.data;
}

export async function loginUser(login: string, password: string): Promise<TokenResponse> {
  const { data } = await api.post<TokenResponse>('/login', { login, password });
  return data;
}

export async function getMe(): Promise<User> {
  const { data } = await api.get<User>('/auth/me');
  return data;
}
