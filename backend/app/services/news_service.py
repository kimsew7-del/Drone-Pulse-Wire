"""
Async news service layer for the FastAPI backend.

All public functions receive an AsyncSession and return dicts suitable
for JSON responses.  Heavy synchronous work (HTTP fetches, translation)
is offloaded via ``asyncio.to_thread()``.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import delete, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    CategorySnapshot as ORMCategorySnapshot,
    NewsItem as ORMNewsItem,
    Source as ORMSource,
    SourceStat as ORMSourceStat,
    TrendSnapshot as ORMTrendSnapshot,
)
from app.services.domain import (
    REPORT_SOURCE_IDS,
    NewsItem as DomainNewsItem,
    canonicalize,
    classify_content_type,
)
from app.services.analytics import (
    assign_auto_categories,
    build_category_snapshot,
    build_signals,
    capture_trend_snapshot,
    discover_categories,
    merge_news,
    prune_irrelevant_news,
    rebuild_duplicates,
)
from app.services.fetchers import collect_from_sources
from app.services.translators import (
    apply_korean_translation,
    compare_translations as _compare_translations,
)

logger = logging.getLogger(__name__)

# Module-level translation cache shared across requests
_translation_cache: dict[str, str] = {}


# =====================================================================
# Conversion helpers
# =====================================================================


def _orm_to_domain(row: ORMNewsItem) -> DomainNewsItem:
    """Convert an ORM NewsItem to a domain dataclass."""
    return DomainNewsItem(
        id=row.id,
        topic=row.topic,
        region=row.region,
        headline=row.headline,
        summary=row.summary,
        highlights=_safe_json_list(row.highlights),
        source=row.source,
        impact=row.impact,
        timestamp=row.timestamp,
        url=row.url,
        status=row.status or "queued",
        duplicate_group=row.duplicate_group,
        related_sources=_safe_json_list(row.related_sources),
        duplicate_count=row.duplicate_count or 0,
        canonical_key=row.canonical_key or "",
        merged_summary=row.merged_summary,
        related_articles=_safe_json_list(row.related_articles),
        editor_note=row.editor_note or "",
        source_id=row.source_id or "",
        translated_headline=row.translated_headline or "",
        translated_summary=row.translated_summary or "",
        translated_to_ko=bool(row.translated_to_ko),
        auto_categories=_safe_json_list(row.auto_categories),
        content_type=row.content_type or "news",
        doc_type=row.doc_type or "",
    )


def _domain_to_orm(item: DomainNewsItem) -> ORMNewsItem:
    """Convert a domain NewsItem to an ORM object (for INSERT)."""
    return ORMNewsItem(
        id=item.id,
        topic=item.topic,
        region=item.region,
        headline=item.headline,
        summary=item.summary,
        highlights=json.dumps(item.highlights, ensure_ascii=False),
        source=item.source,
        source_id=item.source_id,
        impact=item.impact,
        timestamp=item.timestamp,
        url=item.url,
        status=item.status,
        duplicate_group=item.duplicate_group,
        related_sources=json.dumps(item.related_sources, ensure_ascii=False),
        duplicate_count=item.duplicate_count,
        canonical_key=item.canonical_key,
        merged_summary=item.merged_summary,
        related_articles=json.dumps(item.related_articles, ensure_ascii=False),
        editor_note=item.editor_note,
        translated_headline=item.translated_headline,
        translated_summary=item.translated_summary,
        translated_to_ko=1 if item.translated_to_ko else 0,
        auto_categories=json.dumps(item.auto_categories, ensure_ascii=False),
        content_type=item.content_type,
        doc_type=item.doc_type,
    )


def _safe_json_list(val: Any) -> list:
    if isinstance(val, list):
        return val
    if not val:
        return []
    try:
        parsed = json.loads(val)
        return parsed if isinstance(parsed, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def _safe_json_dict(val: Any) -> dict:
    if isinstance(val, dict):
        return val
    if not val:
        return {}
    try:
        parsed = json.loads(val)
        return parsed if isinstance(parsed, dict) else {}
    except (json.JSONDecodeError, TypeError):
        return {}


# =====================================================================
# DB read helpers
# =====================================================================


async def _load_all_news(db: AsyncSession) -> list[DomainNewsItem]:
    result = await db.execute(select(ORMNewsItem))
    return [_orm_to_domain(row) for row in result.scalars().all()]


async def _load_sources_as_dicts(db: AsyncSession) -> list[dict[str, Any]]:
    result = await db.execute(select(ORMSource))
    rows = result.scalars().all()
    return [
        {
            "id": r.id,
            "name": r.name,
            "type": r.type,
            "url": r.url,
            "query": r.query,
            "language": r.language,
            "page_size": r.page_size,
            "env_key": r.env_key,
            "must_contain_any": r.must_contain_any_list,
            "content_class": r.content_class,
        }
        for r in rows
    ]


async def _load_source_stats(db: AsyncSession) -> dict[str, dict[str, Any]]:
    result = await db.execute(select(ORMSourceStat))
    stats: dict[str, dict[str, Any]] = {}
    for r in result.scalars().all():
        stats[r.source_id] = {
            "last_checked_at": r.last_checked_at,
            "last_success_at": r.last_success_at,
            "last_error": r.last_error,
            "fetched_count": r.fetched_count,
            "blocked_reason": r.blocked_reason,
        }
    return stats


async def _load_trend_history(db: AsyncSession) -> list[dict[str, Any]]:
    result = await db.execute(
        select(ORMTrendSnapshot).order_by(ORMTrendSnapshot.date.desc()).limit(14)
    )
    rows = result.scalars().all()
    return [
        {
            "date": r.date,
            "total": r.total,
            "news_count": r.news_count,
            "research_count": r.research_count,
            "average_impact": r.average_impact,
            "keyword_counts": _safe_json_dict(r.keyword_counts),
            "topic_counts": _safe_json_dict(r.topic_counts),
            "region_counts": _safe_json_dict(r.region_counts),
        }
        for r in reversed(rows)
    ]


async def _load_category_snapshots(db: AsyncSession) -> list[dict[str, Any]]:
    result = await db.execute(
        select(ORMCategorySnapshot).order_by(ORMCategorySnapshot.date.desc()).limit(14)
    )
    rows = result.scalars().all()
    return [
        {
            "date": r.date,
            "windows": _safe_json_dict(r.windows),
            "categories": _safe_json_list(r.categories),
        }
        for r in reversed(rows)
    ]


# =====================================================================
# DB write helpers (also used by crawl_manager)
# =====================================================================


async def persist_domain_items_to_db(
    db: AsyncSession,
    news: list[DomainNewsItem],
) -> None:
    """Replace all news items in the DB with the given domain items."""
    await db.execute(delete(ORMNewsItem))
    for item in news:
        db.add(_domain_to_orm(item))


async def persist_source_stats_to_db(
    db: AsyncSession,
    source_stats: dict[str, dict[str, Any]],
) -> None:
    """Upsert source stats."""
    for source_id, stats in source_stats.items():
        existing = await db.get(ORMSourceStat, source_id)
        if existing:
            existing.last_checked_at = stats.get("last_checked_at")
            existing.last_success_at = stats.get("last_success_at") or existing.last_success_at
            existing.last_error = stats.get("last_error")
            existing.fetched_count = stats.get("fetched_count", 0)
            existing.blocked_reason = stats.get("blocked_reason")
        else:
            db.add(ORMSourceStat(
                source_id=source_id,
                last_checked_at=stats.get("last_checked_at"),
                last_success_at=stats.get("last_success_at"),
                last_error=stats.get("last_error"),
                fetched_count=stats.get("fetched_count", 0),
                blocked_reason=stats.get("blocked_reason"),
            ))


async def _persist_trend_history(
    db: AsyncSession,
    trend_history: list[dict[str, Any]],
) -> None:
    """Replace trend snapshots."""
    await db.execute(delete(ORMTrendSnapshot))
    for entry in trend_history:
        db.add(ORMTrendSnapshot(
            date=entry["date"],
            total=entry.get("total"),
            news_count=entry.get("news_count"),
            research_count=entry.get("research_count"),
            average_impact=entry.get("average_impact"),
            keyword_counts=json.dumps(entry.get("keyword_counts", {}), ensure_ascii=False),
            topic_counts=json.dumps(entry.get("topic_counts", {}), ensure_ascii=False),
            region_counts=json.dumps(entry.get("region_counts", {}), ensure_ascii=False),
        ))


async def _persist_category_snapshots(
    db: AsyncSession,
    category_snapshots: list[dict[str, Any]],
) -> None:
    """Replace category snapshots."""
    await db.execute(delete(ORMCategorySnapshot))
    for snap in category_snapshots:
        db.add(ORMCategorySnapshot(
            date=snap["date"],
            windows=json.dumps(snap.get("windows", {}), ensure_ascii=False),
            categories=json.dumps(snap.get("categories", []), ensure_ascii=False),
        ))


# =====================================================================
# Public API functions
# =====================================================================


async def get_payload(db: AsyncSession) -> dict[str, Any]:
    """Build the full response payload from the database."""
    news = await _load_all_news(db)
    sources = await _load_sources_as_dicts(db)
    source_stats = await _load_source_stats(db)
    trend_history = await _load_trend_history(db)
    category_snapshots = await _load_category_snapshots(db)

    sorted_news = sorted(news, key=lambda item: item.timestamp, reverse=True)
    queued = [item for item in sorted_news if item.status == "queued"]
    published = [item for item in sorted_news if item.status == "published"]
    duplicate_hidden = [item for item in news if item.status == "duplicate_hidden"]
    visible = [item for item in news if item.status != "duplicate_hidden"]

    current_cats = discover_categories(visible, category_snapshots)
    assign_auto_categories(visible, current_cats)

    report_items = [item for item in visible if item.content_type == "report"]
    report_sources = [
        s for s in sources
        if s.get("content_class") == "report" or s.get("id") in REPORT_SOURCE_IDS
    ]

    return {
        "news": [item.to_dict() for item in queued],
        "published": [item.to_dict() for item in published],
        "sources": sources,
        "source_stats": source_stats,
        "signals": build_signals(queued, published, duplicate_hidden),
        "trend_history": trend_history[-7:],
        "auto_categories": current_cats,
        "category_snapshots": category_snapshots[-7:],
        "reports": [
            item.to_dict()
            for item in sorted(report_items, key=lambda i: i.timestamp, reverse=True)
        ],
        "report_sources": report_sources,
        "report_stats": {
            "total": len(report_items),
            "source_count": len(report_sources),
            "regions": sorted({item.region for item in report_items}),
        },
        "meta": {
            "tracked_sources": len(sources),
            "feed_status": "LIVE",
            "last_sync": datetime.now(timezone.utc).isoformat(),
            "queue_length": 0,
            "queued_count": len(queued),
            "published_count": len(published),
            "duplicate_count": len(duplicate_hidden),
            "last_persisted_at": datetime.now(timezone.utc).isoformat(),
        },
    }


async def refresh_feed(db: AsyncSession) -> dict[str, Any]:
    """Collect from all sources, merge, persist, return full payload."""
    sources = await _load_sources_as_dicts(db)
    news = await _load_all_news(db)
    trend_history = await _load_trend_history(db)
    category_snapshots = await _load_category_snapshots(db)

    source_stats: dict[str, dict[str, Any]] = await _load_source_stats(db)

    # Fetch is sync/blocking, run in thread pool
    fetched = await asyncio.to_thread(collect_from_sources, sources, source_stats)

    # merge_news operates on in-memory lists
    added = merge_news(fetched, news, trend_history, sources, lambda: None) if fetched else 0

    if added:
        # Rebuild analytics
        prune_irrelevant_news(news, sources)
        rebuild_duplicates(news)
    capture_trend_snapshot(news, trend_history, sources)
    build_category_snapshot(news, category_snapshots)

    # Persist everything
    await persist_domain_items_to_db(db, news)
    await persist_source_stats_to_db(db, source_stats)
    await _persist_trend_history(db, trend_history)
    await _persist_category_snapshots(db, category_snapshots)
    await db.commit()

    return await get_payload(db)


async def update_status(db: AsyncSession, item_id: str, status: str) -> dict[str, Any]:
    """Update the status of a news item, rebuild duplicates, persist."""
    news = await _load_all_news(db)
    target = next((item for item in news if item.id == item_id), None)
    if target:
        target.status = status
        rebuild_duplicates(news)
        await persist_domain_items_to_db(db, news)
        await db.commit()
    return await get_payload(db)


async def update_note(db: AsyncSession, item_id: str, note: str) -> dict[str, Any]:
    """Update the editor note of a news item."""
    row = await db.get(ORMNewsItem, item_id)
    if row:
        row.editor_note = note.strip()
        await db.commit()
    return await get_payload(db)


async def translate_item(db: AsyncSession, item_id: str) -> dict[str, Any]:
    """Force-translate a single news item."""
    news = await _load_all_news(db)
    target = next((item for item in news if item.id == item_id), None)
    if target:
        target.translated_headline = ""
        target.translated_summary = ""
        target.translated_to_ko = False
        # Translation is sync/blocking
        await asyncio.to_thread(
            apply_korean_translation, target, _translation_cache, True
        )
        # Update only the translated fields in DB
        row = await db.get(ORMNewsItem, item_id)
        if row:
            row.translated_headline = target.translated_headline
            row.translated_summary = target.translated_summary
            row.translated_to_ko = 1 if target.translated_to_ko else 0
            await db.commit()
    return await get_payload(db)


async def do_compare_translations(text: str, mode: str = "headline") -> dict[str, Any]:
    """Compare translations across all available engines."""
    return await asyncio.to_thread(_compare_translations, text, mode)


async def create_source(
    db: AsyncSession, name: str, url: str, source_type: str = "rss"
) -> dict[str, Any]:
    """Add a new source if it doesn't already exist."""
    normalized_name = name.strip()
    normalized_url = url.strip()
    if normalized_name and normalized_url:
        result = await db.execute(
            select(ORMSource).where(ORMSource.url == normalized_url)
        )
        existing = result.scalar_one_or_none()
        if not existing:
            db.add(ORMSource(
                id=f"src-{uuid.uuid4().hex[:8]}",
                name=normalized_name,
                type=source_type,
                url=normalized_url,
            ))
            await db.commit()
    return await get_payload(db)


async def delete_source(db: AsyncSession, source_id: str) -> dict[str, Any]:
    """Delete a source by id."""
    result = await db.execute(
        select(ORMSource).where(ORMSource.id == source_id)
    )
    row = result.scalar_one_or_none()
    if row:
        await db.delete(row)
        await db.commit()
    return await get_payload(db)
