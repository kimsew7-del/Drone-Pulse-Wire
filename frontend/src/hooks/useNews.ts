'use client';

import useSWR from 'swr';
import { apiFetch } from '@/lib/api';
import type { NewsPayload } from '@/lib/types';

const fetcher = (path: string) => apiFetch<NewsPayload>(path);

export function useNews() {
  const { data, error, mutate } = useSWR<NewsPayload>(
    '/api/news',
    fetcher,
    { refreshInterval: 30000 }
  );

  return {
    data,
    error,
    isLoading: !data && !error,
    mutate,
  };
}
