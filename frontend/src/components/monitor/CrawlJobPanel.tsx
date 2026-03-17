'use client';

import React from 'react';
import type { CrawlJob } from '@/lib/types';
import { classNames } from '@/lib/utils';
import Button from '@/components/ui/Button';

export interface CrawlJobPanelProps {
  job: CrawlJob;
  onReset: () => void;
}

function statusConfig(status: string): { label: string; bg: string; text: string } {
  switch (status?.toLowerCase()) {
    case 'running':
      return { label: 'Running', bg: 'bg-accent/10', text: 'text-accent' };
    case 'completed':
      return { label: 'Completed', bg: 'bg-ok/10', text: 'text-ok' };
    case 'error':
    case 'failed':
      return { label: 'Error', bg: 'bg-danger/10', text: 'text-danger' };
    default:
      return { label: status || 'Idle', bg: 'bg-bg', text: 'text-muted' };
  }
}

function logEntryColor(line: string): string {
  if (line.toLowerCase().includes('error') || line.toLowerCase().includes('fail')) {
    return 'text-danger';
  }
  if (line.toLowerCase().includes('success') || line.toLowerCase().includes('done') || line.toLowerCase().includes('ok')) {
    return 'text-ok';
  }
  return 'text-muted';
}

export default function CrawlJobPanel({ job, onReset }: CrawlJobPanelProps) {
  const { label, bg, text } = statusConfig(job.status);
  const progressPct = job.total > 0 ? Math.round((job.progress / job.total) * 100) : 0;

  return (
    <section className="rounded-3xl bg-white border border-muted/10 p-6 shadow-sm">
      <div className="flex items-center justify-between mb-5">
        <h3 className="font-display font-bold text-text text-base">Crawl Job</h3>
        <Button variant="danger" size="sm" onClick={onReset}>
          Reset
        </Button>
      </div>

      {/* Status */}
      <div className={classNames('inline-flex items-center gap-2 rounded-2xl px-4 py-2 mb-5', bg)}>
        {job.status?.toLowerCase() === 'running' && (
          <span className="relative flex h-2.5 w-2.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-accent opacity-75" />
            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-accent" />
          </span>
        )}
        <span className={classNames('text-sm font-semibold', text)}>{label}</span>
      </div>

      {/* Progress */}
      {job.total > 0 && (
        <div className="mb-5">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-xs text-muted font-medium">
              Progress: {job.progress} / {job.total}
            </span>
            <span className="text-xs font-semibold text-text">{progressPct}%</span>
          </div>
          <div className="h-2 rounded-full bg-bg overflow-hidden">
            <div
              className="h-full rounded-full bg-gradient-to-r from-accent to-accent-2 transition-all duration-500"
              style={{ width: `${progressPct}%` }}
            />
          </div>
        </div>
      )}

      {/* Current seed info */}
      {job.current_seed && (
        <div className="rounded-2xl bg-bg p-3 mb-5">
          <p className="text-[10px] text-muted font-semibold uppercase tracking-wide mb-1">
            Current Seed
          </p>
          <p className="text-xs text-text font-medium truncate">{job.current_seed}</p>
          {job.current_region && (
            <p className="text-[11px] text-muted mt-0.5">Region: {job.current_region}</p>
          )}
          {job.discovered > 0 && (
            <p className="text-[11px] text-muted mt-0.5">Discovered: {job.discovered}</p>
          )}
        </div>
      )}

      {/* Log entries */}
      {(job.log || []).length > 0 && (
        <div className="rounded-2xl bg-bg p-3 max-h-60 overflow-y-auto">
          <p className="text-[10px] text-muted font-semibold uppercase tracking-wide mb-2">
            Log ({job.log.length})
          </p>
          <div className="flex flex-col gap-1">
            {job.log.map((line, idx) => (
              <p
                key={idx}
                className={classNames('text-[11px] font-mono leading-snug', logEntryColor(line))}
              >
                {line}
              </p>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}
