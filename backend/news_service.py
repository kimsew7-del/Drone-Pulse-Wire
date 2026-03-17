from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.models import REPORT_SOURCE_IDS, NewsItem
from backend.fetchers import collect_from_sources
from backend.translators import apply_korean_translation, compare_translations
from backend.analytics import (
    assign_auto_categories,
    build_category_snapshot,
    build_signals,
    capture_trend_snapshot,
    discover_categories,
    merge_news,
    prune_irrelevant_news,
    rebuild_duplicates,
)
from backend.persistence import (
    from_dict,
    load_json,
    load_runtime_category_snapshots,
    load_runtime_news,
    load_runtime_source_stats,
    load_runtime_trend_history,
    merge_discovered_sources,
    persist_sources,
    persist_state,
)
from backend.crawl_manager import CrawlManager


class NewsService:
    def __init__(self, base_dir: Path, data_dir: Path | None = None):
        self.base_dir = base_dir
        self.data_dir = data_dir or (self.base_dir / "data")
        self.runtime_path = self.data_dir / "runtime_state.json"
        self.sources = load_json(self.data_dir, "sources.json")
        merge_discovered_sources(self.sources, self.data_dir)
        self.mock_queue = [from_dict(item, self.sources) for item in load_json(self.data_dir, "mock_feed.json")]
        self.lock = threading.RLock()
        self.last_sync = datetime.now(timezone.utc)
        self.feed_status = "READY"
        self.last_persisted_at: str | None = None
        self.source_stats = load_runtime_source_stats(self.runtime_path)
        self.trend_history = load_runtime_trend_history(self.runtime_path)
        news, last_sync, last_persisted_at = load_runtime_news(self.runtime_path, self.data_dir, self.sources)
        self.news: list[NewsItem] = news
        if last_sync:
            self.last_sync = last_sync
        if last_persisted_at:
            self.last_persisted_at = last_persisted_at
        self.translation_cache: dict[str, str] = {}
        self.category_snapshots: list[dict[str, Any]] = load_runtime_category_snapshots(self.runtime_path)
        self.crawl = CrawlManager(self)

        prune_irrelevant_news(self.news, self.sources)
        rebuild_duplicates(self.news)
        capture_trend_snapshot(self.news, self.trend_history, self.sources)
        build_category_snapshot(self.news, self.category_snapshots)
        self._do_persist()

    def _do_persist(self) -> None:
        self.last_persisted_at = persist_state(
            self.runtime_path,
            self.news,
            self.source_stats,
            self.trend_history,
            self.category_snapshots,
            self.last_sync,
        )

    def _sorted_news(self) -> list[NewsItem]:
        return sorted(self.news, key=lambda item: item.timestamp, reverse=True)

    # ── Public API ────────────────────────────────────────────

    def get_payload(self) -> dict[str, Any]:
        with self.lock:
            sorted_news = self._sorted_news()
            queued = [item for item in sorted_news if item.status == "queued"]
            published = [item for item in sorted_news if item.status == "published"]
            duplicate_hidden = [item for item in self.news if item.status == "duplicate_hidden"]
            visible = [item for item in self.news if item.status != "duplicate_hidden"]
            current_cats = discover_categories(visible, self.category_snapshots)
            assign_auto_categories(visible, current_cats)
            report_items = [item for item in visible if item.content_type == "report"]
            report_sources = [s for s in self.sources if s.get("content_class") == "report" or s.get("id") in REPORT_SOURCE_IDS]
            return {
                "news": [item.to_dict() for item in queued],
                "published": [item.to_dict() for item in published],
                "sources": self.sources,
                "source_stats": self.source_stats,
                "signals": build_signals(queued, published, duplicate_hidden),
                "trend_history": self.trend_history[-7:],
                "auto_categories": current_cats,
                "category_snapshots": self.category_snapshots[-7:],
                "reports": [item.to_dict() for item in sorted(report_items, key=lambda i: i.timestamp, reverse=True)],
                "report_sources": report_sources,
                "report_stats": {
                    "total": len(report_items),
                    "source_count": len(report_sources),
                    "regions": sorted({item.region for item in report_items}),
                },
                "meta": {
                    "tracked_sources": len(self.sources),
                    "feed_status": self.feed_status,
                    "last_sync": self.last_sync.isoformat(),
                    "queue_length": len(self.mock_queue),
                    "queued_count": len(queued),
                    "published_count": len(published),
                    "duplicate_count": len(duplicate_hidden),
                    "last_persisted_at": self.last_persisted_at,
                },
            }

    def refresh(self) -> dict[str, Any]:
        with self.lock:
            self.feed_status = "SYNCING"
            fetched = collect_from_sources(self.sources, self.source_stats)
            added = merge_news(fetched, self.news, self.trend_history, self.sources, self._do_persist) if fetched else 0

            if added == 0 and self.mock_queue:
                self.news.append(self.mock_queue.pop(0))
                rebuild_duplicates(self.news)
                capture_trend_snapshot(self.news, self.trend_history, self.sources)
                self._do_persist()

            self.last_sync = datetime.now(timezone.utc)
            self.feed_status = "LIVE"
            capture_trend_snapshot(self.news, self.trend_history, self.sources)
            build_category_snapshot(self.news, self.category_snapshots)
            self._do_persist()
            return self.get_payload()

    def update_status(self, item_id: str, status: str) -> dict[str, Any]:
        with self.lock:
            target = next((item for item in self.news if item.id == item_id), None)
            if target:
                target.status = status
                rebuild_duplicates(self.news)
                self._do_persist()
            return self.get_payload()

    def update_note(self, item_id: str, note: str) -> dict[str, Any]:
        with self.lock:
            target = next((item for item in self.news if item.id == item_id), None)
            if target:
                target.editor_note = note.strip()
                self._do_persist()
            return self.get_payload()

    def translate_item(self, item_id: str) -> dict[str, Any]:
        with self.lock:
            target = next((item for item in self.news if item.id == item_id), None)
            if target:
                target.translated_headline = ""
                target.translated_summary = ""
                target.translated_to_ko = False
                apply_korean_translation(target, cache=self.translation_cache, force=True)
                self._do_persist()
            return self.get_payload()

    def compare_translations(self, text: str, mode: str = "headline") -> dict[str, Any]:
        return compare_translations(text, mode)

    def create_source(self, name: str, url: str, source_type: str = "rss") -> dict[str, Any]:
        with self.lock:
            normalized_name = name.strip()
            normalized_url = url.strip()
            if normalized_name and normalized_url:
                exists = any(source["url"] == normalized_url for source in self.sources)
                if not exists:
                    self.sources.append(
                        {
                            "id": f"src-{uuid.uuid4().hex[:8]}",
                            "name": normalized_name,
                            "type": source_type,
                            "url": normalized_url,
                        }
                    )
                    persist_sources(self.data_dir, self.sources)
            return self.get_payload()

    def delete_source(self, source_id: str) -> dict[str, Any]:
        with self.lock:
            self.sources = [source for source in self.sources if source.get("id", source.get("url")) != source_id]
            persist_sources(self.data_dir, self.sources)
            return self.get_payload()

    # ── Crawl delegation ──────────────────────────────────────

    def get_crawl_status(self) -> dict[str, Any]:
        return self.crawl.get_status()

    def reset_crawl(self) -> dict[str, Any]:
        return self.crawl.reset()

    def clear_reports(self) -> dict[str, Any]:
        return self.crawl.clear_reports()

    def start_crawl(self, regions: list[str] | None = None) -> dict[str, Any]:
        return self.crawl.start_crawl(regions)

    def start_topic_crawl(self, topic: str) -> dict[str, Any]:
        return self.crawl.start_topic_crawl(topic)

    def start_stats_crawl(self, topic: str) -> dict[str, Any]:
        return self.crawl.start_stats_crawl(topic)
