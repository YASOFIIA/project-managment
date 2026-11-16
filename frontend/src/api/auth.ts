import { api } from './client';
import type { TokenResponse, User } from '../types';

export async function registerUser(login: string, password: string): Promise<User> {
  const { data } = await api.post<User>('/auth', { login, password, repeat_password: password });
  return data;
}

export async function loginUser(login: string, password: string): Promise<TokenResponse> {
  const { data } = await api.post<TokenResponse>('/login', { login, password });
  return data;
}

export async function getMe(): Promise<User> {
  const { data } = await api.get<User>('/auth/me');
  return data;
}
