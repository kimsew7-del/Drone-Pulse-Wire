'use client';

import React, { useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import { useToast } from '@/components/ui/Toast';
import Button from '@/components/ui/Button';

export default function LoginPage() {
  const router = useRouter();
  const { login, register } = useAuth();
  const { addToast } = useToast();

  const [isRegister, setIsRegister] = useState(false);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      setError('');

      if (!username.trim() || !password.trim()) {
        setError('Please enter both username and password.');
        return;
      }

      setLoading(true);
      try {
        if (isRegister) {
          await register(username.trim(), password);
          addToast({ type: 'success', title: 'Account created', message: 'Welcome to Briefwave!' });
        } else {
          await login(username.trim(), password);
          addToast({ type: 'success', title: 'Logged in', message: `Welcome back, ${username}!` });
        }
        router.push('/');
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'An error occurred';
        setError(msg);
      } finally {
        setLoading(false);
      }
    },
    [username, password, isRegister, login, register, router, addToast],
  );

  return (
    <div className="min-h-[80vh] flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        {/* Brand header */}
        <div className="text-center mb-8">
          <div className="inline-flex h-14 w-14 rounded-2xl bg-gradient-to-br from-accent to-accent-2 items-center justify-center shadow-lg mb-4">
            <span className="text-white font-display font-bold text-xl leading-none">BW</span>
          </div>
          <h1 className="font-display font-bold text-2xl text-text">
            {isRegister ? 'Create Account' : 'Welcome Back'}
          </h1>
          <p className="text-sm text-muted mt-1">
            {isRegister
              ? 'Sign up for Briefwave intelligence'
              : 'Sign in to your Briefwave account'}
          </p>
        </div>

        {/* Form card */}
        <div className="rounded-3xl bg-white border border-muted/10 p-8 shadow-sm">
          <form onSubmit={handleSubmit} className="flex flex-col gap-5">
            {/* Error */}
            {error && (
              <div className="rounded-2xl bg-danger/10 border border-danger/20 px-4 py-3">
                <p className="text-sm text-red-700 font-medium">{error}</p>
              </div>
            )}

            {/* Username */}
            <div>
              <label
                htmlFor="username"
                className="block text-[11px] text-muted font-semibold uppercase tracking-wide mb-1.5"
              >
                Username
              </label>
              <input
                id="username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Enter your username"
                autoComplete="username"
                className="w-full px-4 py-3 rounded-2xl border border-muted/15 text-sm text-text placeholder:text-muted/50 focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent/40 transition-all bg-bg/30"
              />
            </div>

            {/* Password */}
            <div>
              <label
                htmlFor="password"
                className="block text-[11px] text-muted font-semibold uppercase tracking-wide mb-1.5"
              >
                Password
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter your password"
                autoComplete={isRegister ? 'new-password' : 'current-password'}
                className="w-full px-4 py-3 rounded-2xl border border-muted/15 text-sm text-text placeholder:text-muted/50 focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent/40 transition-all bg-bg/30"
              />
            </div>

            {/* Submit */}
            <Button type="submit" size="lg" loading={loading} className="w-full mt-1">
              {isRegister ? 'Create Account' : 'Sign In'}
            </Button>
          </form>

          {/* Toggle */}
          <div className="text-center mt-6 pt-5 border-t border-muted/10">
            <p className="text-sm text-muted">
              {isRegister ? 'Already have an account?' : "Don't have an account?"}{' '}
              <button
                type="button"
                onClick={() => {
                  setIsRegister((prev) => !prev);
                  setError('');
                }}
                className="text-accent font-semibold hover:text-accent/80 transition-colors"
              >
                {isRegister ? 'Sign In' : 'Sign Up'}
              </button>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
