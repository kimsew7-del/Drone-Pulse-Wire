from pydantic import BaseModel, Field
from typing import Any


# ── Auth ──────────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    username: str
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ── Sources ───────────────────────────────────────────────────────────────

class SourceCreate(BaseModel):
    name: str
    url: str
    type: str = "rss"


class SourceResponse(BaseModel):
    id: str
    name: str
    type: str
    url: str
    query: str | None = None
    language: str | None = None
    page_size: int | None = None
    env_key: str | None = None
    must_contain_any: str | None = "[]"
    content_class: str | None = None

    model_config = {"from_attributes": True}


class SourceStatResponse(BaseModel):
    source_id: str
    last_checked_at: str | None = None
    last_success_at: str | None = None
    last_error: str | None = None
    fetched_count: int = 0
    blocked_reason: str | None = None

    model_config = {"from_attributes": True}


# ── News ──────────────────────────────────────────────────────────────────

class NewsItemResponse(BaseModel):
    id: str
    topic: str
    region: str
    headline: str
    summary: str
    highlights: str = "[]"
    source: str
    source_id: str | None = None
    impact: int
    timestamp: str
    url: str
    status: str = "queued"
    duplicate_group: str | None = None
    related_sources: str = "[]"
    duplicate_count: int = 0
    canonical_key: str | None = None
    merged_summary: str | None = None
    related_articles: str = "[]"
    editor_note: str = ""
    translated_headline: str = ""
    translated_summary: str = ""
    translated_to_ko: int = 0
    auto_categories: str = "[]"
    content_type: str = "news"
    doc_type: str = ""

    model_config = {"from_attributes": True}


class NoteUpdateRequest(BaseModel):
    note: str


class TranslateCompareRequest(BaseModel):
    text: str
    mode: str = "headline"


# ── Signals ───────────────────────────────────────────────────────────────

class SignalResponse(BaseModel):
    type: str
    label: str
    description: str
    severity: str = "info"
    data: dict[str, Any] = Field(default_factory=dict)


# ── Trends ────────────────────────────────────────────────────────────────

class TrendSnapshotResponse(BaseModel):
    date: str
    total: int | None = None
    news_count: int | None = None
    research_count: int | None = None
    average_impact: int | None = None
    keyword_counts: str = "{}"
    topic_counts: str = "{}"
    region_counts: str = "{}"

    model_config = {"from_attributes": True}


# ── Categories ────────────────────────────────────────────────────────────

class CategoryResponse(BaseModel):
    name: str
    count: int
    keywords: list[str] = Field(default_factory=list)
    avg_impact: float = 0.0


class CategorySnapshotResponse(BaseModel):
    date: str
    windows: str = "{}"
    categories: str = "[]"

    model_config = {"from_attributes": True}


# ── Reports ───────────────────────────────────────────────────────────────

class ReportStatsResponse(BaseModel):
    total_reports: int = 0
    total_sources: int = 0
    average_impact: float = 0.0
    top_topics: list[dict[str, Any]] = Field(default_factory=list)


# ── Feed Meta ─────────────────────────────────────────────────────────────

class FeedMeta(BaseModel):
    tracked_sources: int = 0
    feed_status: str = "idle"
    last_sync: str | None = None
    queue_length: int = 0
    queued_count: int = 0
    published_count: int = 0
    duplicate_count: int = 0
    last_persisted_at: str | None = None


# ── Crawl ─────────────────────────────────────────────────────────────────

class CrawlStartRequest(BaseModel):
    regions: list[str] | None = None
    topic: str | None = None
    mode: str | None = None


class CrawlJobResponse(BaseModel):
    job_id: str
    status: str = "started"
    message: str = ""


# ── Full Payload ──────────────────────────────────────────────────────────

class NewsPayloadResponse(BaseModel):
    news: list[NewsItemResponse] = Field(default_factory=list)
    published: list[NewsItemResponse] = Field(default_factory=list)
    sources: list[SourceResponse] = Field(default_factory=list)
    source_stats: list[SourceStatResponse] = Field(default_factory=list)
    signals: list[SignalResponse] = Field(default_factory=list)
    trend_history: list[TrendSnapshotResponse] = Field(default_factory=list)
    auto_categories: list[CategoryResponse] = Field(default_factory=list)
    category_snapshots: list[CategorySnapshotResponse] = Field(default_factory=list)
    reports: list[dict[str, Any]] = Field(default_factory=list)
    report_sources: list[dict[str, Any]] = Field(default_factory=list)
    report_stats: ReportStatsResponse = Field(default_factory=ReportStatsResponse)
    meta: FeedMeta = Field(default_factory=FeedMeta)
