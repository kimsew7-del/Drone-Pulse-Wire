'use client';

import React, { useState, useCallback, useMemo } from 'react';
import { useNews } from '@/hooks/useNews';
import { useAuth } from '@/hooks/useAuth';
import { useLocalStorage } from '@/hooks/useLocalStorage';
import { refreshFeed, translateArticle } from '@/lib/api';
import { useToast } from '@/components/ui/Toast';
import LeftRail from '@/components/layout/LeftRail';
import FeedColumn from '@/components/feed/FeedColumn';
import RightRail from '@/components/layout/RightRail';

export default function HomePage() {
  const { data, isLoading, mutate } = useNews();
  const { token } = useAuth();
  const { addToast } = useToast();

  const [searchQuery, setSearchQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [isRefreshing, setIsRefreshing] = useState(false);

  const [likedArray, setLikedArray] = useLocalStorage<string[]>('briefwave-liked', []);
  const [savedArray, setSavedArray] = useLocalStorage<string[]>('briefwave-saved', []);

  const likedIds = useMemo(() => new Set(likedArray), [likedArray]);
  const savedIds = useMemo(() => new Set(savedArray), [savedArray]);

  // Combine published + queued news items
  const allItems = useMemo(() => {
    if (!data) return [];
    return [...(data.published || []), ...(data.news || [])];
  }, [data]);

  // Filter and sort
  const filteredItems = useMemo(() => {
    let items = allItems;

    // Search filter
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      items = items.filter((item) => {
        const text = [
          item.headline,
          item.translated_headline,
          item.summary,
          item.translated_summary,
          item.source,
          item.region,
          item.topic,
          ...(item.auto_categories || []),
        ]
          .filter(Boolean)
          .join(' ')
          .toLowerCase();
        return text.includes(q);
      });
    }

    // Category filter
    if (categoryFilter) {
      const label = categoryFilter.toLowerCase();
      items = items.filter((item) => {
        const cats = (item.auto_categories || []).map((c) => c.toLowerCase());
        const text = `${item.headline} ${item.summary}`.toLowerCase();
        return cats.some((c) => c.includes(label)) || text.includes(label);
      });
    }

    // Sort by timestamp descending
    items.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());

    return items;
  }, [allItems, searchQuery, categoryFilter]);

  // Handlers
  const handleSearch = useCallback((query: string) => {
    setSearchQuery(query);
  }, []);

  const handleCategoryFilter = useCallback((label: string) => {
    setCategoryFilter((prev) => (prev === label ? '' : label));
  }, []);

  const handleRefresh = useCallback(async () => {
    if (!token) {
      addToast({ type: 'error', title: 'Login required', message: 'Please log in to refresh the feed.' });
      return;
    }
    setIsRefreshing(true);
    try {
      await refreshFeed(token);
      await mutate();
      addToast({ type: 'success', title: 'Feed refreshed' });
    } catch (err) {
      addToast({ type: 'error', title: 'Refresh failed', message: String(err) });
    } finally {
      setIsRefreshing(false);
    }
  }, [token, mutate, addToast]);

  const handleTranslate = useCallback(
    async (id: string) => {
      if (!token) {
        addToast({ type: 'error', title: 'Login required', message: 'Please log in to translate.' });
        return;
      }
      try {
        await translateArticle(id, token);
        await mutate();
        addToast({ type: 'success', title: 'Translation complete' });
      } catch (err) {
        addToast({ type: 'error', title: 'Translation failed', message: String(err) });
      }
    },
    [token, mutate, addToast],
  );

  const handleLike = useCallback(
    (id: string) => {
      setLikedArray((prev) =>
        prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
      );
    },
    [setLikedArray],
  );

  const handleSave = useCallback(
    (id: string) => {
      setSavedArray((prev) =>
        prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
      );
    },
    [setSavedArray],
  );

  // Loading state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="flex flex-col items-center gap-4">
          <div className="h-10 w-10 rounded-full border-4 border-accent/30 border-t-accent animate-spin" />
          <p className="text-sm text-muted font-medium">Loading feed...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 py-6">
      {/* Category filter indicator */}
      {categoryFilter && (
        <div className="mb-4 flex items-center gap-2">
          <span className="text-xs text-muted font-medium">Filtering by category:</span>
          <button
            onClick={() => setCategoryFilter('')}
            className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-accent/15 text-accent text-xs font-semibold hover:bg-accent/25 transition-colors"
          >
            {categoryFilter}
            <span className="text-sm leading-none">&times;</span>
          </button>
        </div>
      )}

      {/* 3-column layout */}
      <div className="grid grid-cols-1 lg:grid-cols-[300px_1fr_300px] xl:grid-cols-[340px_1fr_340px] gap-6">
        {/* Left rail */}
        <div className="hidden lg:block">
          <LeftRail
            sources={data?.sources || []}
            meta={data?.meta || {
              tracked_sources: 0,
              feed_status: 'unknown',
              last_sync: '',
              queue_length: 0,
              queued_count: 0,
              published_count: 0,
              duplicate_count: 0,
              last_persisted_at: null,
            }}
            autoCategories={data?.auto_categories || []}
            categorySnapshots={data?.category_snapshots || []}
            trendHistory={data?.trend_history || []}
            signals={data?.signals || []}
            feedItems={allItems}
            onCategoryFilter={handleCategoryFilter}
          />
        </div>

        {/* Center feed */}
        <FeedColumn
          items={filteredItems}
          onSearch={handleSearch}
          onRefresh={handleRefresh}
          isRefreshing={isRefreshing}
          onTranslate={handleTranslate}
          likedIds={likedIds}
          savedIds={savedIds}
          onLike={handleLike}
          onSave={handleSave}
        />

        {/* Right rail */}
        <div className="hidden lg:block">
          <RightRail items={allItems} />
        </div>
      </div>
    </div>
  );
}
