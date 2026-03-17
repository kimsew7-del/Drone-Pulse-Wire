'use client';

import React from 'react';
import { classNames } from '@/lib/utils';

export type BadgeVariant =
  | 'default'
  | 'contentType'
  | 'translation'
  | 'report'
  | 'category'
  | 'ok'
  | 'warn'
  | 'danger'
  | 'neutral';

export interface BadgeProps {
  variant?: BadgeVariant;
  children: React.ReactNode;
  className?: string;
  onClick?: () => void;
}

const variantStyles: Record<BadgeVariant, string> = {
  default: 'bg-accent/15 text-accent',
  contentType: 'bg-accent-2/20 text-amber-800',
  translation: 'bg-blue-100 text-blue-700',
  report: 'bg-accent-3/20 text-pink-700',
  category: 'bg-bg text-muted hover:bg-accent/10 hover:text-accent cursor-pointer',
  ok: 'bg-ok/15 text-green-700',
  warn: 'bg-warn/15 text-amber-700',
  danger: 'bg-danger/15 text-red-700',
  neutral: 'bg-muted/10 text-muted',
};

export default function Badge({
  variant = 'default',
  children,
  className,
  onClick,
}: BadgeProps) {
  return (
    <span
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      onClick={onClick}
      onKeyDown={onClick ? (e) => { if (e.key === 'Enter' || e.key === ' ') onClick(); } : undefined}
      className={classNames(
        'inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium leading-tight whitespace-nowrap transition-colors duration-150',
        variantStyles[variant],
        className,
      )}
    >
      {children}
    </span>
  );
}
