import { createContext, useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';
import { getMe, loginUser, registerUser } from '../api/auth';
import { TOKEN_KEY } from '../api/client';
import type { User } from '../types';

export interface AuthContextValue {
  user: User | null;
  token: string | null;
  loading: boolean;
  login: (login: string, password: string) => Promise<void>;
  register: (login: string, password: string) => Promise<void>;
  logout: () => void;
  isAuthenticated: boolean;
}

export const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(TOKEN_KEY));
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState<boolean>(() => localStorage.getItem(TOKEN_KEY) !== null);

  // Restore session from a stored token
  useEffect(() => {
    if (!token || user) {
      setLoading(false);
      return;
    }
    let cancelled = false;
    getMe()
      .then((me) => !cancelled && setUser(me))
      .catch(() => {
        if (cancelled) return;
        localStorage.removeItem(TOKEN_KEY);
        setToken(null);
      })
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [token, user]);

  const login = useCallback(async (loginName: string, password: string) => {
    const { access_token } = await loginUser(loginName, password);
    localStorage.setItem(TOKEN_KEY, access_token);
    const me = await getMe();
    setToken(access_token);
    setUser(me);
  }, []);

  const register = useCallback(
    async (loginName: string, password: string) => {
      await registerUser(loginName, password);
      await login(loginName, password);
    },
    [login],
  );

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    setToken(null);
    setUser(null);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({ user, token, loading, login, register, logout, isAuthenticated: !!token && !!user }),
    [user, token, loading, login, register, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
