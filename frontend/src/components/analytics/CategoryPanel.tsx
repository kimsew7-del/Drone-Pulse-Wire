'use client';

import React, { useState, useMemo } from 'react';
import type { Category, CategorySnapshot } from '@/lib/types';
import { classNames } from '@/lib/utils';

export interface CategoryPanelProps {
  categorySnapshots: CategorySnapshot[];
  autoCategories: Category[];
  onFilter: (label: string) => void;
}

type WindowKey = '24h' | '3d' | '7d';

const WINDOWS: { key: WindowKey; label: string }[] = [
  { key: '24h', label: '24h' },
  { key: '3d', label: '3d' },
  { key: '7d', label: '7d' },
];

function momentumDisplay(momentum: string): { arrow: string; label: string; color: string } {
  switch (momentum) {
    case 'rising':
      return { arrow: '\u25B2', label: 'Rising', color: 'text-ok' };
    case 'falling':
      return { arrow: '\u25BC', label: 'Falling', color: 'text-danger' };
    default:
      return { arrow: '\u2014', label: 'Stable', color: 'text-muted' };
  }
}

export default function CategoryPanel({
  categorySnapshots,
  autoCategories,
  onFilter,
}: CategoryPanelProps) {
  const [activeWindow, setActiveWindow] = useState<WindowKey>('24h');

  const categories = useMemo(() => {
    const snapshots = categorySnapshots || [];
    const latest = snapshots[snapshots.length - 1];
    if (latest?.windows) {
      const windowCats = latest.windows[activeWindow];
      if (Array.isArray(windowCats) && windowCats.length > 0) return windowCats;
    }
    return autoCategories || [];
  }, [categorySnapshots, autoCategories, activeWindow]);

  return (
    <section className="rounded-3xl bg-white border border-muted/10 p-5 shadow-sm">
      {/* Header + tabs */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-display font-bold text-text text-sm">Auto Categories</h3>
        <div className="flex gap-1 bg-bg rounded-xl p-0.5">
          {WINDOWS.map((w) => (
            <button
              key={w.key}
              onClick={() => setActiveWindow(w.key)}
              className={classNames(
                'px-3 py-1 rounded-lg text-[11px] font-semibold transition-all duration-150',
                activeWindow === w.key
                  ? 'bg-white text-accent shadow-sm'
                  : 'text-muted hover:text-text',
              )}
            >
              {w.label}
            </button>
          ))}
        </div>
      </div>

      {/* Categories */}
      {categories.length === 0 ? (
        <p className="text-xs text-muted py-4 text-center">Collecting category data...</p>
      ) : (
        <div className="flex flex-col gap-2.5">
          {categories.map((cat) => {
            const m = momentumDisplay(cat.momentum);
            return (
              <button
                key={cat.label}
                onClick={() => onFilter(cat.label)}
                className="group text-left rounded-2xl p-3 bg-bg/50 hover:bg-accent/5 border border-transparent hover:border-accent/15 transition-all duration-150"
              >
                {/* Top row */}
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-sm font-semibold text-text group-hover:text-accent transition-colors">
                    {cat.label}
                  </span>
                  <span className={classNames('text-[11px] font-medium', m.color)}>
                    {m.arrow} {m.label}
                  </span>
                </div>

                {/* Meta row */}
                <div className="flex items-center gap-3 mb-2">
                  <span className="text-[11px] text-muted">
                    {cat.article_count || 0} articles
                  </span>
                  <span className="text-[11px] text-muted">
                    Impact {cat.avg_impact || '-'}
                  </span>
                </div>

                {/* Terms */}
                {(cat.terms || []).length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {cat.terms.slice(0, 4).map((term) => (
                      <span
                        key={term}
                        className="inline-block px-2 py-0.5 rounded-full bg-white text-[10px] text-muted font-medium border border-muted/10"
                      >
                        {term}
                      </span>
                    ))}
                  </div>
                )}
              </button>
            );
          })}
        </div>
      )}
    </section>
  );
}
