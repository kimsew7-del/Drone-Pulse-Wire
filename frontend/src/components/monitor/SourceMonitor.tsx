'use client';

import React, { useMemo } from 'react';
import type { Source, SourceStat } from '@/lib/types';
import { formatRelative, classNames } from '@/lib/utils';
import Badge from '@/components/ui/Badge';

export interface SourceMonitorProps {
  sources: Source[];
  sourceStats: Record<string, SourceStat>;
}

/* ── Helpers (ported from app.js) ──────────────────────── */

function getSourceStatus(
  stats: Partial<SourceStat>,
  _source: Source,
): { label: string; tone: 'ok' | 'warn' | 'danger' | 'neutral' } {
  if (stats.blocked_reason === 'missing_env_key') {
    return { label: 'Key Pending', tone: 'warn' };
  }
  if (stats.last_error) {
    return { label: 'Error', tone: 'danger' };
  }
  if (stats.last_checked_at && (stats.fetched_count ?? 0) === 0) {
    return { label: 'Waiting', tone: 'neutral' };
  }
  if (stats.last_checked_at) {
    return { label: 'OK', tone: 'ok' };
  }
  return { label: 'Unchecked', tone: 'neutral' };
}

function classifySource(source: Source): string {
  if (source.type === 'crossref' || source.type === 'europepmc') {
    return 'Research';
  }
  return 'News';
}

function formatSourceError(error: string | null): string {
  if (!error) return 'None';
  if (error === 'network_error') return 'Network';
  if (error === 'collection_error') return 'Collection';
  return error;
}

/* ── Component ─────────────────────────────────────────── */

export default function SourceMonitor({ sources, sourceStats }: SourceMonitorProps) {
  const metrics = useMemo(() => {
    let ok = 0;
    let warn = 0;
    let error = 0;

    sources.forEach((src) => {
      const stats = sourceStats[src.id] || {};
      const status = getSourceStatus(stats as Partial<SourceStat>, src);
      if (status.tone === 'ok') ok++;
      else if (status.tone === 'warn') warn++;
      else if (status.tone === 'danger') error++;
    });

    return { ok, warn, error };
  }, [sources, sourceStats]);

  return (
    <section className="flex flex-col gap-5">
      {/* Metric summary */}
      <div className="grid grid-cols-3 gap-3">
        <MetricTile label="OK" value={metrics.ok} color="bg-ok/10 text-ok" />
        <MetricTile label="Warning" value={metrics.warn} color="bg-warn/10 text-warn" />
        <MetricTile label="Error" value={metrics.error} color="bg-danger/10 text-danger" />
      </div>

      {/* Source cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {sources.map((source) => {
          const stats = (sourceStats[source.id] || {}) as Partial<SourceStat>;
          const status = getSourceStatus(stats, source);

          return (
            <article
              key={source.id}
              className="rounded-3xl bg-white border border-muted/10 p-5 shadow-sm hover:shadow-md transition-shadow duration-200"
            >
              {/* Header */}
              <div className="flex items-center justify-between mb-3">
                <h4 className="font-display font-bold text-text text-sm truncate pr-2">
                  {source.name}
                </h4>
                <Badge variant={status.tone}>{status.label}</Badge>
              </div>

              {/* Tags */}
              <div className="flex gap-1.5 mb-3">
                <Badge variant="contentType">{source.type.toUpperCase()}</Badge>
                <Badge variant="neutral">{classifySource(source)}</Badge>
              </div>

              {/* URL */}
              <p className="text-[11px] text-muted truncate mb-3" title={source.url}>
                {source.url}
              </p>

              {/* Metrics */}
              <div className="flex items-center gap-4 text-[11px] text-muted mb-2">
                <span>Fetched: {stats.fetched_count ?? 0}</span>
                <span>Errors: {formatSourceError(stats.last_error ?? null)}</span>
              </div>

              {/* Timestamps */}
              <p className="text-[10px] text-muted/60">
                Last check: {formatRelative(stats.last_checked_at ?? null)} &middot;
                Last success: {formatRelative(stats.last_success_at ?? null)}
              </p>
            </article>
          );
        })}
      </div>
    </section>
  );
}

/* ── Metric tile ───────────────────────────────────────── */

function MetricTile({
  label,
  value,
  color,
}: {
  label: string;
  value: number;
  color: string;
}) {
  return (
    <div className={classNames('rounded-2xl p-4 text-center', color)}>
      <span className="block text-2xl font-display font-bold">{value}</span>
      <span className="block text-[11px] font-medium mt-0.5">{label}</span>
    </div>
  );
}
