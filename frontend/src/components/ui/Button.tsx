'use client';

import React from 'react';
import { classNames } from '@/lib/utils';

export type ButtonVariant = 'primary' | 'secondary' | 'danger';
export type ButtonSize = 'sm' | 'md' | 'lg';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
}

const variantStyles: Record<ButtonVariant, string> = {
  primary:
    'bg-gradient-to-r from-accent to-accent-2 text-white shadow-md hover:shadow-lg hover:brightness-110 active:brightness-95',
  secondary:
    'bg-white border border-muted/30 text-text hover:bg-bg hover:border-accent/40 active:bg-accent/5',
  danger:
    'bg-danger text-white hover:brightness-110 active:brightness-95',
};

const sizeStyles: Record<ButtonSize, string> = {
  sm: 'px-3 py-1.5 text-xs rounded-xl gap-1.5',
  md: 'px-5 py-2.5 text-sm rounded-2xl gap-2',
  lg: 'px-7 py-3.5 text-base rounded-2xl gap-2.5',
};

export default function Button({
  variant = 'primary',
  size = 'md',
  loading = false,
  disabled,
  children,
  className,
  ...rest
}: ButtonProps) {
  const isDisabled = disabled || loading;

  return (
    <button
      disabled={isDisabled}
      className={classNames(
        'inline-flex items-center justify-center font-display font-semibold transition-all duration-200 cursor-pointer select-none',
        variantStyles[variant],
        sizeStyles[size],
        isDisabled && 'opacity-50 cursor-not-allowed pointer-events-none',
        className,
      )}
      {...rest}
    >
      {loading && (
        <svg
          className="animate-spin h-4 w-4 shrink-0"
          viewBox="0 0 24 24"
          fill="none"
        >
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
          />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
          />
        </svg>
      )}
      {children}
    </button>
  );
}
