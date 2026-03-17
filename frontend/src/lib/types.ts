export interface NewsItem {
  id: string;
  topic: string;
  region: string;
  headline: string;
  summary: string;
  highlights: string[];
  source: string;
  source_id: string;
  impact: number;
  timestamp: string;
  url: string;
  status: string;
  duplicate_group: string | null;
  related_sources: string[];
  duplicate_count: number;
  canonical_key: string;
  merged_summary: string | null;
  related_articles: RelatedArticle[];
  editor_note: string;
  translated_headline: string;
  translated_summary: string;
  translated_to_ko: boolean;
  auto_categories: string[];
  content_type: string;
  doc_type: string;
}

export interface RelatedArticle {
  id: string;
  headline: string;
  source: string;
  timestamp: string;
  url: string;
}

export interface Source {
  id: string;
  name: string;
  type: string;
  url: string;
  query?: string;
  language?: string;
  page_size?: number;
  env_key?: string;
  must_contain_any?: string[];
  content_class?: string;
}

export interface SourceStat {
  last_checked_at: string | null;
  last_success_at: string | null;
  last_error: string | null;
  fetched_count: number;
  blocked_reason: string | null;
}

export interface Signal {
  title: string;
  copy: string;
  tag: string;
}

export interface TrendSnapshot {
  date: string;
  total: number;
  news_count: number;
  research_count: number;
  average_impact: number;
  keyword_counts: Record<string, number>;
  topic_counts: Record<string, number>;
  region_counts: Record<string, number>;
}

export interface CategorySnapshot {
  date: string;
  windows: Record<string, Category[]>;
  categories: Category[];
}

export interface Category {
  label: string;
  terms: string[];
  article_count: number;
  avg_impact: number;
  article_ids?: string[];
  momentum: string;
}

export interface ReportStats {
  total: number;
  source_count: number;
  regions: string[];
}

export interface FeedMeta {
  tracked_sources: number;
  feed_status: string;
  last_sync: string;
  queue_length: number;
  queued_count: number;
  published_count: number;
  duplicate_count: number;
  last_persisted_at: string | null;
}

export interface NewsPayload {
  news: NewsItem[];
  published: NewsItem[];
  sources: Source[];
  source_stats: Record<string, SourceStat>;
  signals: Signal[];
  trend_history: TrendSnapshot[];
  auto_categories: Category[];
  category_snapshots: CategorySnapshot[];
  reports: NewsItem[];
  report_sources: Source[];
  report_stats: ReportStats;
  meta: FeedMeta;
}

export interface CrawlJob {
  status: string;
  regions: string[];
  progress: number;
  total: number;
  current_region: string;
  current_seed: string;
  discovered: number;
  log: string[];
  started_at: string | null;
  finished_at: string | null;
}

export interface User {
  id: number;
  username: string;
}

export interface AuthState {
  user: User | null;
  token: string | null;
}
