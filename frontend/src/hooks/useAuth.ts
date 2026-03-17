'use client';

import { useState, useEffect, useCallback } from 'react';
import { login as apiLogin, register as apiRegister, apiFetch } from '@/lib/api';
import type { User, AuthState } from '@/lib/types';

const TOKEN_KEY = 'briefwave-token';

export function useAuth(): AuthState & {
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, password: string) => Promise<void>;
  logout: () => void;
} {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);

  // Load token from localStorage on mount and fetch user info
  useEffect(() => {
    const stored = localStorage.getItem(TOKEN_KEY);
    if (stored) {
      setToken(stored);
      apiFetch<User>('/api/auth/me', {
        headers: { Authorization: `Bearer ${stored}` },
      })
        .then((u) => setUser(u))
        .catch(() => {
          localStorage.removeItem(TOKEN_KEY);
          setToken(null);
          setUser(null);
        });
    }
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    const res = await apiLogin(username, password);
    localStorage.setItem(TOKEN_KEY, res.access_token);
    setToken(res.access_token);
    setUser(res.user);
  }, []);

  const register = useCallback(async (username: string, password: string) => {
    const res = await apiRegister(username, password);
    localStorage.setItem(TOKEN_KEY, res.access_token);
    setToken(res.access_token);
    setUser(res.user);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    setToken(null);
    setUser(null);
  }, []);

  return { user, token, login, register, logout };
}
