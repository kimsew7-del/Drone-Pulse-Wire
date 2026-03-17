'use client';

import React, { useState } from 'react';
import type { NewsItem } from '@/lib/types';
import { formatRelative, isKorean, classNames } from '@/lib/utils';
import Badge from '@/components/ui/Badge';

/* ── Helpers ───────────────────────────────────────────── */

const RESEARCH_SOURCES = new Set([
  'Crossref Drone AI Research',
  'Europe PMC AI Robotics',
  'KCI Korea Drone AI Papers',
]);

function classifyItem(item: NewsItem): string {
  if (item.content_type) return item.content_type;
  return RESEARCH_SOURCES.has(item.source) ? 'research' : 'news';
}

function contentTypeBadgeVariant(type: string): 'contentType' | 'report' | 'default' {
  if (type === 'report') return 'report';
  if (type === 'research') return 'contentType';
  return 'default';
}

function contentTypeLabel(type: string): string {
  if (type === 'research') return 'Research';
  if (type === 'report') return 'Report';
  return 'News';
}

/* ── Gradient helper for avatar ────────────────────────── */
function sourceGradient(source: string): string {
  const hash = source.split('').reduce((acc, ch) => acc + ch.charCodeAt(0), 0);
  const gradients = [
    'from-accent to-accent-2',
    'from-accent-2 to-accent-3',
    'from-accent-3 to-accent',
    'from-ok to-accent-2',
    'from-accent to-ok',
    'from-accent-3 to-accent-2',
  ];
  return gradients[hash % gradients.length];
}

/* ── Props ─────────────────────────────────────────────── */

export interface FeedCardProps {
  item: NewsItem;
  onTranslate: (id: string) => void;
  onLike: (id: string) => void;
  onSave: (id: string) => void;
  liked: boolean;
  saved: boolean;
}

/* ── Component ─────────────────────────────────────────── */

export default function FeedCard({
  item,
  onTranslate,
  onLike,
  onSave,
  liked,
  saved,
}: FeedCardProps) {
  const [showRelated, setShowRelated] = useState(false);
  const [shareLabel, setShareLabel] = useState('Share');

  const itemType = classifyItem(item);
  const displayHeadline = item.translated_headline || item.headline;
  const displaySummary = item.translated_summary || item.summary;
  const hideSummary =
    displaySummary === displayHeadline ||
    displaySummary === '요약 정보가 아직 제공되지 않았습니다.';

  const isAlreadyKorean = isKorean(item.headline) && isKorean(item.summary);
  const hasRelated = (item.related_articles || []).length > 0;

  async function handleShare() {
    const payload = `${item.headline}\n${item.url}`;
    if (typeof navigator !== 'undefined' && navigator.share) {
      try {
        await navigator.share({ title: item.headline, text: item.summary, url: item.url });
        return;
      } catch {
        /* user cancelled */
      }
    }
    if (typeof navigator !== 'undefined' && navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(payload);
    }
    setShareLabel('Copied');
    setTimeout(() => setShareLabel('Share'), 1200);
  }

  return (
    <article className="rounded-3xl bg-white border border-muted/10 overflow-hidden shadow-sm hover:shadow-md transition-shadow duration-200">
      {/* Header */}
      <div className="flex items-center gap-3 px-5 pt-5 pb-3">
        {/* Avatar */}
        <div
          className={classNames(
            'h-9 w-9 rounded-full bg-gradient-to-br flex items-center justify-center shrink-0',
            sourceGradient(item.source),
          )}
        >
          <span className="text-white text-[11px] font-bold leading-none">
            {item.source.charAt(0).toUpperCase()}
          </span>
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-semibold text-text truncate">{item.source}</span>
            <span className="text-xs text-muted">{item.region}</span>
            <span className="text-xs text-muted/60">{formatRelative(item.timestamp)}</span>
          </div>
          {/* Badges */}
          <div className="flex flex-wrap gap-1.5 mt-1.5">
            <Badge variant={contentTypeBadgeVariant(itemType)}>
              {contentTypeLabel(itemType)}
            </Badge>
            {item.translated_to_ko && <Badge variant="translation">KO Translated</Badge>}
            {(item.auto_categories || []).map((cat) => (
              <Badge key={cat} variant="category">
                {cat}
              </Badge>
            ))}
          </div>
        </div>
      </div>

      {/* Cover */}
      <div className="mx-5 rounded-2xl bg-gradient-to-br from-bg to-white p-5 mb-3">
        <Badge variant="neutral" className="mb-2">
          {item.topic}
        </Badge>
        <h3 className="font-display font-bold text-text text-base leading-snug">
          {displayHeadline}
        </h3>
        {item.translated_headline && item.translated_headline !== item.headline && (
          <p className="mt-1.5 text-xs text-muted/70 leading-relaxed italic">
            {item.headline}
          </p>
        )}
      </div>

      {/* Body */}
      <div className="px-5 pb-3 space-y-3">
        {/* Summary */}
        {!hideSummary && (
          <p className="text-sm text-muted leading-relaxed">{displaySummary}</p>
        )}

        {/* Duplicate note */}
        {item.duplicate_count > 0 && (
          <p className="text-xs text-muted/70 bg-bg rounded-xl px-3 py-2">
            {item.duplicate_count} duplicate articles merged
            {(item.related_sources || []).length > 0 && (
              <> &middot; {item.related_sources.join(', ')}</>
            )}
          </p>
        )}

        {/* Merged summary */}
        {item.merged_summary && (
          <p className="text-xs text-muted leading-relaxed bg-accent/5 rounded-xl px-3 py-2">
            {item.merged_summary}
          </p>
        )}

        {/* Highlights */}
        {(item.highlights || []).length > 0 && (
          <div className="flex flex-wrap gap-1.5">
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

        {/* Related articles */}
        {hasRelated && showRelated && (
          <div className="rounded-xl bg-bg p-3 space-y-1.5">
            <p className="text-[11px] font-semibold text-muted uppercase tracking-wide mb-1">
              Related ({item.related_articles.length})
            </p>
            {item.related_articles.map((ra) => (
              <a
                key={ra.id}
                href={ra.url}
                target="_blank"
                rel="noreferrer"
                className="block text-xs text-accent hover:text-accent/70 truncate transition-colors"
              >
                {ra.headline}
              </a>
            ))}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between px-5 py-3 border-t border-muted/8">
        <div className="flex items-center gap-1.5">
          <ActionButton active={liked} onClick={() => onLike(item.id)}>
            {liked ? 'Liked' : 'Like'}
          </ActionButton>
          <ActionButton active={saved} onClick={() => onSave(item.id)}>
            {saved ? 'Saved' : 'Save'}
          </ActionButton>
          <ActionButton
            onClick={() => onTranslate(item.id)}
            disabled={isAlreadyKorean && !item.translated_to_ko}
          >
            {item.translated_to_ko ? 'Re-translate' : isAlreadyKorean ? 'Korean' : 'Translate'}
          </ActionButton>
          <ActionButton onClick={handleShare}>{shareLabel}</ActionButton>
          {hasRelated && (
            <ActionButton onClick={() => setShowRelated((p) => !p)}>
              {showRelated ? 'Hide Related' : `Related (${item.related_articles.length})`}
            </ActionButton>
          )}
        </div>

        <div className="flex items-center gap-3">
          <span className="text-xs text-muted font-medium">Impact {item.impact}</span>
          <a
            href={item.url}
            target="_blank"
            rel="noreferrer"
            className="text-xs text-accent hover:text-accent/70 font-medium transition-colors"
          >
            Source
          </a>
        </div>
      </div>
    </article>
  );
}

/* ── Small action button ───────────────────────────────── */

function ActionButton({
  children,
  active,
  disabled,
  onClick,
}: {
  children: React.ReactNode;
  active?: boolean;
  disabled?: boolean;
  onClick?: () => void;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={classNames(
        'px-3 py-1.5 rounded-xl text-[11px] font-medium transition-colors duration-150',
        active
          ? 'bg-accent/15 text-accent'
          : 'bg-bg text-muted hover:text-text hover:bg-muted/10',
        disabled && 'opacity-40 cursor-not-allowed',
      )}
    >
      {children}
    </button>
  );
}
