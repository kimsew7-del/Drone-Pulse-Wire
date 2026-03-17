'use client';

import React from 'react';
import { ToastProvider } from '@/components/ui/Toast';
import Topbar from '@/components/layout/Topbar';

export default function ClientProviders({ children }: { children: React.ReactNode }) {
  return (
    <ToastProvider>
      <Topbar />
      <main>{children}</main>
    </ToastProvider>
  );
}
