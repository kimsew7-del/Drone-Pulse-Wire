'use client';

import React, { useState, useCallback } from 'react';
import { classNames } from '@/lib/utils';

export interface SearchBarProps {
  onSearch: (query: string) => void;
  onRefresh: () => void;
  isRefreshing: boolean;
}

export default function SearchBar({ onSearch, onRefresh, isRefreshing }: SearchBarProps) {
  const [value, setValue] = useState('');

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const v = e.target.value;
      setValue(v);
      onSearch(v);
    },
    [onSearch],
  );

  const handleClear = useCallback(() => {
    setValue('');
    onSearch('');
  }, [onSearch]);

  return (
    <div className="flex items-center gap-3">
      {/* Search input */}
      <div className="relative flex-1">
        {/* Search icon */}
        <svg
          className="absolute left-4 top-1/2 -translate-y-1/2 h-4 w-4 text-muted pointer-events-none"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>

        <input
          type="text"
          value={value}
          onChange={handleChange}
          placeholder="Search headlines, sources, regions..."
          className="w-full pl-11 pr-10 py-3 rounded-2xl bg-white border border-muted/15 text-sm text-text placeholder:text-muted/50 focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent/40 transition-all"
        />

        {value && (
          <button
            onClick={handleClear}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-muted hover:text-text transition-colors text-lg leading-none"
            aria-label="Clear search"
          >
            &times;
          </button>
        )}
      </div>

      {/* Refresh button */}
      <button
        onClick={onRefresh}
        disabled={isRefreshing}
        className={classNames(
          'flex items-center justify-center h-11 w-11 rounded-2xl border border-muted/15 bg-white transition-all hover:bg-bg hover:border-accent/30',
          isRefreshing && 'opacity-50 cursor-not-allowed',
        )}
        aria-label="Refresh feed"
      >
        <svg
          className={classNames('h-4.5 w-4.5 text-muted', isRefreshing && 'animate-spin')}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
          />
        </svg>
      </button>
    </div>
  );
}
