import axios from 'axios';

export const TOKEN_KEY = 'access_token';

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? '/api',
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// 401 on a protected call -> drop token and go to login (auth endpoints report their own errors)
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const url: string = error.config?.url ?? '';
    const isAuthCall = url === '/login' || url === '/auth';
    if (error.response?.status === 401 && !isAuthCall) {
      localStorage.removeItem(TOKEN_KEY);
      if (window.location.pathname !== '/login') {
        const back = window.location.pathname + window.location.search;
        window.location.href = `/login?redirect=${encodeURIComponent(back)}`;
      }
    }
    return Promise.reject(error);
  },
);
