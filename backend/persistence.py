from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.models import (
    NewsItem,
    canonicalize,
    classify_content_type,
    parse_runtime_datetime,
)


# ── JSON I/O ──────────────────────────────────────────────────


def load_json(data_dir: Path, filename: str) -> list[dict[str, Any]]:
    with (data_dir / filename).open("r", encoding="utf-8") as file:
        payload = json.load(file)
    if filename == "sources.json":
        normalized = []
        for item in payload:
            if "_comment" in item:
                continue
            normalized.append(
                {
                    "id": item.get("id", f"src-{uuid.uuid4().hex[:8]}"),
                    "name": item["name"],
                    "type": item.get("type", "rss"),
                    "url": item["url"],
                    "query": item.get("query"),
                    "language": item.get("language"),
                    "page_size": item.get("page_size"),
                    "env_key": item.get("env_key"),
                    "must_contain_any": item.get("must_contain_any", []),
                    "content_class": item.get("content_class"),
                }
            )
        return normalized
    return payload


def persist_sources(data_dir: Path, sources: list[dict[str, Any]]) -> None:
    with (data_dir / "sources.json").open("w", encoding="utf-8") as file:
        json.dump(sources, file, ensure_ascii=False, indent=2)


def merge_discovered_sources(sources: list[dict[str, Any]], data_dir: Path) -> None:
    discovered_path = data_dir / "discovered_sources.json"
    if not discovered_path.exists():
        return
    try:
        with discovered_path.open("r", encoding="utf-8") as f:
            discovered = json.load(f)
    except (json.JSONDecodeError, OSError):
        return
    known_ids = {s.get("id") for s in sources}
    known_urls = {s.get("url") for s in sources}
    for item in discovered:
        if not isinstance(item, dict) or item.get("_comment"):
            continue
        if item.get("id") in known_ids or item.get("url") in known_urls:
            continue
        sources.append({
            "id": item.get("id", f"src-discovered-{uuid.uuid4().hex[:8]}"),
            "name": item.get("name", "Discovered Source"),
            "type": item.get("type", "rss"),
            "url": item.get("url", ""),
            "query": item.get("query"),
            "language": item.get("language"),
            "page_size": item.get("page_size"),
            "env_key": item.get("env_key"),
            "must_contain_any": item.get("must_contain_any", []),
            "content_class": item.get("content_class"),
        })


def from_dict(item: dict[str, Any], sources: list[dict[str, Any]]) -> NewsItem:
    known_fields = {f.name for f in NewsItem.__dataclass_fields__.values()}
    filtered = {k: v for k, v in item.items() if k in known_fields}
    article = NewsItem(**filtered)
    article.canonical_key = article.canonical_key or canonicalize(article.headline)
    article.related_sources = article.related_sources or []
    article.related_articles = article.related_articles or []
    article.editor_note = article.editor_note or ""
    article.source_id = article.source_id or ""
    article.translated_headline = article.translated_headline or ""
    article.translated_summary = article.translated_summary or ""
    article.translated_to_ko = bool(article.translated_to_ko)
    article.auto_categories = article.auto_categories or []
    article.content_type = article.content_type or classify_content_type(article, sources)
    article.doc_type = article.doc_type or ""
    return article


# ── Runtime state ─────────────────────────────────────────────


def load_runtime_state(runtime_path: Path) -> dict[str, Any] | None:
    if not runtime_path.exists():
        return None
    with runtime_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def load_runtime_news(
    runtime_path: Path,
    data_dir: Path,
    sources: list[dict[str, Any]],
) -> tuple[list[NewsItem], datetime | None, str | None]:
    runtime = load_runtime_state(runtime_path)
    if runtime:
        last_sync = parse_runtime_datetime(runtime.get("last_sync"))
        last_persisted_at = runtime.get("saved_at")
        news = [from_dict(item, sources) for item in runtime.get("news", [])]
        return news, last_sync, last_persisted_at
    news = [from_dict(item, sources) for item in load_json(data_dir, "seed_news.json")]
    return news, None, None


def load_runtime_source_stats(runtime_path: Path) -> dict[str, dict[str, Any]]:
    runtime = load_runtime_state(runtime_path)
    if runtime:
        return runtime.get("source_stats", {})
    return {}


def load_runtime_trend_history(runtime_path: Path) -> list[dict[str, Any]]:
    runtime = load_runtime_state(runtime_path)
    if runtime:
        return runtime.get("trend_history", [])
    return []


def load_runtime_category_snapshots(runtime_path: Path) -> list[dict[str, Any]]:
    runtime = load_runtime_state(runtime_path)
    if runtime:
        return runtime.get("category_snapshots", [])
    return []


def persist_state(
    runtime_path: Path,
    news: list[NewsItem],
    source_stats: dict[str, dict[str, Any]],
    trend_history: list[dict[str, Any]],
    category_snapshots: list[dict[str, Any]],
    last_sync: datetime,
) -> str:
    payload = {
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "last_sync": last_sync.isoformat(),
        "news": [item.to_dict() for item in news],
        "source_stats": source_stats,
        "trend_history": trend_history,
        "category_snapshots": category_snapshots,
    }
    with runtime_path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)
    return payload["saved_at"]
