'use client';

import React from 'react';
import { useNews } from '@/hooks/useNews';
import SourceMonitor from '@/components/monitor/SourceMonitor';
import SignalList from '@/components/analytics/SignalList';
import Badge from '@/components/ui/Badge';

export default function HealthPage() {
  const { data, isLoading } = useNews();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="flex flex-col items-center gap-4">
          <div className="h-10 w-10 rounded-full border-4 border-ok/30 border-t-ok animate-spin" />
          <p className="text-sm text-muted font-medium">Loading health data...</p>
        </div>
      </div>
    );
  }

  const sources = data?.sources || [];
  const sourceStats = data?.source_stats || {};
  const signals = data?.signals || [];
  const meta = data?.meta;

  // Compute summary metrics
  let okCount = 0;
  let warnCount = 0;
  let errorCount = 0;

  sources.forEach((src) => {
    const stats = sourceStats[src.id];
    if (!stats) return;
    if (stats.blocked_reason === 'missing_env_key') {
      warnCount++;
    } else if (stats.last_error) {
      errorCount++;
    } else if (stats.last_checked_at) {
      okCount++;
    }
  });

  const totalFetched = Object.values(sourceStats).reduce(
    (sum, s) => sum + ((s as { fetched_count?: number }).fetched_count || 0),
    0,
  );

  const overallStatus =
    errorCount > 0 ? 'Degraded' : warnCount > 0 ? 'Partial' : 'Healthy';
  const statusColor =
    errorCount > 0 ? 'text-danger' : warnCount > 0 ? 'text-warn' : 'text-ok';
  const statusBg =
    errorCount > 0 ? 'bg-danger/10' : warnCount > 0 ? 'bg-warn/10' : 'bg-ok/10';

  return (
    <div className="max-w-[1200px] mx-auto px-4 sm:px-6 lg:px-8 py-6">
      {/* Hero panel */}
      <section className="rounded-3xl bg-gradient-to-br from-emerald-500 via-teal-500 to-cyan-500 p-8 text-white shadow-lg mb-8 relative overflow-hidden">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_80%_20%,rgba(255,255,255,0.15),transparent_60%)]" />
        <div className="relative z-10">
          <div className="flex items-center gap-3 mb-4">
            <span className="inline-block px-2.5 py-1 rounded-full bg-white/20 text-[10px] font-semibold uppercase tracking-widest">
              System Health
            </span>
            <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold ${statusBg} ${statusColor}`}>
              <span className="relative flex h-2 w-2">
                {errorCount === 0 && warnCount === 0 && (
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-ok opacity-75" />
                )}
                <span className={`relative inline-flex rounded-full h-2 w-2 ${
                  errorCount > 0 ? 'bg-danger' : warnCount > 0 ? 'bg-warn' : 'bg-ok'
                }`} />
              </span>
              {overallStatus}
            </span>
          </div>

          <h2 className="font-display font-bold text-2xl mb-2">Source Status Dashboard</h2>
          <p className="text-sm text-white/85 leading-relaxed mb-6">
            Real-time monitoring of all data sources feeding into Briefwave.
          </p>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="rounded-2xl bg-white/10 backdrop-blur-sm p-4 text-center">
              <span className="block text-2xl font-display font-bold">{sources.length}</span>
              <span className="block text-[11px] text-white/70 mt-1">Total Sources</span>
            </div>
            <div className="rounded-2xl bg-white/10 backdrop-blur-sm p-4 text-center">
              <span className="block text-2xl font-display font-bold">{okCount}</span>
              <span className="block text-[11px] text-white/70 mt-1">Healthy</span>
            </div>
            <div className="rounded-2xl bg-white/10 backdrop-blur-sm p-4 text-center">
              <span className="block text-2xl font-display font-bold">{warnCount}</span>
              <span className="block text-[11px] text-white/70 mt-1">Warnings</span>
            </div>
            <div className="rounded-2xl bg-white/10 backdrop-blur-sm p-4 text-center">
              <span className="block text-2xl font-display font-bold">{totalFetched}</span>
              <span className="block text-[11px] text-white/70 mt-1">Total Fetched</span>
            </div>
          </div>

          {meta && (
            <div className="mt-4 flex flex-wrap gap-2">
              <Badge variant="neutral" className="bg-white/15 text-white border-0">
                Feed: {meta.feed_status}
              </Badge>
              <Badge variant="neutral" className="bg-white/15 text-white border-0">
                Queue: {meta.queued_count}
              </Badge>
              <Badge variant="neutral" className="bg-white/15 text-white border-0">
                Published: {meta.published_count}
              </Badge>
              <Badge variant="neutral" className="bg-white/15 text-white border-0">
                Duplicates: {meta.duplicate_count}
              </Badge>
            </div>
          )}
        </div>
      </section>

      {/* Source monitor grid */}
      <div className="mb-8">
        <h3 className="font-display font-bold text-text text-lg mb-5">Source Monitor</h3>
        <SourceMonitor sources={sources} sourceStats={sourceStats} />
      </div>

      {/* Signals */}
      {signals.length > 0 && (
        <div className="max-w-2xl">
          <SignalList signals={signals} />
        </div>
      )}
    </div>
  );
}
