'use client';

import React from 'react';
import type { Signal } from '@/lib/types';
import Badge from '@/components/ui/Badge';

export interface SignalListProps {
  signals: Signal[];
}

export default function SignalList({ signals }: SignalListProps) {
  if (!signals || signals.length === 0) {
    return null;
  }

  return (
    <section className="rounded-3xl bg-white border border-muted/10 p-5 shadow-sm">
      <h3 className="font-display font-bold text-text text-sm mb-4">Signals</h3>

      <div className="flex flex-col gap-3">
        {signals.map((signal, idx) => (
          <article
            key={idx}
            className="rounded-2xl bg-bg/50 p-4 border border-transparent hover:border-accent/10 transition-colors duration-150"
          >
            <h4 className="font-semibold text-text text-sm leading-snug mb-1">
              {signal.title}
            </h4>
            <p className="text-xs text-muted leading-relaxed mb-2">{signal.copy}</p>
            <Badge variant="neutral">{signal.tag}</Badge>
          </article>
        ))}
      </div>
    </section>
  );
}
