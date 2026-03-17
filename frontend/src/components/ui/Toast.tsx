'use client';

import React, { useState, useCallback, useEffect, createContext, useContext } from 'react';
import { classNames } from '@/lib/utils';

/* ── Types ─────────────────────────────────────────────── */

export type ToastType = 'success' | 'error';

export interface ToastItem {
  id: string;
  title: string;
  message?: string;
  type: ToastType;
}

interface ToastContextValue {
  toasts: ToastItem[];
  addToast: (toast: Omit<ToastItem, 'id'>) => void;
  removeToast: (id: string) => void;
}

/* ── Context ───────────────────────────────────────────── */

const ToastContext = createContext<ToastContextValue | null>(null);

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    throw new Error('useToast must be used inside <ToastProvider>');
  }
  return ctx;
}

/* ── Provider ──────────────────────────────────────────── */

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const addToast = useCallback((toast: Omit<ToastItem, 'id'>) => {
    const id = `toast-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    setToasts((prev) => [...prev, { ...toast, id }]);
  }, []);

  return (
    <ToastContext.Provider value={{ toasts, addToast, removeToast }}>
      {children}
      <ToastContainer toasts={toasts} onDismiss={removeToast} />
    </ToastContext.Provider>
  );
}

/* ── Single Toast ──────────────────────────────────────── */

function Toast({
  item,
  onDismiss,
}: {
  item: ToastItem;
  onDismiss: (id: string) => void;
}) {
  useEffect(() => {
    const timer = setTimeout(() => onDismiss(item.id), 3000);
    return () => clearTimeout(timer);
  }, [item.id, onDismiss]);

  const isSuccess = item.type === 'success';

  return (
    <div
      role="alert"
      className={classNames(
        'pointer-events-auto flex items-start gap-3 w-80 rounded-2xl p-4 shadow-lg border backdrop-blur-sm',
        'animate-[slideIn_0.25s_ease-out]',
        isSuccess
          ? 'bg-white/95 border-ok/30'
          : 'bg-white/95 border-danger/30',
      )}
    >
      {/* Icon */}
      <span
        className={classNames(
          'mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-white text-[11px] font-bold',
          isSuccess ? 'bg-ok' : 'bg-danger',
        )}
      >
        {isSuccess ? '\u2713' : '!'}
      </span>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-text leading-tight">{item.title}</p>
        {item.message && (
          <p className="mt-0.5 text-xs text-muted leading-snug">{item.message}</p>
        )}
      </div>

      {/* Close */}
      <button
        onClick={() => onDismiss(item.id)}
        className="shrink-0 text-muted hover:text-text transition-colors text-lg leading-none -mt-0.5"
        aria-label="Close"
      >
        &times;
      </button>
    </div>
  );
}

/* ── Container ─────────────────────────────────────────── */

function ToastContainer({
  toasts,
  onDismiss,
}: {
  toasts: ToastItem[];
  onDismiss: (id: string) => void;
}) {
  if (!toasts.length) return null;

  return (
    <div className="fixed top-4 right-4 z-[9999] flex flex-col gap-3 pointer-events-none">
      {toasts.map((t) => (
        <Toast key={t.id} item={t} onDismiss={onDismiss} />
      ))}
    </div>
  );
}
