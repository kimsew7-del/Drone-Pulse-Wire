import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Column, Index, Integer, Text, text
from app.database import Base


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(Text, unique=True, nullable=False)
    hashed_password = Column(Text, nullable=False)
    created_at = Column(Text, nullable=False, default=_now_iso, server_default=text("(datetime('now'))"))


class Source(Base):
    __tablename__ = "sources"

    id = Column(Text, primary_key=True)
    name = Column(Text, nullable=False)
    type = Column(Text, nullable=False, default="rss", server_default=text("'rss'"))
    url = Column(Text, nullable=False)
    query = Column(Text, nullable=True)
    language = Column(Text, nullable=True)
    page_size = Column(Integer, nullable=True)
    env_key = Column(Text, nullable=True)
    must_contain_any = Column(Text, default="[]", server_default=text("'[]'"))
    content_class = Column(Text, nullable=True)
    created_at = Column(Text, nullable=False, default=_now_iso, server_default=text("(datetime('now'))"))

    @property
    def must_contain_any_list(self) -> list[str]:
        try:
            return json.loads(self.must_contain_any or "[]")
        except (json.JSONDecodeError, TypeError):
            return []

    @must_contain_any_list.setter
    def must_contain_any_list(self, value: list[str]) -> None:
        self.must_contain_any = json.dumps(value, ensure_ascii=False)


class NewsItem(Base):
    __tablename__ = "news_items"
    __table_args__ = (
        Index("ix_news_items_timestamp_desc", "timestamp"),
        Index("ix_news_items_status", "status"),
        Index("ix_news_items_canonical_key", "canonical_key"),
        Index("ix_news_items_source_id", "source_id"),
        Index("ix_news_items_content_type", "content_type"),
    )

    id = Column(Text, primary_key=True)
    topic = Column(Text, nullable=False)
    region = Column(Text, nullable=False)
    headline = Column(Text, nullable=False)
    summary = Column(Text, nullable=False)
    highlights = Column(Text, default="[]", server_default=text("'[]'"))
    source = Column(Text, nullable=False)
    source_id = Column(Text, nullable=True)
    impact = Column(Integer, nullable=False)
    timestamp = Column(Text, nullable=False)
    url = Column(Text, unique=True, nullable=False)
    status = Column(Text, nullable=False, default="queued", server_default=text("'queued'"))
    duplicate_group = Column(Text, nullable=True)
    related_sources = Column(Text, default="[]", server_default=text("'[]'"))
    duplicate_count = Column(Integer, default=0, server_default=text("0"))
    canonical_key = Column(Text, nullable=True)
    merged_summary = Column(Text, nullable=True)
    related_articles = Column(Text, default="[]", server_default=text("'[]'"))
    editor_note = Column(Text, default="", server_default=text("''"))
    translated_headline = Column(Text, default="", server_default=text("''"))
    translated_summary = Column(Text, default="", server_default=text("''"))
    translated_to_ko = Column(Integer, default=0, server_default=text("0"))
    auto_categories = Column(Text, default="[]", server_default=text("'[]'"))
    content_type = Column(Text, default="news", server_default=text("'news'"))
    doc_type = Column(Text, default="", server_default=text("''"))

    # --- JSON property helpers ---

    def _get_json_list(self, attr: str) -> list[Any]:
        val = getattr(self, attr)
        try:
            return json.loads(val or "[]")
        except (json.JSONDecodeError, TypeError):
            return []

    def _set_json_list(self, attr: str, value: list[Any]) -> None:
        setattr(self, attr, json.dumps(value, ensure_ascii=False))

    @property
    def highlights_list(self) -> list[str]:
        return self._get_json_list("highlights")

    @highlights_list.setter
    def highlights_list(self, value: list[str]) -> None:
        self._set_json_list("highlights", value)

    @property
    def related_sources_list(self) -> list[str]:
        return self._get_json_list("related_sources")

    @related_sources_list.setter
    def related_sources_list(self, value: list[str]) -> None:
        self._set_json_list("related_sources", value)

    @property
    def related_articles_list(self) -> list[Any]:
        return self._get_json_list("related_articles")

    @related_articles_list.setter
    def related_articles_list(self, value: list[Any]) -> None:
        self._set_json_list("related_articles", value)

    @property
    def auto_categories_list(self) -> list[str]:
        return self._get_json_list("auto_categories")

    @auto_categories_list.setter
    def auto_categories_list(self, value: list[str]) -> None:
        self._set_json_list("auto_categories", value)


class SourceStat(Base):
    __tablename__ = "source_stats"

    source_id = Column(Text, primary_key=True)
    last_checked_at = Column(Text, nullable=True)
    last_success_at = Column(Text, nullable=True)
    last_error = Column(Text, nullable=True)
    fetched_count = Column(Integer, default=0, server_default=text("0"))
    blocked_reason = Column(Text, nullable=True)


class TrendSnapshot(Base):
    __tablename__ = "trend_snapshots"

    date = Column(Text, primary_key=True)
    total = Column(Integer, nullable=True)
    news_count = Column(Integer, nullable=True)
    research_count = Column(Integer, nullable=True)
    average_impact = Column(Integer, nullable=True)
    keyword_counts = Column(Text, default="{}", server_default=text("'{}'"))
    topic_counts = Column(Text, default="{}", server_default=text("'{}'"))
    region_counts = Column(Text, default="{}", server_default=text("'{}'"))

    def _get_json_dict(self, attr: str) -> dict[str, Any]:
        val = getattr(self, attr)
        try:
            return json.loads(val or "{}")
        except (json.JSONDecodeError, TypeError):
            return {}

    def _set_json_dict(self, attr: str, value: dict[str, Any]) -> None:
        setattr(self, attr, json.dumps(value, ensure_ascii=False))

    @property
    def keyword_counts_dict(self) -> dict[str, int]:
        return self._get_json_dict("keyword_counts")

    @keyword_counts_dict.setter
    def keyword_counts_dict(self, value: dict[str, int]) -> None:
        self._set_json_dict("keyword_counts", value)

    @property
    def topic_counts_dict(self) -> dict[str, int]:
        return self._get_json_dict("topic_counts")

    @topic_counts_dict.setter
    def topic_counts_dict(self, value: dict[str, int]) -> None:
        self._set_json_dict("topic_counts", value)

    @property
    def region_counts_dict(self) -> dict[str, int]:
        return self._get_json_dict("region_counts")

    @region_counts_dict.setter
    def region_counts_dict(self, value: dict[str, int]) -> None:
        self._set_json_dict("region_counts", value)


class CategorySnapshot(Base):
    __tablename__ = "category_snapshots"

    date = Column(Text, primary_key=True)
    windows = Column(Text, default="{}", server_default=text("'{}'"))
    categories = Column(Text, default="[]", server_default=text("'[]'"))

    @property
    def windows_dict(self) -> dict[str, Any]:
        try:
            return json.loads(self.windows or "{}")
        except (json.JSONDecodeError, TypeError):
            return {}

    @windows_dict.setter
    def windows_dict(self, value: dict[str, Any]) -> None:
        self.windows = json.dumps(value, ensure_ascii=False)

    @property
    def categories_list(self) -> list[Any]:
        try:
            return json.loads(self.categories or "[]")
        except (json.JSONDecodeError, TypeError):
            return []

    @categories_list.setter
    def categories_list(self, value: list[Any]) -> None:
        self.categories = json.dumps(value, ensure_ascii=False)
