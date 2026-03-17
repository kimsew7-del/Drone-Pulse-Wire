'use client';

import React from 'react';
import type { NewsItem } from '@/lib/types';
import { formatRelative } from '@/lib/utils';
import Badge from '@/components/ui/Badge';

export interface ReportCardProps {
  item: NewsItem;
}

function docTypeBadgeVariant(docType: string): 'ok' | 'warn' | 'danger' | 'report' | 'neutral' {
  switch (docType?.toLowerCase()) {
    case 'regulation':
    case 'policy':
      return 'warn';
    case 'research':
    case 'paper':
      return 'ok';
    case 'report':
      return 'report';
    case 'alert':
    case 'incident':
      return 'danger';
    default:
      return 'neutral';
  }
}

export default function ReportCard({ item }: ReportCardProps) {
  const displayHeadline = item.translated_headline || item.headline;
  const displaySummary = item.translated_summary || item.summary;
  const showOriginal =
    item.translated_headline && item.translated_headline !== item.headline;

  return (
    <article className="rounded-3xl bg-white border border-muted/10 p-5 shadow-sm hover:shadow-md transition-shadow duration-200">
      {/* Title */}
      <div className="mb-3">
        <h3 className="font-display font-bold text-text text-base leading-snug">
          {displayHeadline}
        </h3>
        {showOriginal && (
          <p className="mt-1 text-xs text-muted/60 italic">{item.headline}</p>
        )}
      </div>

      {/* Summary */}
      {displaySummary && (
        <p className="text-sm text-muted leading-relaxed mb-4">{displaySummary}</p>
      )}

      {/* Badges */}
      <div className="flex flex-wrap gap-1.5 mb-3">
        {item.doc_type && (
          <Badge variant={docTypeBadgeVariant(item.doc_type)}>
            {item.doc_type}
          </Badge>
        )}
        {item.region && <Badge variant="neutral">{item.region}</Badge>}
        {item.source && <Badge variant="category">{item.source}</Badge>}
        <Badge variant="neutral">{formatRelative(item.timestamp)}</Badge>
        <Badge variant="default">Impact {item.impact}</Badge>
      </div>

      {/* Highlight tags */}
      {(item.highlights || []).length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-3">
          {item.highlights.map((h, i) => (
            <span
              key={i}
              className="inline-block px-2.5 py-1 rounded-full bg-accent/8 text-accent text-[11px] font-medium"
            >
              {h}
            </span>
          ))}
        </div>
      )}

      {/* Source link */}
      <a
        href={item.url}
        target="_blank"
        rel="noreferrer"
        className="inline-flex items-center gap-1 text-xs text-accent hover:text-accent/70 font-medium transition-colors"
      >
        View source
        <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
        </svg>
      </a>
    </article>
  );
}
