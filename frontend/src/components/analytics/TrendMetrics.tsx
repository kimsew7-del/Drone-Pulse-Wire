'use client';

import React, { useMemo } from 'react';
import type { NewsItem, TrendSnapshot } from '@/lib/types';
import { formatDelta, classNames } from '@/lib/utils';

/* ── Trend terms (from app.js) ─────────────────────────── */

const TREND_TERMS = [
  'drone', 'uav', 'swarm', 'delivery', 'ai', 'autonomous',
  'robotics', 'inspection', 'mapping', 'navigation', 'vision',
  'airspace', 'defense', 'safety', 'semiconductor', 'edge',
];

/* ── Analytics helpers ─────────────────────────────────── */

function extractTrendScores(items: NewsItem[]) {
  const scores = new Map<string, number>();

  items.forEach((item) => {
    const text = [item.headline, item.summary, ...(item.highlights || [])]
      .join(' ')
      .toLowerCase();

    TREND_TERMS.forEach((term) => {
      if (text.includes(term)) {
        scores.set(term, (scores.get(term) || 0) + 1);
      }
    });
  });

  return [...scores.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, 6)
    .map(([term, count]) => ({ term, count }));
}

function buildAnalytics(items: NewsItem[]) {
  const now = Date.now();
  const recentWindow = items.filter((item) => {
    const ts = new Date(item.timestamp).getTime();
    return Number.isFinite(ts) && now - ts <= 72 * 60 * 60 * 1000;
  });
  const averageImpact = items.length
    ? Math.round(items.reduce((sum, i) => sum + (Number(i.impact) || 0), 0) / items.length)
    : 0;

  return { total: items.length, recent: recentWindow.length, averageImpact };
}

function buildDeltaMap(trendHistory: TrendSnapshot[]) {
  const history = trendHistory || [];
  const latest = history[history.length - 1];
  const previous = history[history.length - 2];
  const deltas = new Map<string, number>();

  if (!latest) return deltas;

  Object.entries(latest.keyword_counts || {}).forEach(([term, count]) => {
    const prev = previous?.keyword_counts?.[term] || 0;
    deltas.set(term, count - prev);
  });

  return deltas;
}

/* ── Props ─────────────────────────────────────────────── */

export interface TrendMetricsProps {
  items: NewsItem[];
  trendHistory: TrendSnapshot[];
}

/* ── Component ─────────────────────────────────────────── */

export default function TrendMetrics({ items, trendHistory }: TrendMetricsProps) {
  const trends = useMemo(() => extractTrendScores(items), [items]);
  const analytics = useMemo(() => buildAnalytics(items), [items]);
  const deltaMap = useMemo(() => buildDeltaMap(trendHistory), [trendHistory]);

  const leader = trends[0];
  const leaderShare = analytics.total && leader
    ? Math.round((leader.count / analytics.total) * 100)
    : 0;

  return (
    <section className="rounded-3xl bg-white border border-muted/10 p-5 shadow-sm">
      <h3 className="font-display font-bold text-text text-sm mb-4">Trend Metrics</h3>

      {/* Metric tiles */}
      <div className="grid grid-cols-3 gap-2 mb-5">
        {[
          { label: 'Feed Volume', value: `${analytics.total}` },
          { label: '72h Window', value: `${analytics.recent}` },
          { label: 'Avg Impact', value: `${analytics.averageImpact || '-'}` },
        ].map((m) => (
          <div key={m.label} className="rounded-2xl bg-bg p-3 text-center">
            <span className="block text-[10px] text-muted font-medium uppercase tracking-wide mb-1">
              {m.label}
            </span>
            <span className="block text-lg font-display font-bold text-text">{m.value}</span>
          </div>
        ))}
      </div>

      {/* Trend summary */}
      {leader ? (
        <div className="mb-4">
          <span className="font-display font-bold text-accent text-sm uppercase tracking-wide">
            {leader.term}
          </span>
          <p className="text-xs text-muted leading-relaxed mt-1">
            Most repeated keyword across the recent feed, observed in {leaderShare}% of articles.
            Day-over-day: {formatDelta(deltaMap.get(leader.term) || 0)}.
          </p>
        </div>
      ) : (
        <p className="text-xs text-muted mb-4">Aggregating trends...</p>
      )}

      {/* Trend list */}
      {trends.length > 0 && (
        <div className="flex flex-col gap-2">
          {trends.map((t, idx) => {
            const barWidth = leader
              ? Math.max((t.count / leader.count) * 100, 18)
              : 18;
            const delta = deltaMap.get(t.term) || 0;

            return (
              <div key={t.term} className="flex items-center gap-3">
                <span className="text-[11px] font-bold text-muted/40 w-5 text-right shrink-0">
                  {String(idx + 1).padStart(2, '0')}
                </span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-semibold text-text">{t.term}</span>
                    <span className="text-[10px] text-muted">
                      {t.count} mentions &middot; {formatDelta(delta)}
                    </span>
                  </div>
                  <div className="h-1.5 rounded-full bg-bg overflow-hidden">
                    <div
                      className={classNames(
                        'h-full rounded-full transition-all duration-500',
                        idx === 0
                          ? 'bg-gradient-to-r from-accent to-accent-2'
                          : 'bg-accent/30',
                      )}
                      style={{ width: `${barWidth}%` }}
                    />
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
