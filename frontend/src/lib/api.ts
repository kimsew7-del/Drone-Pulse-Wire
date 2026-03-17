import type {
  NewsPayload,
  CrawlJob,
  Source,
  User,
} from './types';

/**
 * Returns the API base URL. Uses NEXT_PUBLIC_API_URL if set,
 * otherwise defaults to empty string (same-origin proxy via Next.js rewrites).
 */
export function getApiBase(): string {
  return process.env.NEXT_PUBLIC_API_URL || '';
}

/**
 * Wrapper around fetch that adds auth headers and handles 401 responses.
 */
export async function apiFetch<T = unknown>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const base = getApiBase();
  const url = `${base}${path}`;

  const headers = new Headers(options.headers);

  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('briefwave-token');
    if (token) {
      headers.set('Authorization', `Bearer ${token}`);
    }
  }

  if (!headers.has('Content-Type') && options.body && typeof options.body === 'string') {
    headers.set('Content-Type', 'application/json');
  }

  const res = await fetch(url, { ...options, headers });

  if (res.status === 401) {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('briefwave-token');
    }
    throw new Error('Unauthorized');
  }

  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`API error ${res.status}: ${text}`);
  }

  const contentType = res.headers.get('content-type');
  if (contentType && contentType.includes('application/json')) {
    return res.json() as Promise<T>;
  }

  return res.text() as unknown as T;
}

// --- News ---

export function getNews(): Promise<NewsPayload> {
  return apiFetch<NewsPayload>('/api/news');
}

export function refreshFeed(token: string): Promise<{ status: string }> {
  return apiFetch<{ status: string }>('/api/news/refresh', {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
  });
}

export function publishArticle(id: string, token: string): Promise<{ status: string }> {
  return apiFetch<{ status: string }>(`/api/news/${id}/publish`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
  });
}

export function queueArticle(id: string, token: string): Promise<{ status: string }> {
  return apiFetch<{ status: string }>(`/api/news/${id}/queue`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
  });
}

export function updateNote(
  id: string,
  note: string,
  token: string
): Promise<{ status: string }> {
  return apiFetch<{ status: string }>(`/api/news/${id}/note`, {
    method: 'PUT',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ note }),
  });
}

export function translateArticle(id: string, token: string): Promise<{ status: string }> {
  return apiFetch<{ status: string }>(`/api/news/${id}/translate`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
  });
}

export function compareTranslations(
  text: string,
  mode: string,
  token: string
): Promise<{ translations: Record<string, string> }> {
  return apiFetch<{ translations: Record<string, string> }>('/api/translate/compare', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ text, mode }),
  });
}

// --- Sources ---

export function getSources(): Promise<Source[]> {
  return apiFetch<Source[]>('/api/sources');
}

export function createSource(
  name: string,
  url: string,
  type: string,
  token: string
): Promise<Source> {
  return apiFetch<Source>('/api/sources', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ name, url, type }),
  });
}

export function deleteSource(id: string, token: string): Promise<{ status: string }> {
  return apiFetch<{ status: string }>(`/api/sources/${id}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${token}` },
  });
}

// --- Crawl ---

export function getCrawlStatus(): Promise<CrawlJob> {
  return apiFetch<CrawlJob>('/api/crawl/status');
}

export function startCrawl(
  body: { regions?: string[]; seeds?: string[] },
  token: string
): Promise<{ status: string }> {
  return apiFetch<{ status: string }>('/api/crawl/start', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  });
}

export function resetCrawl(token: string): Promise<{ status: string }> {
  return apiFetch<{ status: string }>('/api/crawl/reset', {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
  });
}

// --- Reports ---

export function clearReports(token: string): Promise<{ status: string }> {
  return apiFetch<{ status: string }>('/api/reports/clear', {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
  });
}

// --- Auth ---

export function login(
  username: string,
  password: string
): Promise<{ access_token: string; user: User }> {
  return apiFetch<{ access_token: string; user: User }>('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });
}

export function register(
  username: string,
  password: string
): Promise<{ access_token: string; user: User }> {
  return apiFetch<{ access_token: string; user: User }>('/api/auth/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });
}
