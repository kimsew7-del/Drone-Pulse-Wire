'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import { classNames } from '@/lib/utils';
import Button from '@/components/ui/Button';

export default function Topbar() {
  const { user, logout } = useAuth();
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-50 flex items-center justify-between px-6 py-3 bg-white/80 backdrop-blur-md border-b border-muted/10">
      {/* Brand lockup */}
      <Link href="/" className="flex items-center gap-3 group">
        {/* BW mark */}
        <div className="h-9 w-9 rounded-xl bg-gradient-to-br from-accent to-accent-2 flex items-center justify-center shadow-sm group-hover:shadow-md transition-shadow">
          <span className="text-white font-display font-bold text-sm leading-none">BW</span>
        </div>
        <div className="flex flex-col">
          <span className="text-[10px] font-medium uppercase tracking-widest text-muted leading-none">
            Tech Intelligence Feed
          </span>
          <h1 className="font-display text-xl font-bold text-text leading-tight -mt-0.5">
            Briefwave
          </h1>
        </div>
      </Link>

      {/* Right side */}
      <nav className="flex items-center gap-2">
        <Link
          href="/monitor"
          className={classNames(
            'px-4 py-1.5 rounded-full text-sm font-medium transition-colors duration-150',
            pathname === '/monitor'
              ? 'bg-accent text-white'
              : 'bg-bg text-muted hover:text-text hover:bg-accent/10',
          )}
        >
          Report Monitor
        </Link>

        <Link
          href="/health"
          className={classNames(
            'px-4 py-1.5 rounded-full text-sm font-medium transition-colors duration-150',
            pathname === '/health'
              ? 'bg-ok text-white'
              : 'bg-bg text-muted hover:text-text hover:bg-ok/10',
          )}
        >
          Health
        </Link>

        {user ? (
          <div className="flex items-center gap-2 ml-2">
            <span className="text-xs text-muted font-medium">{user.username}</span>
            <Button variant="secondary" size="sm" onClick={logout}>
              Logout
            </Button>
          </div>
        ) : (
          <Link href="/login">
            <Button variant="primary" size="sm">
              Login
            </Button>
          </Link>
        )}
      </nav>
    </header>
  );
}
