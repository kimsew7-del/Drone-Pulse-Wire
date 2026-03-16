from __future__ import annotations

import json
import os
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from backend.models import (
    DRONE_RELEVANCE_TERMS,
    PHYSICAL_AI_RELEVANCE_TERMS,
    RESEARCH_RELEVANCE_TERMS,
    NewsItem,
    extract_xml_text,
    normalize_article,
    parse_crossref_date,
    parse_date,
    parse_iso_datetime,
    parse_kci_date,
    strip_html,
)


# ── Helpers ───────────────────────────────────────────────────


def fetch_json(base_url: str, params: dict[str, str]) -> dict[str, Any]:
    request = Request(
        f"{base_url}?{urlencode(params)}",
        headers={
            "User-Agent": "DronePulseWire/0.1 (+https://localhost)",
            "Accept": "application/json",
        },
    )
    with urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def source_missing_env_key(source: dict[str, Any]) -> bool:
    env_key = source.get("env_key")
    return bool(env_key and not os.environ.get(env_key, "").strip())


def source_item_is_relevant(source: dict[str, Any], headline: str, summary: str) -> bool:
    must_contain_any = source.get("must_contain_any") or []
    text = f"{headline} {summary}".lower()
    if must_contain_any and not any(keyword.lower() in text for keyword in must_contain_any):
        return False
    if source.get("type") in {"crossref", "europepmc"}:
        return passes_research_relevance(text)
    if must_contain_any:
        return True
    return passes_focus_relevance(text)


def passes_research_relevance(text: str) -> bool:
    matches = sum(term in text for term in RESEARCH_RELEVANCE_TERMS)
    return matches >= 2


def passes_focus_relevance(text: str) -> bool:
    has_drone_signal = any(term in text for term in DRONE_RELEVANCE_TERMS)
    has_physical_ai_signal = any(term in text for term in PHYSICAL_AI_RELEVANCE_TERMS)
    return has_drone_signal or has_physical_ai_signal


def record_source_stat(
    source_stats: dict[str, dict[str, Any]],
    source: dict[str, Any],
    fetched_count: int,
    error: str | None,
    blocked_reason: str | None = None,
) -> None:
    source_id = source["id"]
    current = source_stats.get(source_id, {})
    source_stats[source_id] = {
        "last_checked_at": datetime.now(timezone.utc).isoformat(),
        "last_success_at": datetime.now(timezone.utc).isoformat() if error is None else current.get("last_success_at"),
        "last_error": error,
        "fetched_count": fetched_count,
        "blocked_reason": blocked_reason,
    }


# ── Per-source fetchers ──────────────────────────────────────


def fetch_rss_source(source: dict[str, Any], sources: list[dict[str, Any]]) -> list[NewsItem]:
    request = Request(
        source["url"],
        headers={
            "User-Agent": "DronePulseWire/0.1 (+https://localhost)",
            "Accept": "application/rss+xml, application/xml, text/xml",
        },
    )
    with urlopen(request, timeout=10) as response:
        payload = response.read()

    root = ET.fromstring(payload)
    items = []
    is_google_news = "news.google.com" in source["url"]
    limit = source.get("page_size") or (15 if is_google_news else 5)

    for node in root.findall(".//item")[:limit]:
        title = (node.findtext("title") or "").strip()
        link = (node.findtext("link") or source["url"]).strip()
        description = strip_html(node.findtext("description") or "")

        source_name = source["name"]
        if is_google_news and " - " in title:
            title, source_name = title.rsplit(" - ", 1)
            title = title.strip()
            source_name = source_name.strip()
            description = ""

        if not source_item_is_relevant(source, title, description):
            continue
        pub_date = parse_date(node.findtext("pubDate"))
        items.append(
            normalize_article(
                headline=title,
                summary=description,
                source_name=source_name,
                source_id=source["id"],
                url=link,
                sources=sources,
                published_at=pub_date,
            )
        )

    return items


def fetch_newsapi_source(source: dict[str, Any], sources: list[dict[str, Any]]) -> list[NewsItem]:
    api_key = os.environ.get(source.get("env_key") or "NEWSAPI_KEY", "")
    if not api_key:
        return []

    params = {
        "q": source.get("query") or '"drone" OR UAV OR "artificial intelligence" OR robotics',
        "language": source.get("language") or "en",
        "sortBy": "publishedAt",
        "pageSize": str(source.get("page_size") or 10),
        "apiKey": api_key,
    }
    payload = fetch_json("https://newsapi.org/v2/everything", params)
    items = []
    for article in payload.get("articles", []):
        title = article.get("title", "")
        summary = article.get("description", "") or article.get("content", "")
        if not source_item_is_relevant(source, title, summary):
            continue
        items.append(
            normalize_article(
                headline=title,
                summary=summary,
                source_name=article.get("source", {}).get("name", source["name"]),
                source_id=source["id"],
                url=article.get("url", source["url"]),
                sources=sources,
                published_at=parse_iso_datetime(article.get("publishedAt")),
            )
        )
    return items


def fetch_gnews_source(source: dict[str, Any], sources: list[dict[str, Any]]) -> list[NewsItem]:
    api_key = os.environ.get(source.get("env_key") or "GNEWS_API_KEY", "")
    if not api_key:
        return []

    params = {
        "q": source.get("query") or '"drone" OR UAV OR "artificial intelligence" OR robotics',
        "lang": source.get("language") or "en",
        "max": str(source.get("page_size") or 10),
        "apikey": api_key,
    }
    payload = fetch_json("https://gnews.io/api/v4/search", params)
    items = []
    for article in payload.get("articles", []):
        title = article.get("title", "")
        summary = article.get("description", "") or article.get("content", "")
        if not source_item_is_relevant(source, title, summary):
            continue
        items.append(
            normalize_article(
                headline=title,
                summary=summary,
                source_name=article.get("source", {}).get("name", source["name"]),
                source_id=source["id"],
                url=article.get("url", source["url"]),
                sources=sources,
                published_at=parse_iso_datetime(article.get("publishedAt")),
            )
        )
    return items


def fetch_crossref_source(source: dict[str, Any], sources: list[dict[str, Any]]) -> list[NewsItem]:
    params = {
        "rows": str(source.get("page_size") or 6),
        "query.title": source.get("query") or '"drone" "artificial intelligence"',
        "select": "DOI,title,published,container-title,URL,abstract",
    }
    mailto = os.environ.get("CROSSREF_MAILTO", "")
    if mailto:
        params["mailto"] = mailto

    payload = fetch_json("https://api.crossref.org/works", params)
    items = []
    for article in payload.get("message", {}).get("items", []):
        title = " ".join(article.get("title", [])[:1])
        summary = strip_html(article.get("abstract", "") or "")
        if not source_item_is_relevant(source, title, summary):
            continue
        items.append(
            normalize_article(
                headline=title,
                summary=summary,
                source_name=" / ".join(article.get("container-title", [])[:1]) or source["name"],
                source_id=source["id"],
                url=article.get("URL", source["url"]),
                sources=sources,
                published_at=parse_crossref_date(article.get("published")),
            )
        )
    return items


def fetch_europepmc_source(source: dict[str, Any], sources: list[dict[str, Any]]) -> list[NewsItem]:
    params = {
        "query": f'{source.get("query") or "\"drone\" OR \"autonomous flight\" OR \"artificial intelligence\""} sort_date:y',
        "pageSize": str(source.get("page_size") or 6),
        "format": "json",
        "resultType": "core",
    }
    payload = fetch_json("https://www.ebi.ac.uk/europepmc/webservices/rest/search", params)
    items = []
    for article in payload.get("resultList", {}).get("result", []):
        title = article.get("title", "")
        summary = article.get("abstractText", "")
        if not source_item_is_relevant(source, title, summary):
            continue
        items.append(
            normalize_article(
                headline=title,
                summary=summary,
                source_name=article.get("journalTitle", "") or source["name"],
                source_id=source["id"],
                url=f'https://doi.org/{article.get("doi")}' if article.get("doi") else source["url"],
                sources=sources,
                published_at=parse_iso_datetime(article.get("firstPublicationDate")),
            )
        )
    return items


def fetch_kci_source(source: dict[str, Any], sources: list[dict[str, Any]]) -> list[NewsItem]:
    api_key = os.environ.get(source.get("env_key") or "KCI_API_KEY", "")
    if not api_key:
        return []

    params = {
        "apiCode": "articleSearch",
        "key": api_key,
        "keyword": source.get("query") or "드론 인공지능",
        "displayCount": str(source.get("page_size") or 10),
        "sortNm": "date",
    }
    request = Request(
        f'{source["url"]}?{urlencode(params)}',
        headers={
            "User-Agent": "DronePulseWire/0.1 (+https://localhost)",
            "Accept": "application/xml, text/xml",
        },
    )
    with urlopen(request, timeout=10) as response:
        payload = response.read()

    root = ET.fromstring(payload)
    items: list[NewsItem] = []
    for record in root.findall(".//record"):
        title = extract_xml_text(record, ["title", "article-title", "articletitle"])
        summary = extract_xml_text(record, ["abstract", "keyword", "keywords"])
        journal = extract_xml_text(record, ["journal", "journal-title", "pubname", "publisher"])
        doi = extract_xml_text(record, ["doi"])
        url = (
            extract_xml_text(record, ["url", "link", "article-url"])
            or (f"https://doi.org/{doi}" if doi else source["url"])
        )
        pub_value = extract_xml_text(record, ["pub-date", "pubyear", "pubi-yr", "date"])
        if not source_item_is_relevant(source, title, summary):
            continue
        items.append(
            normalize_article(
                headline=title,
                summary=summary,
                source_name=source["name"],
                source_id=source["id"],
                url=url,
                sources=sources,
                published_at=parse_kci_date(pub_value),
            )
        )
    return items


# ── Dispatcher ────────────────────────────────────────────────

_FETCHER_MAP = {
    "rss": fetch_rss_source,
    "newsapi": fetch_newsapi_source,
    "gnews": fetch_gnews_source,
    "crossref": fetch_crossref_source,
    "europepmc": fetch_europepmc_source,
    "kci": fetch_kci_source,
}


def collect_source_items(source: dict[str, Any], sources: list[dict[str, Any]]) -> list[NewsItem]:
    fetcher = _FETCHER_MAP.get(source.get("type"))
    if fetcher:
        return fetcher(source, sources)
    return []


def collect_from_sources(
    sources: list[dict[str, Any]],
    source_stats: dict[str, dict[str, Any]],
) -> list[NewsItem]:
    collected: list[NewsItem] = []

    for source in sources:
        if source_missing_env_key(source):
            record_source_stat(source_stats, source, 0, None, blocked_reason="missing_env_key")
            continue
        try:
            items = collect_source_items(source, sources)
            record_source_stat(source_stats, source, len(items), None)
        except URLError:
            record_source_stat(source_stats, source, 0, "network_error")
            continue
        except Exception:
            record_source_stat(source_stats, source, 0, "collection_error")
            continue

        collected.extend(items)

    return collected
