'use client';

import React from 'react';
import type { NewsItem } from '@/lib/types';
import SearchBar from '@/components/feed/SearchBar';
import FeedCard from '@/components/feed/FeedCard';

export interface FeedColumnProps {
  items: NewsItem[];
  onSearch: (query: string) => void;
  onRefresh: () => void;
  isRefreshing: boolean;
  onTranslate: (id: string) => void;
  likedIds: Set<string>;
  savedIds: Set<string>;
  onLike: (id: string) => void;
  onSave: (id: string) => void;
}

export default function FeedColumn({
  items,
  onSearch,
  onRefresh,
  isRefreshing,
  onTranslate,
  likedIds,
  savedIds,
  onLike,
  onSave,
}: FeedColumnProps) {
  return (
    <div className="flex flex-col gap-4 w-full">
      <SearchBar onSearch={onSearch} onRefresh={onRefresh} isRefreshing={isRefreshing} />

      {/* Results count */}
      <p className="text-xs text-muted font-medium px-1">
        {items.length} article{items.length !== 1 ? 's' : ''}
      </p>

      {/* Feed list */}
      {items.length === 0 ? (
        <div className="rounded-3xl border border-dashed border-muted/20 p-12 text-center">
          <p className="text-sm text-muted">No articles match the current filters.</p>
        </div>
      ) : (
        <div className="flex flex-col gap-4">
          {items.map((item, index) => (
            <div
              key={item.id}
              className="animate-[fadeIn_0.3s_ease-out_both]"
              style={{ animationDelay: `${index * 50}ms` }}
            >
              <FeedCard
                item={item}
                onTranslate={onTranslate}
                onLike={onLike}
                onSave={onSave}
                liked={likedIds.has(item.id)}
                saved={savedIds.has(item.id)}
              />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
