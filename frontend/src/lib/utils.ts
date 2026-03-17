/**
 * Format an ISO date string as a relative time (e.g. "3m ago", "2h ago", "1d ago").
 * Returns '--' for null/invalid input.
 */
export function formatRelative(isoString: string | null): string {
  if (!isoString) return '--';

  const date = new Date(isoString);
  if (isNaN(date.getTime())) return '--';

  const now = Date.now();
  const diffMs = now - date.getTime();
  const diffSec = Math.floor(diffMs / 1000);

  if (diffSec < 60) return `${diffSec}s ago`;

  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `${diffMin}m ago`;

  const diffHour = Math.floor(diffMin / 60);
  if (diffHour < 24) return `${diffHour}h ago`;

  const diffDay = Math.floor(diffHour / 24);
  if (diffDay < 30) return `${diffDay}d ago`;

  const diffMonth = Math.floor(diffDay / 30);
  if (diffMonth < 12) return `${diffMonth}mo ago`;

  const diffYear = Math.floor(diffMonth / 12);
  return `${diffYear}y ago`;
}

/**
 * Format an ISO date string as a readable date (e.g. "2024-03-15 14:30").
 * Returns '--' for null/invalid input.
 */
export function formatDate(isoString: string | null): string {
  if (!isoString) return '--';

  const date = new Date(isoString);
  if (isNaN(date.getTime())) return '--';

  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  const hours = String(date.getHours()).padStart(2, '0');
  const minutes = String(date.getMinutes()).padStart(2, '0');

  return `${year}-${month}-${day} ${hours}:${minutes}`;
}

/**
 * Check if a string contains Korean characters.
 */
export function isKorean(text: string): boolean {
  return /[\uAC00-\uD7AF\u1100-\u11FF\u3130-\u318F\uA960-\uA97F\uD7B0-\uD7FF]/.test(text);
}

/**
 * Format a numeric delta with a sign prefix and percentage symbol.
 * e.g. formatDelta(12.5) -> "+12.5%", formatDelta(-3) -> "-3%"
 */
export function formatDelta(value: number): string {
  if (value === 0) return '0%';
  const sign = value > 0 ? '+' : '';
  return `${sign}${value}%`;
}

/**
 * Concatenate class names, filtering out falsy values.
 * Usage: classNames('base', isActive && 'active', className)
 */
export function classNames(
  ...classes: (string | boolean | undefined | null)[]
): string {
  return classes.filter(Boolean).join(' ');
}
