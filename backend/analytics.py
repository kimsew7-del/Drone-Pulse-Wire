from __future__ import annotations

import math
import re
from datetime import datetime, timedelta, timezone
from typing import Any

from backend.models import (
    CATEGORY_STOP_WORDS,
    REPORT_SOURCE_IDS,
    RESEARCH_SOURCES,
    TREND_TERMS,
    NewsItem,
    canonicalize,
    parse_iso_datetime,
    strip_korean_particles,
)


# ── Tokenization ──────────────────────────────────────────────


def tokenize_text(text: str) -> list[str]:
    lowered = text.lower()
    lowered = re.sub(r"[^\w\s가-힣]", " ", lowered)
    raw_tokens = lowered.split()
    tokens = []
    for tok in raw_tokens:
        tok = strip_korean_particles(tok)
        if len(tok) > 1 and tok not in CATEGORY_STOP_WORDS:
            tokens.append(tok)
    bigrams = []
    for i in range(len(tokens) - 1):
        bigram = f"{tokens[i]} {tokens[i+1]}"
        bigrams.append(bigram)
    return tokens + bigrams


def build_corpus_vocabulary(
    items: list[NewsItem], window_hours: float | None = None
) -> list[tuple[str, float]]:
    now = datetime.now(timezone.utc)
    filtered = items
    if window_hours is not None:
        cutoff = now - timedelta(hours=window_hours)
        filtered = [
            item for item in items
            if parse_iso_datetime(item.timestamp)
            and parse_iso_datetime(item.timestamp) >= cutoff
        ]
    if not filtered:
        return []

    n_docs = len(filtered)
    df: dict[str, int] = {}
    tf: dict[str, int] = {}

    for item in filtered:
        text = f"{item.headline} {item.summary}"
        tokens = tokenize_text(text)
        unique_tokens = set(tokens)
        for tok in unique_tokens:
            df[tok] = df.get(tok, 0) + 1
        for tok in tokens:
            tf[tok] = tf.get(tok, 0) + 1

    scores: dict[str, float] = {}
    for term in df:
        if df[term] < 2:
            continue
        idf = math.log(n_docs / df[term]) if df[term] < n_docs else 0.1
        scores[term] = tf[term] * idf

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return ranked[:40]


# ── Category discovery ────────────────────────────────────────


def discover_categories(
    items: list[NewsItem],
    category_snapshots: list[dict[str, Any]],
    max_categories: int = 8,
) -> list[dict[str, Any]]:
    if len(items) < 3:
        return []

    top_terms = build_corpus_vocabulary(items)
    if not top_terms:
        return []

    term_labels = [t[0] for t in top_terms]
    term_scores = {t[0]: t[1] for t in top_terms}

    term_articles: dict[str, set[str]] = {term: set() for term in term_labels}
    for item in items:
        text = f"{item.headline} {item.summary}".lower()
        for term in term_labels:
            if term in text:
                term_articles[term].add(item.id)

    used: set[str] = set()
    groups: list[list[str]] = []
    for term in term_labels:
        if term in used:
            continue
        group = [term]
        used.add(term)
        articles_a = term_articles[term]
        if not articles_a:
            continue
        for other in term_labels:
            if other in used:
                continue
            articles_b = term_articles[other]
            if not articles_b:
                continue
            overlap = len(articles_a & articles_b)
            min_size = min(len(articles_a), len(articles_b))
            if min_size > 0 and overlap / min_size >= 0.3:
                group.append(other)
                used.add(other)
        groups.append(group)

    categories = []
    for group in groups[:max_categories]:
        label = max(group, key=lambda t: term_scores.get(t, 0))
        article_ids: set[str] = set()
        for term in group:
            article_ids |= term_articles.get(term, set())
        matched_items = [item for item in items if item.id in article_ids]
        avg_impact = (
            round(sum(item.impact for item in matched_items) / len(matched_items))
            if matched_items else 0
        )

        for item in matched_items:
            if label not in item.auto_categories:
                item.auto_categories.append(label)

        categories.append({
            "label": label,
            "terms": group[:5],
            "article_count": len(article_ids),
            "avg_impact": avg_impact,
            "article_ids": sorted(article_ids)[:20],
            "momentum": "stable",
        })

    prev_snapshot = category_snapshots[-1] if category_snapshots else None
    if prev_snapshot:
        prev_labels = {
            cat["label"]: cat["article_count"]
            for cat in prev_snapshot.get("categories", [])
        }
        for cat in categories:
            prev_count = prev_labels.get(cat["label"], 0)
            if cat["article_count"] > prev_count + 1:
                cat["momentum"] = "rising"
            elif cat["article_count"] < prev_count - 1:
                cat["momentum"] = "falling"
            else:
                cat["momentum"] = "stable"

    return categories


def build_category_snapshot(
    news: list[NewsItem],
    category_snapshots: list[dict[str, Any]],
) -> None:
    visible = [item for item in news if item.status != "duplicate_hidden"]
    snapshot_date = datetime.now(timezone.utc).date().isoformat()

    windows = {"24h": 24, "3d": 72, "7d": 168}
    window_categories: dict[str, list[dict[str, Any]]] = {}
    now = datetime.now(timezone.utc)

    for window_key, hours in windows.items():
        cutoff = now - timedelta(hours=hours)
        windowed = [
            item for item in visible
            if parse_iso_datetime(item.timestamp)
            and parse_iso_datetime(item.timestamp) >= cutoff
        ]
        if len(windowed) >= 3:
            cats = discover_categories(windowed, category_snapshots)
            window_categories[window_key] = [
                {k: v for k, v in cat.items() if k != "article_ids"}
                for cat in cats
            ]
        else:
            window_categories[window_key] = []

    snapshot = {
        "date": snapshot_date,
        "windows": window_categories,
        "categories": window_categories.get("7d", []),
    }

    existing = next(
        (s for s in category_snapshots if s.get("date") == snapshot_date), None
    )
    if existing:
        existing.update(snapshot)
    else:
        category_snapshots.append(snapshot)
    category_snapshots[:] = sorted(
        category_snapshots, key=lambda s: s.get("date", "")
    )[-14:]


# ── Trend snapshots ───────────────────────────────────────────


def classify_content_type_for_trend(item: NewsItem, sources: list[dict[str, Any]]) -> str:
    if item.source_id in REPORT_SOURCE_IDS:
        return "report"
    source_cfg = next((s for s in sources if s.get("id") == item.source_id), None)
    if source_cfg and source_cfg.get("content_class") == "report":
        return "report"
    if item.source in RESEARCH_SOURCES:
        return "research"
    return "news"


def capture_trend_snapshot(
    news: list[NewsItem],
    trend_history: list[dict[str, Any]],
    sources: list[dict[str, Any]],
) -> None:
    visible_items = sorted(news, key=lambda item: item.timestamp, reverse=True)
    visible_items = [item for item in visible_items if item.status != "duplicate_hidden"]
    snapshot_date = datetime.now(timezone.utc).date().isoformat()
    keyword_counts = {term: 0 for term in TREND_TERMS}
    topic_counts: dict[str, int] = {}
    region_counts: dict[str, int] = {}
    research_count = 0

    for item in visible_items:
        text = f"{item.headline} {item.summary} {' '.join(item.highlights)}".lower()
        for term in TREND_TERMS:
            if term in text:
                keyword_counts[term] += 1
        topic_counts[item.topic] = topic_counts.get(item.topic, 0) + 1
        region_counts[item.region] = region_counts.get(item.region, 0) + 1
        if classify_content_type_for_trend(item, sources) == "research":
            research_count += 1

    snapshot = {
        "date": snapshot_date,
        "total": len(visible_items),
        "news_count": len(visible_items) - research_count,
        "research_count": research_count,
        "average_impact": round(sum(item.impact for item in visible_items) / len(visible_items))
        if visible_items
        else 0,
        "keyword_counts": keyword_counts,
        "topic_counts": topic_counts,
        "region_counts": region_counts,
    }

    existing = next((entry for entry in trend_history if entry.get("date") == snapshot_date), None)
    if existing:
        existing.update(snapshot)
    else:
        trend_history.append(snapshot)
    trend_history[:] = sorted(trend_history, key=lambda entry: entry.get("date", ""))[-14:]


# ── Signals ───────────────────────────────────────────────────


def build_signals(
    queued: list[NewsItem],
    published: list[NewsItem],
    duplicate_hidden: list[NewsItem],
) -> list[dict[str, str]]:
    drone_count = sum("Drone" in item.topic for item in queued)
    ai_count = sum("AI" in item.topic for item in queued)
    report_count = sum(item.content_type == "report" for item in queued)
    research_count = sum(item.content_type == "research" for item in queued)
    region_counts: dict[str, int] = {}
    for item in queued:
        region_counts[item.region] = region_counts.get(item.region, 0) + 1
    top_region = max(region_counts, key=region_counts.get, default="Global")

    return [
        {
            "title": "실시간 피드 볼륨",
            "copy": f"라이브 피드 {len(queued) + len(published)}건이 누적되어 있으며 최신 수집분이 먼저 노출됩니다.",
            "tag": "Feed Volume",
        },
        {
            "title": "중복 필터링",
            "copy": f"유사 기사 {len(duplicate_hidden)}건을 대표 기사 뒤로 숨겨 중복 노출을 줄였습니다.",
            "tag": "Dedup Layer",
        },
        {
            "title": "기관 리포트 · 연구",
            "copy": f"기관 리포트 {report_count}건, 학술 연구 {research_count}건이 수집되어 있습니다.",
            "tag": "Reports",
        },
        {
            "title": "핵심 주제 분포",
            "copy": f"드론 {drone_count}건, AI {ai_count}건이며 {top_region} 비중이 가장 큽니다.",
            "tag": "Topic Mix",
        },
    ]


# ── Duplicate handling ────────────────────────────────────────


def is_duplicate(left: NewsItem, right: NewsItem) -> bool:
    if left.url == right.url:
        return True
    left_tokens = set(left.canonical_key.split())
    right_tokens = set(right.canonical_key.split())
    if len(left_tokens) >= 3 and left.canonical_key == right.canonical_key:
        return True
    if not left_tokens or not right_tokens:
        return False

    overlap = len(left_tokens & right_tokens)
    min_len = min(len(left_tokens), len(right_tokens))
    if min_len < 3:
        return False
    threshold = max(3, min_len - 1)
    return overlap >= threshold


def choose_primary(group: list[NewsItem]) -> NewsItem:
    return sorted(
        group,
        key=lambda item: (
            item.status != "published",
            -item.impact,
            item.timestamp,
        ),
    )[0]


def build_merged_summary(primary: NewsItem, siblings: list[NewsItem]) -> str:
    source_count = len({primary.source, *[item.source for item in siblings]})
    region_set = sorted({primary.region, *[item.region for item in siblings]})
    highlights: list[str] = []
    for item in [primary, *siblings]:
        for point in item.highlights:
            if point not in highlights:
                highlights.append(point)
    focus = ", ".join(highlights[:3]) if highlights else "핵심 이슈"
    return (
        f"{source_count}개 출처에서 같은 이슈를 다뤘습니다. "
        f"주요 포인트는 {focus}이며, 관측 지역은 {', '.join(region_set)}입니다."
    )


def rebuild_duplicates(news: list[NewsItem]) -> None:
    sorted_news = sorted(news, key=lambda item: item.timestamp, reverse=True)
    groups: list[list[NewsItem]] = []

    for item in sorted_news:
        item.duplicate_group = None
        item.related_sources = []
        item.related_articles = []
        item.duplicate_count = 0
        item.merged_summary = None
        if item.status == "duplicate_hidden":
            item.status = "queued"

        matched_group = None
        for group in groups:
            if is_duplicate(item, group[0]):
                matched_group = group
                break

        if matched_group:
            matched_group.append(item)
        else:
            groups.append([item])

    for index, group in enumerate(groups, start=1):
        if len(group) == 1:
            continue

        primary = choose_primary(group)
        group_id = f"dup-{index:03d}"
        siblings = [item for item in group if item.id != primary.id]
        primary.duplicate_group = group_id
        primary.duplicate_count = len(siblings)
        primary.related_sources = sorted({item.source for item in siblings})
        primary.related_articles = [
            {
                "id": item.id,
                "headline": item.headline,
                "source": item.source,
                "timestamp": item.timestamp,
                "url": item.url,
            }
            for item in sorted(siblings, key=lambda candidate: candidate.timestamp, reverse=True)
        ]
        primary.merged_summary = build_merged_summary(primary, siblings)

        for item in siblings:
            if item.status != "published":
                item.status = "duplicate_hidden"
            item.duplicate_group = group_id


# ── Merge & prune ─────────────────────────────────────────────


def merge_news(
    new_items: list[NewsItem],
    news: list[NewsItem],
    trend_history: list[dict[str, Any]],
    sources: list[dict[str, Any]],
    persist_fn: Any,
) -> int:
    known_urls = {item.url for item in news}
    added = 0

    for item in new_items:
        if item.url in known_urls:
            continue
        news.append(item)
        known_urls.add(item.url)
        added += 1

    if added:
        rebuild_duplicates(news)
        sorted_news = sorted(news, key=lambda item: item.timestamp, reverse=True)
        news_items = [i for i in sorted_news if i.content_type != "report"]
        report_items = [i for i in sorted_news if i.content_type == "report"]
        news[:] = news_items[:150] + report_items
        capture_trend_snapshot(news, trend_history, sources)
        persist_fn()
    return added


def prune_irrelevant_news(
    news: list[NewsItem],
    sources: list[dict[str, Any]],
) -> None:
    from backend.fetchers import passes_focus_relevance, source_item_is_relevant

    source_rules = {source["id"]: source for source in sources}
    filtered = []
    for item in news:
        if "example.com" in item.url:
            continue
        if item.content_type in ("report", "research"):
            filtered.append(item)
            continue
        if item.source_id.startswith("topic-"):
            filtered.append(item)
            continue
        text = f"{item.headline} {item.summary}".lower()
        if not passes_focus_relevance(text):
            continue
        source = source_rules.get(item.source_id)
        if source and not source_item_is_relevant(source, item.headline, item.summary):
            continue
        filtered.append(item)
    news[:] = filtered
