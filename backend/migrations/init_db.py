#!/usr/bin/env python3
"""
Migration script: creates all tables and seeds initial data.

Uses synchronous sqlite3 for simplicity. Safe to run multiple times
(idempotent -- only seeds when tables are empty).
"""

import json
import sqlite3
import os
import sys
from pathlib import Path

# Resolve paths relative to the backend/ directory
BACKEND_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BACKEND_DIR / "data"
DB_PATH = DATA_DIR / "briefwave.db"

SOURCES_SEED = DATA_DIR / "sources.json"
NEWS_SEED = DATA_DIR / "seed_news.json"


DDL_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        hashed_password TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS sources (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        type TEXT NOT NULL DEFAULT 'rss',
        url TEXT NOT NULL,
        query TEXT,
        language TEXT,
        page_size INTEGER,
        env_key TEXT,
        must_contain_any TEXT DEFAULT '[]',
        content_class TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS news_items (
        id TEXT PRIMARY KEY,
        topic TEXT NOT NULL,
        region TEXT NOT NULL,
        headline TEXT NOT NULL,
        summary TEXT NOT NULL,
        highlights TEXT DEFAULT '[]',
        source TEXT NOT NULL,
        source_id TEXT REFERENCES sources(id),
        impact INTEGER NOT NULL,
        timestamp TEXT NOT NULL,
        url TEXT UNIQUE NOT NULL,
        status TEXT NOT NULL DEFAULT 'queued',
        duplicate_group TEXT,
        related_sources TEXT DEFAULT '[]',
        duplicate_count INTEGER DEFAULT 0,
        canonical_key TEXT,
        merged_summary TEXT,
        related_articles TEXT DEFAULT '[]',
        editor_note TEXT DEFAULT '',
        translated_headline TEXT DEFAULT '',
        translated_summary TEXT DEFAULT '',
        translated_to_ko INTEGER DEFAULT 0,
        auto_categories TEXT DEFAULT '[]',
        content_type TEXT DEFAULT 'news',
        doc_type TEXT DEFAULT ''
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS source_stats (
        source_id TEXT PRIMARY KEY REFERENCES sources(id),
        last_checked_at TEXT,
        last_success_at TEXT,
        last_error TEXT,
        fetched_count INTEGER DEFAULT 0,
        blocked_reason TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS trend_snapshots (
        date TEXT PRIMARY KEY,
        total INTEGER,
        news_count INTEGER,
        research_count INTEGER,
        average_impact INTEGER,
        keyword_counts TEXT DEFAULT '{}',
        topic_counts TEXT DEFAULT '{}',
        region_counts TEXT DEFAULT '{}'
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS category_snapshots (
        date TEXT PRIMARY KEY,
        windows TEXT DEFAULT '{}',
        categories TEXT DEFAULT '[]'
    )
    """,
]

INDEX_STATEMENTS = [
    "CREATE INDEX IF NOT EXISTS ix_news_items_timestamp_desc ON news_items (timestamp DESC)",
    "CREATE INDEX IF NOT EXISTS ix_news_items_status ON news_items (status)",
    "CREATE INDEX IF NOT EXISTS ix_news_items_canonical_key ON news_items (canonical_key)",
    "CREATE INDEX IF NOT EXISTS ix_news_items_source_id ON news_items (source_id)",
    "CREATE INDEX IF NOT EXISTS ix_news_items_content_type ON news_items (content_type)",
]


def _ensure_json_string(value):
    """If value is a list or dict, serialize to JSON string. Otherwise return as-is."""
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    return value


def seed_sources(conn: sqlite3.Connection) -> int:
    """Seed sources from sources.json if the table is empty. Returns rows inserted."""
    cursor = conn.execute("SELECT COUNT(*) FROM sources")
    if cursor.fetchone()[0] > 0:
        return 0

    if not SOURCES_SEED.exists():
        print(f"  [skip] {SOURCES_SEED} not found")
        return 0

    with open(SOURCES_SEED, "r", encoding="utf-8") as f:
        sources = json.load(f)

    if not sources:
        return 0

    count = 0
    for src in sources:
        if "_comment" in src or not src.get("id"):
            continue
        conn.execute(
            """
            INSERT OR IGNORE INTO sources (id, name, type, url, query, language, page_size, env_key, must_contain_any, content_class)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                src.get("id", ""),
                src.get("name", ""),
                src.get("type", "rss"),
                src.get("url", ""),
                src.get("query"),
                src.get("language"),
                src.get("page_size"),
                src.get("env_key"),
                _ensure_json_string(src.get("must_contain_any", "[]")),
                src.get("content_class"),
            ),
        )
        count += 1

    conn.commit()
    return count


def seed_news(conn: sqlite3.Connection) -> int:
    """Seed news items from seed_news.json if the table is empty. Returns rows inserted."""
    cursor = conn.execute("SELECT COUNT(*) FROM news_items")
    if cursor.fetchone()[0] > 0:
        return 0

    if not NEWS_SEED.exists():
        print(f"  [skip] {NEWS_SEED} not found")
        return 0

    with open(NEWS_SEED, "r", encoding="utf-8") as f:
        items = json.load(f)

    if not items:
        return 0

    count = 0
    for item in items:
        try:
            conn.execute(
                """
                INSERT OR IGNORE INTO news_items
                    (id, topic, region, headline, summary, highlights, source, source_id,
                     impact, timestamp, url, status, duplicate_group, related_sources,
                     duplicate_count, canonical_key, merged_summary, related_articles,
                     editor_note, translated_headline, translated_summary, translated_to_ko,
                     auto_categories, content_type, doc_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item.get("id", ""),
                    item.get("topic", ""),
                    item.get("region", ""),
                    item.get("headline", ""),
                    item.get("summary", ""),
                    _ensure_json_string(item.get("highlights", "[]")),
                    item.get("source", ""),
                    item.get("source_id"),
                    item.get("impact", 0),
                    item.get("timestamp", ""),
                    item.get("url", ""),
                    item.get("status", "queued"),
                    item.get("duplicate_group"),
                    _ensure_json_string(item.get("related_sources", "[]")),
                    item.get("duplicate_count", 0),
                    item.get("canonical_key"),
                    item.get("merged_summary"),
                    _ensure_json_string(item.get("related_articles", "[]")),
                    item.get("editor_note", ""),
                    item.get("translated_headline", ""),
                    item.get("translated_summary", ""),
                    item.get("translated_to_ko", 0),
                    _ensure_json_string(item.get("auto_categories", "[]")),
                    item.get("content_type", "news"),
                    item.get("doc_type", ""),
                ),
            )
            count += 1
        except sqlite3.IntegrityError:
            # Skip duplicates (e.g., duplicate url)
            continue

    conn.commit()
    return count


def main() -> None:
    print(f"Database path: {DB_PATH}")
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")

    print("Creating tables...")
    for stmt in DDL_STATEMENTS:
        conn.execute(stmt)
    conn.commit()

    print("Creating indexes...")
    for stmt in INDEX_STATEMENTS:
        conn.execute(stmt)
    conn.commit()

    print("Seeding sources...")
    n = seed_sources(conn)
    print(f"  Inserted {n} sources")

    print("Seeding news items...")
    n = seed_news(conn)
    print(f"  Inserted {n} news items")

    conn.close()
    print("Migration complete.")


if __name__ == "__main__":
    main()
