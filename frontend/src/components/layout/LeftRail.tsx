'use client';

import React from 'react';
import type {
  Source,
  FeedMeta,
  Category,
  CategorySnapshot,
  TrendSnapshot,
  Signal,
  NewsItem,
} from '@/lib/types';
import CategoryPanel from '@/components/analytics/CategoryPanel';
import TrendMetrics from '@/components/analytics/TrendMetrics';
import SignalList from '@/components/analytics/SignalList';

export interface LeftRailProps {
  sources: Source[];
  meta: FeedMeta;
  autoCategories: Category[];
  categorySnapshots: CategorySnapshot[];
  trendHistory: TrendSnapshot[];
  signals: Signal[];
  feedItems: NewsItem[];
  onCategoryFilter: (label: string) => void;
}

export default function LeftRail({
  sources,
  meta,
  autoCategories,
  categorySnapshots,
  trendHistory,
  signals,
  feedItems,
  onCategoryFilter,
}: LeftRailProps) {
  return (
    <aside className="flex flex-col gap-5 w-full">
      {/* Hero card */}
      <section className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-accent via-accent-2 to-accent-3 p-6 text-white shadow-lg">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_80%_20%,rgba(255,255,255,0.15),transparent_60%)]" />
        <div className="relative z-10">
          <span className="inline-block px-2.5 py-1 rounded-full bg-white/20 text-[10px] font-semibold uppercase tracking-widest mb-3">
            Global Signal Feed
          </span>
          <p className="text-sm text-white/85 leading-relaxed mb-5">
            AI-powered intelligence aggregating drone, robotics & physical AI
            news from global sources in real time.
          </p>
          <div className="flex gap-4">
            <div className="flex flex-col">
              <span className="text-2xl font-display font-bold leading-none">
                {meta.tracked_sources}
              </span>
              <span className="text-[11px] text-white/70 mt-1">Tracked Sources</span>
            </div>
            <div className="flex flex-col">
              <span className="text-2xl font-display font-bold leading-none">
                {meta.published_count + meta.queued_count}
              </span>
              <span className="text-[11px] text-white/70 mt-1">Feed Items</span>
            </div>
          </div>
        </div>
      </section>

      {/* Category panel */}
      <CategoryPanel
        categorySnapshots={categorySnapshots}
        autoCategories={autoCategories}
        onFilter={onCategoryFilter}
      />

      {/* Trend metrics */}
      <TrendMetrics items={feedItems} trendHistory={trendHistory} />

      {/* Signals */}
      <SignalList signals={signals} />
    </aside>
  );
}
