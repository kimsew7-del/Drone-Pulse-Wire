'use client';

import useSWR from 'swr';
import { apiFetch } from '@/lib/api';
import type { CrawlJob } from '@/lib/types';

const fetcher = (path: string) => apiFetch<CrawlJob>(path);

export function useCrawlJob() {
  const { data, error, mutate } = useSWR<CrawlJob>(
    '/api/crawl/status',
    fetcher,
    {
      refreshInterval: (latestData) => {
        if (latestData?.status === 'running') return 1500;
        return 30000;
      },
    }
  );

  return {
    data,
    error,
    isLoading: !data && !error,
    isRunning: data?.status === 'running',
    mutate,
  };
}
